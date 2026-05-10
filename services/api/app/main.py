"""FastAPI application factory."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import settings
from app.routers import analyze, health
from app.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Parkour Spotter API",
        description="API for analyzing parkour spots",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(analyze.router)

    return app


app = create_app()
