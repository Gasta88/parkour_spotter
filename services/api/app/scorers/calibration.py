"""Calibration module for rule-based scorer.

Provides grid-search optimization for sigmoid offset/scale parameters
against human-annotated labels.
"""

import math
from dataclasses import dataclass


@dataclass
class CalibrationResult:
    """Result of calibration optimization."""

    offset: float
    scale: float
    mse: float
    samples_used: int


def grid_search_calibrate(
    samples: list[tuple[float, float]],
    offset_range: tuple[float, float] = (0.0, 5.0),
    offset_step: float = 0.25,
    scale_range: tuple[float, float] = (0.1, 1.0),
    scale_step: float = 0.05,
) -> CalibrationResult:
    """Grid search for optimal sigmoid offset and scale.

    Searches over a grid of (offset, scale) parameter combinations
    to find the pair that minimizes MSE between predicted and human scores.

    Args:
        samples: List of (raw_score, human_score) tuples
        offset_range: (min, max) range for offset search
        offset_step: Step size for offset grid
        scale_range: (min, max) range for scale search
        scale_step: Step size for scale grid

    Returns:
        CalibrationResult with best offset, scale, MSE, and sample count
    """
    if not samples:
        return CalibrationResult(
            offset=2.0,
            scale=0.5,
            mse=0.0,
            samples_used=0,
        )

    best_offset = 2.0
    best_scale = 0.5
    best_mse = float("inf")

    offset_min, offset_max = offset_range
    scale_min, scale_max = scale_range

    offset = offset_min
    while offset <= offset_max:
        scale = scale_min
        while scale <= scale_max:
            mse = _compute_mse(samples, offset, scale)
            if mse < best_mse:
                best_mse = mse
                best_offset = offset
                best_scale = scale
            scale += scale_step
        offset += offset_step

    return CalibrationResult(
        offset=best_offset,
        scale=best_scale,
        mse=best_mse,
        samples_used=len(samples),
    )


def _compute_mse(
    samples: list[tuple[float, float]], offset: float, scale: float
) -> float:
    """Compute mean squared error for given sigmoid parameters.

    Args:
        samples: List of (raw_score, human_score) tuples
        offset: Sigmoid offset parameter
        scale: Sigmoid scale parameter

    Returns:
        Mean squared error between predicted and human scores
    """
    if not samples:
        return 0.0

    total_error = 0.0
    for raw_score, human_score in samples:
        predicted = _sigmoid(raw_score, offset, scale)
        error = (predicted - human_score) ** 2
        total_error += error

    return total_error / len(samples)


def _sigmoid(x: float, offset: float, scale: float) -> float:
    """Sigmoid function with configurable parameters.

    Args:
        x: Input value (raw score)
        offset: Sigmoid offset
        scale: Sigmoid scale

    Returns:
        Normalized score in [0, 1]
    """
    normalized_x = (x - offset) * scale
    return 1.0 / (1.0 + math.exp(-normalized_x))
