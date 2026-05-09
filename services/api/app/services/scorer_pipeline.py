"""Scorer pipeline service.

Wires the feature extractor and rule-based scorer into a single analyze
pipeline that takes coordinates and radius and returns scored H3 cells.
"""

import time

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
    3. Return structured HexCell objects with feature breakdowns
    """

    def __init__(self, engine: AsyncEngine, resolution: int = 11):
        """Initialize the scorer pipeline.

        Args:
            engine: Async SQLAlchemy engine connected to PostGIS database
            resolution: H3 resolution level (default: 11)
        """
        self.extractor = FeatureExtractor(engine, resolution=resolution)
        self.scorer = RuleBasedScorer()

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

        query_time_ms = int((time.time() - start_time) * 1000)
        return cells, query_time_ms
