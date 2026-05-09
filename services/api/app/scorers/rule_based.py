"""Rule-based parkour spot scorer.

Computes a weighted sum over extracted OSM features per H3 cell,
normalized to a 0–1 score range. Negative weights penalize cells
with private/no access restrictions.
"""

import math


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
}

# Maximum raw score used for normalization.
# This represents a "very good" parkour spot with many features.
# Scores above this are clamped to 1.0 after sigmoid normalization.
_MAX_RAW_SCORE = 20.0


class RuleBasedScorer:
    """Rule-based scorer for parkour spot suitability.

    Computes a weighted sum over feature metrics (primarily count),
    applies a sigmoid normalization to produce a score in [0, 1].

    The scoring formula:
        raw_score = sum(weight[category] * metrics.count for each category)
        score = sigmoid(raw_score / _MAX_RAW_SCORE * 5)

    The sigmoid ensures smooth differentiation between cells while
    keeping scores bounded in [0, 1].
    """

    def __init__(self, weights: dict[str, float] | None = None):
        """Initialize the scorer with configurable weights.

        Args:
            weights: Dict mapping feature category name to weight.
                     Uses DEFAULT_WEIGHTS if not provided.
        """
        self.weights = weights if weights is not None else dict(DEFAULT_WEIGHTS)

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

        for category, metrics in features.items():
            weight = self.weights.get(category, 0.0)
            if weight == 0.0:
                continue

            # Extract count from metrics (supports both dict and Pydantic model)
            if hasattr(metrics, "count"):
                count = metrics.count
            elif isinstance(metrics, dict):
                count = metrics.get("count", 0)
            else:
                count = 0

            raw_score += weight * count

        # Normalize to [0, 1] using sigmoid function
        score = self._normalize(raw_score)

        return {
            "score": score,
            "h3_index": h3_index,
        }

    @staticmethod
    def _normalize(raw_score: float) -> float:
        """Normalize a raw score to [0, 1] using a sigmoid function.

        The sigmoid is scaled so that:
        - raw_score = 0 → score ≈ 0.5
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
        # Shift sigmoid: we want raw_score=0 to give a low baseline (~0.1)
        # and raw_score=_MAX_RAW_SCORE to give a high score (~0.9)
        # sigmoid(x) = 1 / (1 + exp(-x))
        # We use: score = sigmoid((raw_score - offset) * scale)
        # With offset=2 and scale=0.5:
        #   raw=0  → sigmoid(-1) ≈ 0.27
        #   raw=10 → sigmoid(4)  ≈ 0.98
        #   raw=-5 → sigmoid(-3.5) ≈ 0.03
        offset = 2.0
        scale = 0.5
        x = (raw_score - offset) * scale
        return 1.0 / (1.0 + math.exp(-x))
