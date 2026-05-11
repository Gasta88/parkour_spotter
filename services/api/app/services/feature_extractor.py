"""Feature extraction service for OSM data.

Orchestrates SQL queries for all 8 feature categories, aggregates results
per H3 cell, and returns a rich feature dictionary suitable for scoring.

Usage:
    extractor = FeatureExtractor(engine, resolution=11)
    features = await extractor.extract(lat=45.4064, lon=11.8778, radius_km=5.0)
"""

from sqlalchemy.ext.asyncio import AsyncEngine

from common.h3_utils import (
    bigint_to_h3_index,
    get_k_ring,
    h3_index_to_bigint,
    latlng_to_h3,
)
from common.sql_queries import FEATURE_QUERIES, H3_RESOLUTION, build_feature_query


class FeatureExtractor:
    """Extracts parkour-relevant features from OSM data into H3 cells.

    Executes 8 SQL queries (one per feature category) against the PostGIS
    database, aggregates results per H3 cell, and returns a dictionary
    mapping H3 index strings to their feature metrics.
    """

    def __init__(self, engine: AsyncEngine, resolution: int = H3_RESOLUTION):
        """Initialize the feature extractor.

        Args:
            engine: Async SQLAlchemy engine connected to PostGIS database
            resolution: H3 resolution level (default: 11)
        """
        self.engine = engine
        self.resolution = resolution

    async def extract(
        self, lat: float, lon: float, radius_km: float
    ) -> dict[str, dict[str, dict]]:
        """Extract features for all H3 cells within the given radius.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius_km: Search radius in kilometers

        Returns:
            Dict mapping H3 index strings to feature dicts.
            Each feature dict maps category names to metric dicts:
            {
                "8b1fb46622dffff": {
                    "walls": {"count": 12, "total_length_m": 45.3, "total_area_m2": 0.0},
                    "steps": {"count": 3, "total_length_m": 18.0, "total_area_m2": 0.0},
                    ...
                },
                ...
            }
        """
        # Compute the center H3 cell and its k-ring coverage
        center_cell = latlng_to_h3(lat, lon, self.resolution)
        k_ring = get_k_ring(center_cell, radius_km, self.resolution)

        # Convert hex string indices to bigint for h3-pg queries
        h3_bigints = [h3_index_to_bigint(idx) for idx in k_ring]

        if not h3_bigints:
            return {}

        # Initialize result structure: all cells start with empty feature dicts
        result: dict[str, dict[str, dict]] = {}
        for h3_idx in k_ring:
            result[h3_idx] = {}

        # Execute each feature query and aggregate results
        async with self.engine.connect() as conn:
            for feature_name in FEATURE_QUERIES:
                query = build_feature_query(feature_name, h3_bigints, self.resolution)

                try:
                    rows = await conn.execute(query)
                    results = rows.fetchall()

                    for row in results:
                        # h3_index comes back as bigint from h3-pg
                        h3_bigint = row[0]
                        h3_hex = bigint_to_h3_index(h3_bigint)

                        # Skip cells outside our k-ring (safety check)
                        if h3_hex not in result:
                            continue

                        # Build metrics dict from row columns
                        metrics = _row_to_metrics(row, feature_name)

                        # Merge with existing metrics for this cell/category
                        if feature_name in result[h3_hex]:
                            existing = result[h3_hex][feature_name]
                            metrics = _merge_metrics(existing, metrics)

                        result[h3_hex][feature_name] = metrics

                except Exception:
                    # If a query fails (e.g., table doesn't exist), skip this feature
                    # This allows graceful handling when planet_osm_* tables are empty
                    continue

        return result


def _row_to_metrics(row, feature_name: str) -> dict:
    """Convert a SQL result row to a metrics dictionary.

    Different feature categories return different columns:
    - Line features: count, total_length_m
    - Polygon features: count, total_area_m2
    - Combined (UNION ALL): count, total_length_m, total_area_m2
    - Point-only features: count

    Args:
        row: SQLAlchemy Row from feature query
        feature_name: Name of the feature category

    Returns:
        Dict with count, total_length_m, total_area_m2
    """
    metrics: dict = {"count": 0, "total_length_m": 0.0, "total_area_m2": 0.0}

    # Row structure: (h3_index, count, [total_length_m], [total_area_m2])
    # Column indices vary by query; we check by column name
    row_dict = row._mapping if hasattr(row, "_mapping") else dict(row._fields)

    if hasattr(row, "_mapping"):
        mapping = dict(row._mapping)
        metrics["count"] = mapping.get("count", 0)
        metrics["total_length_m"] = float(mapping.get("total_length_m", 0.0) or 0.0)
        metrics["total_area_m2"] = float(mapping.get("total_area_m2", 0.0) or 0.0)
    else:
        # Fallback: positional access
        metrics["count"] = row[1] if len(row) > 1 else 0
        if len(row) > 2:
            metrics["total_length_m"] = float(row[2] or 0.0)
        if len(row) > 3:
            metrics["total_area_m2"] = float(row[3] or 0.0)

    return metrics


def _merge_metrics(existing: dict, new: dict) -> dict:
    """Merge two metric dicts for the same cell/category (from UNION ALL).

    When a feature query uses UNION ALL to combine results from multiple
    tables (e.g., walls from both lines and polygons), we need to sum
    the metrics.

    Args:
        existing: Previously accumulated metrics
        new: New metrics to merge

    Returns:
        Merged metrics dict
    """
    return {
        "count": existing.get("count", 0) + new.get("count", 0),
        "total_length_m": existing.get("total_length_m", 0.0)
        + new.get("total_length_m", 0.0),
        "total_area_m2": existing.get("total_area_m2", 0.0)
        + new.get("total_area_m2", 0.0),
    }
