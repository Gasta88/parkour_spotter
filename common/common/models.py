"""Shared SQLAlchemy models and declarative base."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models.

    All models should inherit from this base class.
    """

    pass


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DataVersion(Base, TimestampMixin):
    """Tracks OSM data load history for reproducibility."""

    __tablename__ = "data_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    osm_source_url: Mapped[str] = mapped_column(String, nullable=False)
    osm_file_hash: Mapped[str] = mapped_column(String, nullable=False)
    file_size_mb: Mapped[float] = mapped_column(Float, nullable=False)
    row_counts: Mapped[dict] = mapped_column(JSONB, nullable=False)
    load_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_data_version_loaded_at", "loaded_at"),
        Index("ix_data_version_osm_file_hash", "osm_file_hash"),
    )


class SpotAnnotation(Base, TimestampMixin):
    """Human annotations for H3 hexagons."""

    __tablename__ = "spots_annotated"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    h3_index: Mapped[str] = mapped_column(String(16), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    human_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "rating >= 0 AND rating <= 5", name="ck_spots_annotated_rating_range"
        ),
        Index("ix_spots_annotated_h3_index", "h3_index"),
        UniqueConstraint("h3_index", name="uq_spots_annotated_h3_index"),
    )


class SavedSearch(Base, TimestampMixin):
    """Cached API search queries for analytics and cache lookups."""

    __tablename__ = "saved_search"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[float] = mapped_column(Float, nullable=False)
    cell_count: Mapped[int] = mapped_column(Integer, nullable=False)
    score_distribution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_saved_search_cache_lookup", "lat", "lon", "radius_m"),
        Index("ix_saved_search_created_at", "created_at"),
    )


class CellFeature(Base, TimestampMixin):
    """Pre-computed features for H3 hexagons tied to OSM data version."""

    __tablename__ = "cell_feature"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    h3_index: Mapped[str] = mapped_column(String(16), nullable=False)
    osm_file_hash: Mapped[str] = mapped_column(String, nullable=False)
    walls_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    walls_total_length_m: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    rails_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rails_total_length_m: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    gaps_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gaps_total_length_m: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    stairs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stairs_total_length_m: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    vaults_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vaults_total_area_m2: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    open_spaces_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_spaces_total_area_m2: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    h3_res8_parent: Mapped[str] = mapped_column(String(15), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("h3_index", "osm_file_hash", name="uq_cell_feature_h3_osm"),
        Index("ix_cell_feature_h3_index", "h3_index"),
        Index("ix_cell_feature_osm_file_hash", "osm_file_hash"),
        Index("ix_cell_feature_res8_parent", "h3_res8_parent"),
    )


class Model(Base, TimestampMixin):
    """Registry of trained ML models."""

    __tablename__ = "model"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    model_type: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    feature_list: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    hyperparameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_model_model_type", "model_type"),
        Index("ix_model_name", "name"),
        Index("ix_model_is_active", "is_active"),
        UniqueConstraint("name", "version", name="uq_model_name_version"),
    )


class ModelEvaluation(Base, TimestampMixin):
    """Evaluation metrics for trained models."""

    __tablename__ = "model_evaluation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model.id", ondelete="CASCADE"),
        nullable=False,
    )
    accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    precision: Mapped[float] = mapped_column(Float, nullable=True)
    recall: Mapped[float] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float] = mapped_column(Float, nullable=True)
    roc_auc: Mapped[float] = mapped_column(Float, nullable=True)
    confusion_matrix: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    feature_importance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    model = relationship("Model", back_populates="evaluations")

    __table_args__ = (Index("ix_model_evaluation_model_id", "model_id"),)


class TrainingRun(Base, TimestampMixin):
    """Audit trail for model training runs."""

    __tablename__ = "training_run"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model.id", ondelete="CASCADE"),
        nullable=False,
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_evaluation.id", ondelete="SET NULL"),
        nullable=True,
    )
    train_test_split: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    model = relationship("Model", back_populates="training_runs")
    evaluation = relationship("ModelEvaluation", back_populates="training_run")

    __table_args__ = (
        Index("ix_training_run_model_id", "model_id"),
        Index("ix_training_run_evaluation_id", "evaluation_id"),
        Index("ix_training_run_status", "status"),
    )


Model.evaluations = relationship(
    "ModelEvaluation", order_by=ModelEvaluation.created_at, back_populates="model"
)
Model.training_runs = relationship(
    "TrainingRun", order_by=TrainingRun.created_at, back_populates="model"
)
ModelEvaluation.training_run = relationship(
    "TrainingRun", uselist=False, back_populates="evaluation"
)
