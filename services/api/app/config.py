"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings.

    Attributes:
        database_url: PostgreSQL connection URL
        h3_resolution: H3 grid resolution level
    """

    database_url: str
    h3_resolution: int = 11

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
