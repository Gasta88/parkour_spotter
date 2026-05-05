"""Rule-based parkour spot scorer."""


class RuleBasedScorer:
    """Rule-based scorer for parkour spot suitability.

    This is a Phase 1 placeholder. Will be implemented in future iterations.
    """

    def score(self, h3_index: str, features: list[dict]) -> dict:
        """Score an H3 cell based on OSM features.

        Args:
            h3_index: H3 index to score
            features: List of OSM features in the cell

        Returns:
            Dict with score and h3_index
        """
        return {
            "score": 0.5,
            "h3_index": h3_index,
        }
