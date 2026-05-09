"""Hex cell schema."""

from pydantic import BaseModel


class HexCell(BaseModel):
    """H3 hexagon cell.

    Attributes:
        h3_index: H3 index string
        lat: Latitude coordinate
        lon: Longitude coordinate
    """

    h3_index: str
    lat: float
    lon: float
