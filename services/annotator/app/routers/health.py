"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Check service health.

    Returns:
        Health status with service name and version
    """
    return HealthResponse(
        status="ok",
        service="annotator",
        version="0.1.0",
    )
