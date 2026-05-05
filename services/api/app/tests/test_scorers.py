"""Tests for scorers."""

from app.scorers.rule_based import RuleBasedScorer


def test_rule_based_scorer_returns_dict() -> None:
    """Test that rule-based scorer returns dict with expected keys."""
    scorer = RuleBasedScorer()
    result = scorer.score("8b1fb46622dffff", [])

    assert "score" in result
    assert "h3_index" in result
    assert result["h3_index"] == "8b1fb46622dffff"
    assert 0 <= result["score"] <= 1


def test_rule_based_scorer_with_features() -> None:
    """Test scorer with sample features."""
    scorer = RuleBasedScorer()
    features = [{"type": "wall", "height": 2.0}]
    result = scorer.score("8b1fb46622dffff", features)

    assert isinstance(result["score"], (int, float))
