"""Analyze endpoint for parkour spot analysis."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.analyze import AnalyzeResponse

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


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze an area for parkour spots.

    Args:
        request: Analysis request with coordinates and radius

    Returns:
        Analysis response with scored H3 cells
    """
    from common.h3_utils import latlng_to_h3, h3_to_latlng

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

    return AnalyzeResponse(
        cells=[cell],
        data_version="unknown",
        query_time_ms=0,
    )
