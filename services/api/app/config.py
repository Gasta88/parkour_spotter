"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Attributes:
        database_url: PostgreSQL connection URL
        h3_resolution: H3 grid resolution level
        feature_weights: Dict mapping feature category name to scoring weight
        spatial_alpha: Weight for spatial smoothing (0.0-1.0)
        diversity_bonus: Bonus multiplier for feature diversity
        sigmoid_offset: Offset for sigmoid normalization
        sigmoid_scale: Scale for sigmoid normalization
        min_calibration_samples: Minimum samples required for calibration
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    h3_resolution: int = 11

    # Feature weights for all 12 categories
    feature_weights: dict[str, float] = {
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

    # Geometry metric weights
    length_weights: dict[str, float] = {
        "walls": 0.05,
        "steps": 0.05,
        "rails_fences": 0.04,
        "bridges": 0.04,
    }

    area_weights: dict[str, float] = {
        "playgrounds": 0.02,
        "parking": 0.015,
        "sports_pitches": 0.02,
        "rocks_stones": 0.01,
    }

    # Sigmoid normalization parameters
    sigmoid_offset: float = 2.0
    sigmoid_scale: float = 0.5

    # Diversity bonus multiplier
    diversity_bonus: float = 0.3

    # Spatial smoothing weight
    spatial_alpha: float = 0.7

    # Calibration settings
    min_calibration_samples: int = 30


settings = Settings()
