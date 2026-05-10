"""Spots CRUD endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
from datetime import datetime

from common.models import SpotAnnotation
from app.db import get_db

router = APIRouter(prefix="/spots", tags=["spots"])


class Spot(BaseModel):
    """Annotation spot schema."""

    id: int | None = None
    h3_index: str
    notes: str = ""
    rating: int = 0
    feature_summary: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SpotCreate(BaseModel):
    """Spot creation schema."""

    h3_index: str
    notes: str = ""
    rating: int = 0
    feature_summary: dict[str, Any] | None = None


class SpotUpdate(BaseModel):
    """Spot update schema."""

    notes: str | None = None
    rating: int | None = None
    feature_summary: dict[str, Any] | None = None


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
    if spot.rating < 0 or spot.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")

    db_spot = SpotAnnotation(
        h3_index=spot.h3_index,
        notes=spot.notes,
        rating=spot.rating,
        feature_summary=spot.feature_summary,
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
        HTTPException: If spot not found or rating out of range
    """
    result = await db.execute(
        select(SpotAnnotation).where(SpotAnnotation.id == spot_id)
    )
    spot = result.scalar_one_or_none()
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    if spot_update.rating is not None:
        if spot_update.rating < 0 or spot_update.rating > 5:
            raise HTTPException(
                status_code=400, detail="Rating must be between 0 and 5"
            )
        spot.rating = spot_update.rating

    if spot_update.notes is not None:
        spot.notes = spot_update.notes

    if spot_update.feature_summary is not None:
        spot.feature_summary = spot_update.feature_summary

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
