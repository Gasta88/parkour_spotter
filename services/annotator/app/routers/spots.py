"""Spots CRUD endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/spots", tags=["spots"])


class Spot(BaseModel):
    """Annotation spot schema."""

    id: int | None = None
    h3_index: str
    notes: str = ""
    rating: float = 0.0


class SpotCreate(BaseModel):
    """Spot creation schema."""

    h3_index: str
    notes: str = ""
    rating: float = 0.0


spots_store: list[Spot] = []


@router.get("", response_model=list[Spot])
def list_spots() -> list[Spot]:
    """List all annotation spots.

    Returns:
        List of all spots
    """
    return spots_store


@router.post("", response_model=Spot)
def create_spot(spot: SpotCreate) -> Spot:
    """Create a new annotation spot.

    Args:
        spot: Spot data to create

    Returns:
        Created spot with ID
    """
    new_spot = Spot(
        id=len(spots_store) + 1,
        h3_index=spot.h3_index,
        notes=spot.notes,
        rating=spot.rating,
    )
    spots_store.append(new_spot)
    return new_spot
