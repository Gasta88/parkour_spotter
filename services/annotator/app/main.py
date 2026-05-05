"""FastAPI application for annotator service."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.routers import health, spots

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Parkour Spotter Annotator",
        description="Annotation UI backend service",
        version="0.1.0",
    )

    app.include_router(health.router)
    app.include_router(spots.router)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    return app


app = create_app()
