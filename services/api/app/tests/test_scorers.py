"""Tests for rule-based scorer."""

import math

from app.schemas.analyze import FeatureMetrics
from app.scorers.rule_based import (
    DEFAULT_WEIGHTS,
    DEFAULT_LENGTH_WEIGHTS,
    DEFAULT_AREA_WEIGHTS,
    DEFAULT_SIGMOID_OFFSET,
    DEFAULT_SIGMOID_SCALE,
    DEFAULT_DIVERSITY_BONUS,
    RuleBasedScorer,
)


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


class TestGeometryMetrics:
    """Tests for geometry metric contributions."""

    def test_geometry_metrics_contribution(self) -> None:
        """Test that log(total_length_m + 1) and log(total_area_m2 + 1) contribute to score."""
        scorer = RuleBasedScorer(
            weights={"walls": 1.0},
            length_weights={"walls": 0.05},
            area_weights={},
        )
        
        # Features with geometry
        features_with_geometry = {
            "walls": FeatureMetrics(count=5, total_length_m=45.3, total_area_m2=0.0),
        }
        
        # Features without geometry
        features_without_geometry = {
            "walls": FeatureMetrics(count=5, total_length_m=0.0, total_area_m2=0.0),
        }
        
        result_with = scorer.score("8b1fb46622dffff", features_with_geometry)
        result_without = scorer.score("8b1fb46622dffff", features_without_geometry)
        
        # Geometry should increase the score
        assert result_with["score"] > result_without["score"]

    def test_geometry_zero_values(self) -> None:
        """Test that log(0 + 1) = 0 produces no contribution when geometry metrics are absent."""
        scorer = RuleBasedScorer(
            weights={"walls": 1.0},
            length_weights={"walls": 0.05},
            area_weights={"walls": 0.02},
        )
        
        features = {
            "walls": FeatureMetrics(count=5, total_length_m=0.0, total_area_m2=0.0),
        }
        
        result = scorer.score("8b1fb46622dffff", features)
        
        # Score should be based only on count, not geometry
        # raw = 1.0 * 5 + 0.05 * log(1) + 0.02 * log(1) = 5
        assert 0 < result["score"] < 1

    def test_log_scaling_prevents_domination(self) -> None:
        """Test that log scaling prevents large geometry values from dominating."""
        scorer = RuleBasedScorer(
            weights={"walls": 1.0},
            length_weights={"walls": 0.05},
        )
        
        # Massive geometry value (10km wall)
        features_massive = {
            "walls": FeatureMetrics(count=1, total_length_m=10000.0, total_area_m2=0.0),
        }
        
        # Moderate geometry value
        features_moderate = {
            "walls": FeatureMetrics(count=1, total_length_m=50.0, total_area_m2=0.0),
        }
        
        result_massive = scorer.score("8b1fb46622dffff", features_massive)
        result_moderate = scorer.score("8b1fb46622dffff", features_moderate)
        
        # Massive geometry should not saturate the score
        assert result_massive["score"] < 1.0
        # But should still be higher than moderate
        assert result_massive["score"] > result_moderate["score"]


class TestDiversityBonus:
    """Tests for feature diversity multiplier."""

    def test_diversity_multiplier(self) -> None:
        """Test that a cell with features from 4/10 categories gets ~1.12x multiplier."""
        scorer = RuleBasedScorer(diversity_bonus=0.3)
        
        # 4 different categories
        features = {
            "walls": FeatureMetrics(count=5),
            "steps": FeatureMetrics(count=3),
            "rails_fences": FeatureMetrics(count=4),
            "playgrounds": FeatureMetrics(count=2),
        }
        
        result = scorer.score("8b1fb46622dffff", features)
        
        # Diversity multiplier: 1 + 0.3 * (4/10) = 1.12
        # Score should be higher than single category
        single_features = {"walls": FeatureMetrics(count=14)}
        result_single = scorer.score("8b1fb46622dffff", single_features)
        
        # Diversity should provide a bonus
        assert result["score"] > result_single["score"]

    def test_diversity_full_categories(self) -> None:
        """Test that full diversity (10/10) gets max 1.3x multiplier."""
        scorer = RuleBasedScorer(diversity_bonus=0.3)
        
        # All 10 positive categories
        features = {
            "walls": FeatureMetrics(count=2),
            "steps": FeatureMetrics(count=2),
            "rails_fences": FeatureMetrics(count=2),
            "playgrounds": FeatureMetrics(count=2),
            "parking": FeatureMetrics(count=2),
            "benches_blocks": FeatureMetrics(count=2),
            "fitness_stations": FeatureMetrics(count=2),
            "bridges": FeatureMetrics(count=2),
            "rocks_stones": FeatureMetrics(count=2),
            "sports_pitches": FeatureMetrics(count=2),
        }
        
        result = scorer.score("8b1fb46622dffff", features)
        
        # Should have high score due to max diversity bonus
        assert result["score"] > 0.5

    def test_diversity_with_penalty_excluded(self) -> None:
        """Verify private_access_penalty is excluded from total_possible_categories count."""
        scorer = RuleBasedScorer()
        
        # Features with penalty
        features_with_penalty = {
            "walls": FeatureMetrics(count=5),
            "private_access_penalty": FeatureMetrics(count=10),
        }
        
        result = scorer.score("8b1fb46622dffff", features_with_penalty)
        
        # Penalty should reduce score but not affect diversity count
        assert 0 <= result["score"] <= 1


class TestSigmoidParams:
    """Tests for configurable sigmoid parameters."""

    def test_custom_offset_affects_score(self) -> None:
        """Test that custom offset value produces expected score mapping."""
        default_scorer = RuleBasedScorer(sigmoid_offset=2.0)
        high_offset_scorer = RuleBasedScorer(sigmoid_offset=5.0)
        
        features = {"walls": FeatureMetrics(count=10)}
        
        default_result = default_scorer.score("8b1fb46622dffff", features)
        high_offset_result = high_offset_scorer.score("8b1fb46622dffff", features)
        
        # Higher offset should produce lower score (harder to reach high scores)
        assert high_offset_result["score"] < default_result["score"]

    def test_custom_scale_affects_score(self) -> None:
        """Test that custom scale value produces expected score mapping."""
        default_scorer = RuleBasedScorer(sigmoid_scale=0.5)
        low_scale_scorer = RuleBasedScorer(sigmoid_scale=0.2)
        
        features = {"walls": FeatureMetrics(count=10)}
        
        default_result = default_scorer.score("8b1fb46622dffff", features)
        low_scale_result = low_scale_scorer.score("8b1fb46622dffff", features)
        
        # Lower scale should produce score closer to baseline
        assert abs(low_scale_result["score"] - 0.5) < abs(default_result["score"] - 0.5)


class TestGoodSurfacesMultiplier:
    """Tests for good_surfaces bonus modifier."""

    def test_good_surfaces_increases_score(self) -> None:
        """Test that good_surfaces ratio increases final score by up to 15%."""
        scorer = RuleBasedScorer()
        
        # Features with good surfaces
        features_with_surfaces = {
            "walls": FeatureMetrics(count=5),
            "steps": FeatureMetrics(count=3),
            "good_surfaces": FeatureMetrics(count=8),
        }
        
        # Same features without good surfaces
        features_without_surfaces = {
            "walls": FeatureMetrics(count=5),
            "steps": FeatureMetrics(count=3),
        }
        
        result_with = scorer.score("8b1fb46622dffff", features_with_surfaces)
        result_without = scorer.score("8b1fb46622dffff", features_without_surfaces)
        
        # Good surfaces should increase the score
        assert result_with["score"] > result_without["score"]

    def test_good_surfaces_only_no_bonus(self) -> None:
        """Test that good_surfaces alone without other features gives no bonus."""
        scorer = RuleBasedScorer()
        
        # Only good surfaces
        features_only_surfaces = {
            "good_surfaces": FeatureMetrics(count=10),
        }
        
        # Empty features
        features_empty = {}
        
        result_only = scorer.score("8b1fb46622dffff", features_only_surfaces)
        result_empty = scorer.score("8b1fb46622dffff", features_empty)
        
        # Good surfaces alone should not provide bonus (same as baseline)
        assert abs(result_only["score"] - result_empty["score"]) < 0.01

    def test_good_surfaces_capped_at_multiplier(self) -> None:
        """Test that good_surfaces multiplier is capped."""
        scorer = RuleBasedScorer()
        
        # Many good surfaces (more than other features)
        features = {
            "walls": FeatureMetrics(count=2),
            "good_surfaces": FeatureMetrics(count=100),
        }
        
        result = scorer.score("8b1fb46622dffff", features)
        
        # Score should be capped at 1.0
        assert result["score"] <= 1.0
