"""Tests for calibration module."""

from app.scorers.calibration import (
    CalibrationResult,
    grid_search_calibrate,
    _compute_mse,
    _sigmoid,
)


class TestSigmoidFunction:
    """Tests for sigmoid function."""

    def test_sigmoid_returns_valid_range(self) -> None:
        """Test that sigmoid always returns value in [0, 1]."""
        assert 0 <= _sigmoid(0, 2.0, 0.5) <= 1
        assert 0 <= _sigmoid(100, 2.0, 0.5) <= 1
        assert 0 <= _sigmoid(-100, 2.0, 0.5) <= 1

    def test_sigmoid_with_default_params(self) -> None:
        """Test sigmoid with default offset=2, scale=0.5."""
        # raw=0 → sigmoid(-1) ≈ 0.27
        result = _sigmoid(0, 2.0, 0.5)
        assert 0.2 < result < 0.4

        # raw=10 → sigmoid(4) ≈ 0.98
        result = _sigmoid(10, 2.0, 0.5)
        assert result > 0.95

    def test_sigmoid_monotonic(self) -> None:
        """Test that sigmoid is monotonically increasing."""
        prev = _sigmoid(-10, 2.0, 0.5)
        for x in range(-10, 20):
            curr = _sigmoid(x, 2.0, 0.5)
            assert curr >= prev
            prev = curr


class TestComputeMSE:
    """Tests for MSE computation."""

    def test_mse_perfect_prediction(self) -> None:
        """Test MSE is zero when predictions match perfectly."""
        samples = [(0, 0.27), (5, 0.73), (10, 0.98)]
        mse = _compute_mse(samples, offset=2.0, scale=0.5)
        assert mse < 0.01  # Allow small numerical error

    def test_mse_with_errors(self) -> None:
        """Test MSE computation with prediction errors."""
        samples = [(0, 0.5), (5, 0.5), (10, 0.5)]
        mse = _compute_mse(samples, offset=2.0, scale=0.5)
        assert mse > 0

    def test_mse_empty_samples(self) -> None:
        """Test MSE returns 0 for empty samples."""
        mse = _compute_mse([], offset=2.0, scale=0.5)
        assert mse == 0.0


class TestGridSearchCalibrate:
    """Tests for grid search calibration."""

    def test_calibration_grid_search(self) -> None:
        """Test that grid search finds offset/scale that minimize MSE."""
        # Create synthetic data: raw scores and human annotations
        # We want sigmoid with offset≈3, scale≈0.6
        samples = [
            (0, 0.2),
            (2, 0.35),
            (5, 0.65),
            (8, 0.85),
            (10, 0.95),
        ]

        result = grid_search_calibrate(
            samples,
            offset_range=(0.0, 5.0),
            offset_step=0.25,
            scale_range=(0.1, 1.0),
            scale_step=0.05,
        )

        assert result.samples_used == 5
        assert result.mse >= 0
        assert 0.0 <= result.offset <= 5.0
        assert 0.1 <= result.scale <= 1.0

    def test_calibration_fallback_empty_samples(self) -> None:
        """Test that calibration returns defaults with no samples."""
        result = grid_search_calibrate([])

        assert result.offset == 2.0
        assert result.scale == 0.5
        assert result.mse == 0.0
        assert result.samples_used == 0

    def test_calibration_with_perfect_data(self) -> None:
        """Test calibration with data that perfectly matches sigmoid."""
        # Generate perfect sigmoid data
        samples = []
        for raw in range(0, 20, 2):
            human_score = _sigmoid(raw, 2.0, 0.5)
            samples.append((raw, human_score))

        result = grid_search_calibrate(samples)

        # Should find parameters close to the true values
        assert abs(result.offset - 2.0) < 0.5
        assert abs(result.scale - 0.5) < 0.1
        assert result.mse < 0.01


class TestCalibrationResult:
    """Tests for CalibrationResult dataclass."""

    def test_calibration_result_creation(self) -> None:
        """Test CalibrationResult can be created."""
        result = CalibrationResult(offset=2.5, scale=0.6, mse=0.05, samples_used=50)

        assert result.offset == 2.5
        assert result.scale == 0.6
        assert result.mse == 0.05
        assert result.samples_used == 50
