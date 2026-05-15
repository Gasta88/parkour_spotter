"""Rule-based parkour spot scorer.

Computes a weighted sum over extracted OSM features per H3 cell,
normalized to a 0–1 score range. Negative weights penalize cells
with private/no access restrictions.
"""

import math
from typing import TYPE_CHECKING

from app.scorers.calibration import grid_search_calibrate

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


# Default weights for each feature category.
# Positive weights increase the score; negative weights decrease it.
# Weights are tuned for parkour training suitability.
DEFAULT_WEIGHTS: dict[str, float] = {
    "walls": 1.0,
    "steps": 1.0,
    "rails_fences": 0.8,
    "playgrounds": 1.2,
    "parking": 0.6,
    "benches_blocks": 0.5,
    "fitness_stations": 0.7,
    "private_access_penalty": -1.0,
    "bridges": 0.9,
    "rocks_stones": 0.8,
    "sports_pitches": 0.7,
    "good_surfaces": 0.0,
}

# Default weights for geometry metrics (log-scaled)
DEFAULT_LENGTH_WEIGHTS: dict[str, float] = {
    "walls": 0.05,
    "steps": 0.05,
    "rails_fences": 0.04,
    "bridges": 0.04,
}

DEFAULT_AREA_WEIGHTS: dict[str, float] = {
    "playgrounds": 0.3,
    "parking": 0.2,
    "sports_pitches": 0.3,
    "rocks_stones": 0.15,
}

# Default sigmoid parameters for normalization
DEFAULT_SIGMOID_OFFSET = 2.0
DEFAULT_SIGMOID_SCALE = 0.5

# Default diversity bonus multiplier
DEFAULT_DIVERSITY_BONUS = 0.3

# Maximum raw score used for normalization reference
_MAX_RAW_SCORE = 20.0


class RuleBasedScorer:
    """Rule-based scorer for parkour spot suitability.

    Computes a weighted sum over feature metrics (count + geometry),
    applies a sigmoid normalization to produce a score in [0, 1].

    The scoring formula:
        raw_score = sum(
            count_weight[category] * count +
            length_weight[category] * log(total_length_m + 1) +
            area_weight[category] * log(total_area_m2 + 1)
            for each category
        )
        raw_score *= (1 + diversity_bonus * (unique_categories / total_categories))
        if good_surfaces present: raw_score *= (1 + 0.15 * good_surfaces_ratio)
        score = sigmoid((raw_score - offset) * scale)

    The sigmoid ensures smooth differentiation between cells while
    keeping scores bounded in [0, 1].
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        length_weights: dict[str, float] | None = None,
        area_weights: dict[str, float] | None = None,
        sigmoid_offset: float | None = None,
        sigmoid_scale: float | None = None,
        diversity_bonus: float | None = None,
    ):
        """Initialize the scorer with configurable weights and parameters.

        Args:
            weights: Dict mapping feature category name to weight.
                     Uses DEFAULT_WEIGHTS if not provided.
            length_weights: Dict mapping category to length weight.
                           Uses DEFAULT_LENGTH_WEIGHTS if not provided.
            area_weights: Dict mapping category to area weight.
                         Uses DEFAULT_AREA_WEIGHTS if not provided.
            sigmoid_offset: Offset for sigmoid normalization.
                           Uses DEFAULT_SIGMOID_OFFSET if not provided.
            sigmoid_scale: Scale for sigmoid normalization.
                          Uses DEFAULT_SIGMOID_SCALE if not provided.
            diversity_bonus: Bonus multiplier for feature diversity.
                            Uses DEFAULT_DIVERSITY_BONUS if not provided.
        """
        self.weights = weights if weights is not None else dict(DEFAULT_WEIGHTS)
        self.length_weights = (
            length_weights
            if length_weights is not None
            else dict(DEFAULT_LENGTH_WEIGHTS)
        )
        self.area_weights = (
            area_weights if area_weights is not None else dict(DEFAULT_AREA_WEIGHTS)
        )
        self.sigmoid_offset = (
            sigmoid_offset if sigmoid_offset is not None else DEFAULT_SIGMOID_OFFSET
        )
        self.sigmoid_scale = (
            sigmoid_scale if sigmoid_scale is not None else DEFAULT_SIGMOID_SCALE
        )
        self.diversity_bonus = (
            diversity_bonus if diversity_bonus is not None else DEFAULT_DIVERSITY_BONUS
        )

    def score(self, h3_index: str, features: dict) -> dict:
        """Score an H3 cell based on rich feature metrics.

        Args:
            h3_index: H3 index string to score
            features: Dict mapping feature category name to metrics dict.
                      Each metrics dict has keys: count, total_length_m, total_area_m2.
                      Can also be FeatureMetrics Pydantic models.

        Returns:
            Dict with 'score' (float in [0, 1]) and 'h3_index'
        """
        raw_score = 0.0
        unique_categories = 0
        good_surfaces_count = 0

        for category, metrics in features.items():
            weight = self.weights.get(category, 0.0)
            if weight == 0.0 and category != "good_surfaces":
                continue

            # Extract metrics (supports both dict and Pydantic model)
            if hasattr(metrics, "count"):
                count = metrics.count
                total_length_m = getattr(metrics, "total_length_m", 0.0) or 0.0
                total_area_m2 = getattr(metrics, "total_area_m2", 0.0) or 0.0
            elif isinstance(metrics, dict):
                count = metrics.get("count", 0)
                total_length_m = metrics.get("total_length_m", 0.0) or 0.0
                total_area_m2 = metrics.get("total_area_m2", 0.0) or 0.0
            else:
                count = 0
                total_length_m = 0.0
                total_area_m2 = 0.0

            # Track good_surfaces separately for multiplier
            if category == "good_surfaces":
                good_surfaces_count = count
                continue

            # Count unique categories (excluding penalty and good_surfaces)
            if category != "private_access_penalty" and count > 0:
                unique_categories += 1

            # Compute raw score with geometry metrics
            category_score = weight * count

            # Add log-scaled geometry contributions
            length_weight = self.length_weights.get(category, 0.0)
            if length_weight > 0 and total_length_m > 0:
                category_score += length_weight * math.log(total_length_m + 1)

            area_weight = self.area_weights.get(category, 0.0)
            if area_weight > 0 and total_area_m2 > 0:
                category_score += area_weight * math.log(total_area_m2 + 1)

            raw_score += category_score

        # Apply diversity bonus multiplier
        # Total possible categories excludes penalty and good_surfaces
        total_categories = len(
            [
                k
                for k in self.weights.keys()
                if k not in ("private_access_penalty", "good_surfaces")
            ]
        )
        if total_categories > 0 and unique_categories > 0:
            diversity_multiplier = 1.0 + self.diversity_bonus * (
                unique_categories / total_categories
            )
            raw_score *= diversity_multiplier

        # Apply good_surfaces bonus as final multiplier
        # Ratio based on good_surfaces count relative to other features
        total_other_features = sum(
            1
            for cat, metrics in features.items()
            if cat != "good_surfaces"
            and cat != "private_access_penalty"
            and (
                (hasattr(metrics, "count") and metrics.count > 0)
                or (isinstance(metrics, dict) and metrics.get("count", 0) > 0)
            )
        )
        if total_other_features > 0 and good_surfaces_count > 0:
            good_surfaces_ratio = min(good_surfaces_count / total_other_features, 1.0)
            raw_score *= 1.0 + 0.15 * good_surfaces_ratio

        # Normalize to [0, 1] using sigmoid function
        score = self._normalize_with_params(raw_score)

        return {
            "score": score,
            "h3_index": h3_index,
        }

    @staticmethod
    def _normalize(raw_score: float) -> float:
        """Normalize a raw score to [0, 1] using a sigmoid function.

        The sigmoid is scaled so that:
        - raw_score = 0 → score ≈ baseline (determined by offset)
        - raw_score = _MAX_RAW_SCORE → score ≈ 0.99
        - raw_score = -_MAX_RAW_SCORE → score ≈ 0.01

        For parkour scoring, we want:
        - No features → low score (near 0)
        - Many positive features → high score (near 1)
        - Private access penalty → reduces score

        We shift the sigmoid so that 0 raw score maps to a low baseline.

        Args:
            raw_score: Unnormalized weighted sum

        Returns:
            Score in [0, 1]
        """
        x = (raw_score - DEFAULT_SIGMOID_OFFSET) * DEFAULT_SIGMOID_SCALE
        return 1.0 / (1.0 + math.exp(-x))

    def _normalize_with_params(self, raw_score: float) -> float:
        """Normalize using configurable sigmoid parameters.

        Args:
            raw_score: Unnormalized weighted sum

        Returns:
            Score in [0, 1]
        """
        x = (raw_score - self.sigmoid_offset) * self.sigmoid_scale
        return 1.0 / (1.0 + math.exp(-x))

    async def calibrate(
        self,
        engine: "AsyncEngine",
        min_samples: int = 30,
    ) -> dict[str, float]:
        """Calibrate sigmoid offset/scale against annotated data.

        Reads human-annotated scores from the spots_annotated table,
        computes raw scores for each annotation, and optimizes
        sigmoid parameters to minimize MSE.

        Args:
            engine: Async SQLAlchemy engine connected to database
            min_samples: Minimum number of annotations required for calibration

        Returns:
            Dict with offset, scale, mse, and samples_used
        """
        from sqlalchemy import text
        from sqlalchemy.exc import ProgrammingError

        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("""
                        SELECT h3_index, features, human_score
                        FROM spots_annotated
                        WHERE human_score IS NOT NULL
                        ORDER BY created_at DESC
                    """)
                )
                rows = result.fetchall()
        except ProgrammingError:
            return {
                "offset": self.sigmoid_offset,
                "scale": self.sigmoid_scale,
                "mse": 0.0,
                "samples_used": 0,
            }

        if len(rows) < min_samples:
            return {
                "offset": self.sigmoid_offset,
                "scale": self.sigmoid_scale,
                "mse": 0.0,
                "samples_used": len(rows),
            }

        samples: list[tuple[float, float]] = []
        for row in rows:
            features = row.features
            human_score = row.human_score

            raw_score = self._compute_raw_score(features)
            samples.append((raw_score, human_score))

        calibration_result = grid_search_calibrate(samples)

        self.sigmoid_offset = calibration_result.offset
        self.sigmoid_scale = calibration_result.scale

        return {
            "offset": calibration_result.offset,
            "scale": calibration_result.scale,
            "mse": calibration_result.mse,
            "samples_used": calibration_result.samples_used,
        }

    def _compute_raw_score(self, features: dict) -> float:
        """Compute raw score without normalization.

        Args:
            features: Dict mapping category to metrics

        Returns:
            Raw weighted score before sigmoid normalization
        """
        raw_score = 0.0
        unique_categories = 0
        good_surfaces_count = 0

        for category, metrics in features.items():
            weight = self.weights.get(category, 0.0)
            if weight == 0.0 and category != "good_surfaces":
                continue

            if hasattr(metrics, "count"):
                count = metrics.count
                total_length_m = getattr(metrics, "total_length_m", 0.0) or 0.0
                total_area_m2 = getattr(metrics, "total_area_m2", 0.0) or 0.0
            elif isinstance(metrics, dict):
                count = metrics.get("count", 0)
                total_length_m = metrics.get("total_length_m", 0.0) or 0.0
                total_area_m2 = metrics.get("total_area_m2", 0.0) or 0.0
            else:
                count = 0
                total_length_m = 0.0
                total_area_m2 = 0.0

            if category == "good_surfaces":
                good_surfaces_count = count
                continue

            if category != "private_access_penalty" and count > 0:
                unique_categories += 1

            category_score = weight * count

            length_weight = self.length_weights.get(category, 0.0)
            if length_weight > 0 and total_length_m > 0:
                category_score += length_weight * math.log(total_length_m + 1)

            area_weight = self.area_weights.get(category, 0.0)
            if area_weight > 0 and total_area_m2 > 0:
                category_score += area_weight * math.log(total_area_m2 + 1)

            raw_score += category_score

        total_categories = len(
            [
                k
                for k in self.weights.keys()
                if k not in ("private_access_penalty", "good_surfaces")
            ]
        )
        if total_categories > 0 and unique_categories > 0:
            diversity_multiplier = 1.0 + self.diversity_bonus * (
                unique_categories / total_categories
            )
            raw_score *= diversity_multiplier

        total_other_features = sum(
            1
            for cat, metrics in features.items()
            if cat != "good_surfaces"
            and cat != "private_access_penalty"
            and (
                (hasattr(metrics, "count") and metrics.count > 0)
                or (isinstance(metrics, dict) and metrics.get("count", 0) > 0)
            )
        )
        if total_other_features > 0 and good_surfaces_count > 0:
            good_surfaces_ratio = min(good_surfaces_count / total_other_features, 1.0)
            raw_score *= 1.0 + 0.15 * good_surfaces_ratio

        return raw_score
