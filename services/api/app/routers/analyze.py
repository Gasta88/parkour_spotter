"""Analyze endpoint for parkour spot analysis."""

import asyncpg
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.schemas.analyze import AnalyzeResponse, DataVersion
from app.services.scorer_pipeline import ScorerPipeline

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request schema for analyze endpoint.

    Attributes:
        lat: Latitude coordinate
        lon: Longitude coordinate
        radius_km: Search radius in kilometers
    """

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    radius_km: float = Field(..., gt=0, le=10, description="Radius in kilometers")


async def get_latest_data_version() -> DataVersion | None:
    """Query the latest data version from the database.

    Returns:
        DataVersion object if available, None otherwise
    """
    try:
        db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)
        try:
            row = await conn.fetchrow(
                "SELECT loaded_at, osm_source_url, file_size_mb FROM data_version ORDER BY loaded_at DESC LIMIT 1"
            )
            if row:
                return DataVersion(
                    loaded_at=row["loaded_at"],
                    osm_source_url=row["osm_source_url"],
                    file_size_mb=row["file_size_mb"],
                )
            return None
        finally:
            await conn.close()
    except Exception:
        return None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze an area for parkour spots.

    Extracts OSM features from PostGIS, aggregates them into H3 hexagons,
    scores each cell using the rule-based scorer, and returns the results
    with feature breakdowns.

    Args:
        request: Analysis request with coordinates and radius

    Returns:
        Analysis response with scored H3 cells and feature breakdowns
    """
    # Create engine for this request (lightweight, uses connection pooling)
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )

    try:
        # Run the full scorer pipeline: extract features → score cells
        pipeline = ScorerPipeline(engine, resolution=settings.h3_resolution)
        cells, query_time_ms = await pipeline.analyze(
            lat=request.lat,
            lon=request.lon,
            radius_km=request.radius_km,
        )

        # Fetch data version metadata
        data_version = await get_latest_data_version()

        return AnalyzeResponse(
            cells=cells,
            data_version=data_version,
            query_time_ms=query_time_ms,
        )
    finally:
        await engine.dispose()
