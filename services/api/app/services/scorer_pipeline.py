"""Scorer pipeline service.

Wires the feature extractor and rule-based scorer into a single analyze
pipeline that takes coordinates and radius and returns scored H3 cells.
"""

import time

import h3
from sqlalchemy.ext.asyncio import AsyncEngine

from app.schemas.analyze import Centroid, FeatureMetrics, HexCell
from app.scorers.rule_based import RuleBasedScorer
from app.services.feature_extractor import FeatureExtractor
from common.h3_utils import h3_to_latlng


class ScorerPipeline:
    """End-to-end pipeline: extract features → score cells → return results.

    This service orchestrates the full analyze workflow:
    1. Extract OSM features into H3 cells via FeatureExtractor
    2. Score each cell via RuleBasedScorer
    3. Apply spatial smoothing pass using H3 k-ring neighbors
    4. Return structured HexCell objects with feature breakdowns
    """

    def __init__(
        self,
        engine: AsyncEngine,
        resolution: int = 11,
        spatial_alpha: float = 0.9,
    ):
        """Initialize the scorer pipeline.

        Args:
            engine: Async SQLAlchemy engine connected to PostGIS database
            resolution: H3 resolution level (default: 11)
            spatial_alpha: Weight for spatial smoothing (0.0-1.0).
                          Higher values keep more of the original cell score.
                          Default: 0.7 (70% cell identity, 30% neighbor influence)
        """
        self.extractor = FeatureExtractor(engine, resolution=resolution)
        self.scorer = RuleBasedScorer()
        self.spatial_alpha = spatial_alpha

    async def analyze(
        self, lat: float, lon: float, radius_km: float
    ) -> tuple[list[HexCell], int]:
        """Run the full analyze pipeline.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius_km: Search radius in kilometers

        Returns:
            Tuple of (list of scored HexCells, query time in milliseconds)
        """
        start_time = time.time()

        # Step 1: Extract features from OSM data
        raw_features = await self.extractor.extract(lat, lon, radius_km)

        # Step 2: Score each cell and build response objects
        cells: list[HexCell] = []
        cell_scores: dict[str, float] = {}

        for h3_index, feature_dict in raw_features.items():
            # Convert raw feature dicts to FeatureMetrics objects
            feature_metrics: dict[str, FeatureMetrics] = {}
            for category, metrics in feature_dict.items():
                feature_metrics[category] = FeatureMetrics(
                    count=metrics.get("count", 0),
                    total_length_m=metrics.get("total_length_m", 0.0),
                    total_area_m2=metrics.get("total_area_m2", 0.0),
                )

            # Score the cell using the feature breakdown
            score_result = self.scorer.score(h3_index, feature_metrics)
            score = score_result["score"]
            cell_scores[h3_index] = score

            # Get centroid coordinates
            centroid_lat, centroid_lon = h3_to_latlng(h3_index)

            cells.append(
                HexCell(
                    h3_index=h3_index,
                    score=score,
                    centroid=Centroid(lat=centroid_lat, lon=centroid_lon),
                    features=feature_metrics,
                )
            )

        # Step 3: Apply spatial smoothing pass
        if self.spatial_alpha < 1.0:
            self._apply_spatial_smoothing(cells, cell_scores)

        # Step 4: Filter out zero-score cells to reduce response size
        cells = [cell for cell in cells if cell.score > 0]

        query_time_ms = int((time.time() - start_time) * 1000)
        return cells, query_time_ms

    def _apply_spatial_smoothing(
        self, cells: list[HexCell], cell_scores: dict[str, float]
    ) -> None:
        """Apply spatial smoothing to cell scores using H3 k-ring neighbors.

        For each cell, computes a weighted average:
            final_score = α * cell_score + (1-α) * mean(neighbor_scores)

        Args:
            cells: List of HexCell objects to smooth (modified in place)
            cell_scores: Dict mapping H3 index to initial score
        """
        for cell in cells:
            h3_index = cell.h3_index

            # Get k-ring neighbors at distance 1
            try:
                neighbors = h3.grid_ring(h3_index, 1)
            except Exception:
                continue

            # Filter to neighbors that have scores
            neighbor_scores = [
                cell_scores[neighbor]
                for neighbor in neighbors
                if neighbor in cell_scores
            ]

            if not neighbor_scores:
                continue

            # Compute mean neighbor score
            mean_neighbor_score = sum(neighbor_scores) / len(neighbor_scores)

            # Apply weighted average
            original_score = cell_scores[h3_index]
            smoothed_score = (
                self.spatial_alpha * original_score
                + (1 - self.spatial_alpha) * mean_neighbor_score
            )

            # Clamp to [0, 1]
            smoothed_score = max(0.0, min(1.0, smoothed_score))

            # Update cell score
            cell.score = smoothed_score
