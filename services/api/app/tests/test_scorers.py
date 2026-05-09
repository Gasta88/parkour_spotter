"""Tests for rule-based scorer."""

import math

from app.schemas.analyze import FeatureMetrics
from app.scorers.rule_based import DEFAULT_WEIGHTS, RuleBasedScorer


class TestRuleBasedScorerBasic:
    """Basic tests for RuleBasedScorer."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Test that scorer returns dict with 'score' and 'h3_index'."""
        scorer = RuleBasedScorer()
        result = scorer.score("8b1fb46622dffff", {})
        assert "score" in result
        assert "h3_index" in result
        assert result["h3_index"] == "8b1fb46622dffff"

    def test_score_in_valid_range(self) -> None:
        """Test that score is always in [0, 1]."""
        scorer = RuleBasedScorer()
        result = scorer.score("8b1fb46622dffff", {})
        assert 0 <= result["score"] <= 1

    def test_empty_features_gives_low_score(self) -> None:
        """Test that empty features produce a low baseline score."""
        scorer = RuleBasedScorer()
        result = scorer.score("8b1fb46622dffff", {})
        # With sigmoid offset=2, raw=0 → score ≈ 0.27
        assert result["score"] < 0.5


class TestRuleBasedScorerWithFeatures:
    """Tests for scoring with various feature combinations."""

    def test_positive_features_increase_score(self) -> None:
        """Test that positive features increase the score above baseline."""
        scorer = RuleBasedScorer()
        empty_result = scorer.score("8b1fb46622dffff", {})

        features = {
            "walls": FeatureMetrics(count=10),
            "steps": FeatureMetrics(count=5),
        }
        result = scorer.score("8b1fb46622dffff", features)

        assert result["score"] > empty_result["score"]

    def test_private_access_decreases_score(self) -> None:
        """Test that private access penalty decreases the score."""
        scorer = RuleBasedScorer()
        features_positive = {
            "walls": FeatureMetrics(count=10),
        }
        features_with_penalty = {
            "walls": FeatureMetrics(count=10),
            "private_access_penalty": FeatureMetrics(count=5),
        }

        result_positive = scorer.score("8b1fb46622dffff", features_positive)
        result_penalty = scorer.score("8b1fb46622dffff", features_with_penalty)

        assert result_penalty["score"] < result_positive["score"]

    def test_all_max_features_gives_high_score(self) -> None:
        """Test that many positive features produce a high score."""
        scorer = RuleBasedScorer()
        features = {
            "walls": FeatureMetrics(count=20),
            "steps": FeatureMetrics(count=15),
            "rails_fences": FeatureMetrics(count=10),
            "playgrounds": FeatureMetrics(count=5),
            "parking": FeatureMetrics(count=3),
            "benches_blocks": FeatureMetrics(count=10),
            "fitness_stations": FeatureMetrics(count=5),
        }
        result = scorer.score("8b1fb46622dffff", features)
        assert result["score"] > 0.8

    def test_mixed_features_produce_mid_score(self) -> None:
        """Test that mixed positive/negative features produce a mid-range score."""
        scorer = RuleBasedScorer()
        features = {
            "walls": FeatureMetrics(count=5),
            "steps": FeatureMetrics(count=3),
            "private_access_penalty": FeatureMetrics(count=3),
        }
        result = scorer.score("8b1fb46622dffff", features)
        assert 0.1 < result["score"] < 0.9


class TestRuleBasedScorerWeights:
    """Tests for configurable weights."""

    def test_custom_weights_affect_score(self) -> None:
        """Test that custom weights change the score proportionally."""
        default_scorer = RuleBasedScorer()
        high_weight_scorer = RuleBasedScorer(
            weights={"walls": 5.0, **{k: v for k, v in DEFAULT_WEIGHTS.items() if k != "walls"}}
        )

        features = {"walls": FeatureMetrics(count=10)}

        default_result = default_scorer.score("8b1fb46622dffff", features)
        high_weight_result = high_weight_scorer.score("8b1fb46622dffff", features)

        # Higher weight should produce higher score
        assert high_weight_result["score"] > default_result["score"]

    def test_zero_weight_ignores_feature(self) -> None:
        """Test that zero weight effectively ignores a feature."""
        scorer = RuleBasedScorer(weights={"walls": 0.0})
        features = {"walls": FeatureMetrics(count=100)}
        result = scorer.score("8b1fb46622dffff", features)

        # With zero weight, score should be same as empty features
        empty_result = scorer.score("8b1fb46622dffff", {})
        assert abs(result["score"] - empty_result["score"]) < 0.01

    def test_negative_weight_penalizes(self) -> None:
        """Test that negative weight penalizes the score."""
        scorer = RuleBasedScorer(weights={"walls": -2.0})
        features = {"walls": FeatureMetrics(count=10)}
        result = scorer.score("8b1fb46622dffff", features)

        empty_result = scorer.score("8b1fb46622dffff", {})
        assert result["score"] < empty_result["score"]


class TestRuleBasedScorerNormalization:
    """Tests for score normalization."""

    def test_score_never_exceeds_one(self) -> None:
        """Test that score is clamped to maximum 1.0."""
        scorer = RuleBasedScorer()
        features = {
            "walls": FeatureMetrics(count=1000),
            "steps": FeatureMetrics(count=1000),
            "playgrounds": FeatureMetrics(count=1000),
        }
        result = scorer.score("8b1fb46622dffff", features)
        assert result["score"] <= 1.0

    def test_score_never_below_zero(self) -> None:
        """Test that score is clamped to minimum 0.0."""
        scorer = RuleBasedScorer()
        features = {
            "private_access_penalty": FeatureMetrics(count=1000),
        }
        result = scorer.score("8b1fb46622dffff", features)
        assert result["score"] >= 0.0

    def test_sigmoid_is_monotonic(self) -> None:
        """Test that more features always produce equal or higher scores."""
        scorer = RuleBasedScorer()
        scores = []
        for count in range(0, 20):
            features = {"walls": FeatureMetrics(count=count)}
            result = scorer.score("8b1fb46622dffff", features)
            scores.append(result["score"])

        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1]


class TestRuleBasedScorerDictInput:
    """Tests for scorer accepting dict input (not just Pydantic models)."""

    def test_score_with_dict_metrics(self) -> None:
        """Test that scorer works with plain dict metrics."""
        scorer = RuleBasedScorer()
        features = {
            "walls": {"count": 12, "total_length_m": 45.3, "total_area_m2": 0.0},
            "steps": {"count": 3, "total_length_m": 18.0, "total_area_m2": 0.0},
        }
        result = scorer.score("8b1fb46622dffff", features)
        assert 0 <= result["score"] <= 1

    def test_score_with_partial_dict_metrics(self) -> None:
        """Test that scorer works with partial dict metrics."""
        scorer = RuleBasedScorer()
        features = {
            "walls": {"count": 5},
        }
        result = scorer.score("8b1fb46622dffff", features)
        assert 0 <= result["score"] <= 1
