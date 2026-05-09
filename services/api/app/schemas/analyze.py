"""Response schemas for analyze endpoint."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Centroid(BaseModel):
    """Centroid coordinates."""

    lat: float
    lon: float


class FeatureMetrics(BaseModel):
    """Per-feature category metrics for an H3 cell.

    Attributes:
        count: Number of features in this cell for this category
        total_length_m: Total length in meters (for line features, 0 if not applicable)
        total_area_m2: Total area in square meters (for polygon features, 0 if not applicable)
    """

    count: int = Field(default=0, ge=0)
    total_length_m: float = Field(default=0.0, ge=0.0)
    total_area_m2: float = Field(default=0.0, ge=0.0)


class HexCell(BaseModel):
    """H3 hexagon cell with score and feature breakdown.

    Attributes:
        h3_index: H3 index string
        score: Parkour suitability score (0-1)
        centroid: Cell centroid coordinates
        features: Dict mapping feature category name to its metrics
    """

    h3_index: str
    score: float = Field(..., ge=0, le=1)
    centroid: Centroid
    features: dict[str, FeatureMetrics] = Field(default_factory=dict)


class DataVersion(BaseModel):
    """Data version metadata for OSM data load.

    Attributes:
        loaded_at: Timestamp when data was loaded
        osm_source_url: URL of the OSM data source
        file_size_mb: Size of the downloaded PBF file in MB
    """

    loaded_at: datetime
    osm_source_url: str
    file_size_mb: float


class AnalyzeResponse(BaseModel):
    """Response schema for analyze endpoint.

    Attributes:
        cells: List of scored H3 cells with feature breakdowns
        data_version: Version metadata of OSM data used
        query_time_ms: Query execution time in milliseconds
    """

    cells: list[HexCell]
    data_version: Optional[DataVersion] = None
    query_time_ms: int
