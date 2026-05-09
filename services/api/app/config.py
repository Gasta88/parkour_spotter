"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Attributes:
        database_url: PostgreSQL connection URL
        h3_resolution: H3 grid resolution level
        feature_weights: Dict mapping feature category name to scoring weight
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    h3_resolution: int = 11
    feature_weights: dict[str, float] = {
        "walls": 1.0,
        "steps": 1.0,
        "rails_fences": 0.8,
        "playgrounds": 1.2,
        "parking": 0.6,
        "benches_blocks": 0.5,
        "fitness_stations": 0.7,
        "private_access_penalty": -1.0,
    }


settings = Settings()
