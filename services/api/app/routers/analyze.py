"""Analyze endpoint for parkour spot analysis."""

import asyncpg
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas.analyze import AnalyzeResponse, DataVersion

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

    Args:
        request: Analysis request with coordinates and radius

    Returns:
        Analysis response with scored H3 cells
    """
    from common.h3_utils import latlng_to_h3, h3_to_latlng
    import time

    start_time = time.time()

    h3_index = latlng_to_h3(request.lat, request.lon)
    centroid = h3_to_latlng(h3_index)

    cell = {
        "h3_index": h3_index,
        "score": 0.75,
        "centroid": {
            "lat": centroid[0],
            "lon": centroid[1],
        },
    }

    data_version = await get_latest_data_version()
    
    query_time_ms = int((time.time() - start_time) * 1000)

    return AnalyzeResponse(
        cells=[cell],
        data_version=data_version,
        query_time_ms=query_time_ms,
    )
