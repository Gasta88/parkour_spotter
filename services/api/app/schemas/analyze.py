"""Response schemas for analyze endpoint."""

from pydantic import BaseModel, Field


class Centroid(BaseModel):
    """Centroid coordinates."""

    lat: float
    lon: float


class HexCell(BaseModel):
    """H3 hexagon cell with score.

    Attributes:
        h3_index: H3 index string
        score: Parkour suitability score (0-1)
        centroid: Cell centroid coordinates
    """

    h3_index: str
    score: float = Field(..., ge=0, le=1)
    centroid: Centroid


class AnalyzeResponse(BaseModel):
    """Response schema for analyze endpoint.

    Attributes:
        cells: List of scored H3 cells
        data_version: Version of OSM data used
        query_time_ms: Query execution time in milliseconds
    """

    cells: list[HexCell]
    data_version: str
    query_time_ms: int
