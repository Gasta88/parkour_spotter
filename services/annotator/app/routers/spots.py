"""Spots CRUD endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
from datetime import datetime

from common.models import SpotAnnotation, CellFeature
from app.db import get_db

router = APIRouter(prefix="/spots", tags=["spots"])


class Spot(BaseModel):
    """Annotation spot schema."""

    id: int | None = None
    h3_index: str
    notes: str = ""
    rating: int = 0
    human_score: float | None = None
    features: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SpotCreate(BaseModel):
    """Spot creation schema."""

    h3_index: str
    notes: str = ""
    rating: int = Field(..., ge=0, le=5)
    features: dict[str, Any] | None = None


class SpotUpdate(BaseModel):
    """Spot update schema."""

    notes: str | None = None
    rating: int | None = Field(None, ge=0, le=5)
    features: dict[str, Any] | None = None


@router.get("", response_model=list[Spot])
async def list_spots(db: AsyncSession = Depends(get_db)) -> list[Spot]:
    """List all annotation spots.

    Args:
        db: Database session

    Returns:
        List of all spots
    """
    result = await db.execute(select(SpotAnnotation))
    spots = result.scalars().all()
    return [Spot.model_validate(spot) for spot in spots]


@router.post("", response_model=Spot)
async def create_spot(spot: SpotCreate, db: AsyncSession = Depends(get_db)) -> Spot:
    """Create a new annotation spot.

    Args:
        spot: Spot data to create
        db: Database session

    Returns:
        Created spot with ID
    """
    db_spot = SpotAnnotation(
        h3_index=spot.h3_index,
        notes=spot.notes,
        rating=spot.rating,
        human_score=float(spot.rating),
        features=spot.features,
    )
    db.add(db_spot)
    await db.commit()
    await db.refresh(db_spot)
    return Spot.model_validate(db_spot)


@router.get("/{spot_id}", response_model=Spot)
async def get_spot(spot_id: int, db: AsyncSession = Depends(get_db)) -> Spot:
    """Get a specific annotation spot by ID.

    Args:
        spot_id: Spot ID
        db: Database session

    Returns:
        Spot with given ID

    Raises:
        HTTPException: If spot not found
    """
    result = await db.execute(
        select(SpotAnnotation).where(SpotAnnotation.id == spot_id)
    )
    spot = result.scalar_one_or_none()
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    return Spot.model_validate(spot)


@router.put("/{spot_id}", response_model=Spot)
async def update_spot(
    spot_id: int, spot_update: SpotUpdate, db: AsyncSession = Depends(get_db)
) -> Spot:
    """Update an existing annotation spot.

    Args:
        spot_id: Spot ID
        spot_update: Updated spot data
        db: Database session

    Returns:
        Updated spot

    Raises:
        HTTPException: If spot not found
    """
    result = await db.execute(
        select(SpotAnnotation).where(SpotAnnotation.id == spot_id)
    )
    spot = result.scalar_one_or_none()
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    if spot_update.rating is not None:
        spot.rating = spot_update.rating
        spot.human_score = float(spot_update.rating)

    if spot_update.notes is not None:
        spot.notes = spot_update.notes

    if spot_update.features is not None:
        spot.features = spot_update.features

    await db.commit()
    await db.refresh(spot)
    return Spot.model_validate(spot)


@router.delete("/{spot_id}", status_code=204)
async def delete_spot(spot_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an annotation spot.

    Args:
        spot_id: Spot ID
        db: Database session

    Raises:
        HTTPException: If spot not found
    """
    result = await db.execute(
        select(SpotAnnotation).where(SpotAnnotation.id == spot_id)
    )
    spot = result.scalar_one_or_none()
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    await db.delete(spot)
    await db.commit()


@router.get("/cell-feature/{h3_index}")
async def get_cell_feature(h3_index: str, db: AsyncSession = Depends(get_db)):
    """Get cell feature data for a given H3 index.

    Args:
        h3_index: H3 index to fetch features for
        db: Database session

    Returns:
        Cell feature data in nested JSON format

    Raises:
        HTTPException: If no cell features found for the H3 index
    """
    result = await db.execute(
        select(CellFeature)
        .where(CellFeature.h3_index == h3_index)
        .order_by(CellFeature.created_at.desc())
    )
    cell_feature = result.scalar_one_or_none()

    if cell_feature is None:
        raise HTTPException(
            status_code=404, detail="No cell features found for this H3 index"
        )

    features = {
        "walls": {
            "count": cell_feature.walls_count,
            "total_length_m": cell_feature.walls_total_length_m,
            "total_area_m2": 0.0,
        },
        "rails": {
            "count": cell_feature.rails_count,
            "total_length_m": cell_feature.rails_total_length_m,
            "total_area_m2": 0.0,
        },
        "gaps": {
            "count": cell_feature.gaps_count,
            "total_length_m": cell_feature.gaps_total_length_m,
            "total_area_m2": 0.0,
        },
        "stairs": {
            "count": cell_feature.stairs_count,
            "total_length_m": cell_feature.stairs_total_length_m,
            "total_area_m2": 0.0,
        },
        "vaults": {
            "count": cell_feature.vaults_count,
            "total_length_m": 0.0,
            "total_area_m2": cell_feature.vaults_total_area_m2,
        },
        "open_spaces": {
            "count": cell_feature.open_spaces_count,
            "total_length_m": 0.0,
            "total_area_m2": cell_feature.open_spaces_total_area_m2,
        },
    }

    return {"h3_index": h3_index, "features": features}
