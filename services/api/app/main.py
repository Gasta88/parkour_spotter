"""FastAPI application factory."""

from fastapi import FastAPI

from app.routers import analyze, health


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Parkour Spotter API",
        description="API for analyzing parkour spots",
        version="0.1.0",
    )

    app.include_router(health.router)
    app.include_router(analyze.router)

    return app


app = create_app()
