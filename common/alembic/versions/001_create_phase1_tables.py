"""Create Phase 1 tables: data_version, spots_annotated, saved_search.

Revision ID: 001
Revises:
Create Date: 2026-05-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 1 tables."""

    op.create_table(
        "data_version",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("osm_source_url", sa.String(), nullable=False),
        sa.Column("osm_file_hash", sa.String(), nullable=False),
        sa.Column("file_size_mb", sa.Float(), nullable=False),
        sa.Column(
            "row_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("load_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_version_loaded_at", "data_version", ["loaded_at"])
    op.create_index("ix_data_version_osm_file_hash", "data_version", ["osm_file_hash"])

    op.create_table(
        "spots_annotated",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("h3_index", sa.String(length=16), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), default="", nullable=False),
        sa.Column(
            "feature_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "rating >= 0 AND rating <= 5", name="ck_spots_annotated_rating_range"
        ),
    )
    op.create_index("ix_spots_annotated_h3_index", "spots_annotated", ["h3_index"])

    op.create_table(
        "saved_search",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("radius_m", sa.Float(), nullable=False),
        sa.Column("cell_count", sa.Integer(), nullable=False),
        sa.Column(
            "score_distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_saved_search_cache_lookup", "saved_search", ["lat", "lon", "radius_m"]
    )
    op.create_index("ix_saved_search_created_at", "saved_search", ["created_at"])


def downgrade() -> None:
    """Drop Phase 1 tables."""
    op.drop_index("ix_saved_search_created_at", table_name="saved_search")
    op.drop_index("ix_saved_search_cache_lookup", table_name="saved_search")
    op.drop_table("saved_search")

    op.drop_index("ix_spots_annotated_h3_index", table_name="spots_annotated")
    op.drop_table("spots_annotated")

    op.drop_index("ix_data_version_osm_file_hash", table_name="data_version")
    op.drop_index("ix_data_version_loaded_at", table_name="data_version")
    op.drop_table("data_version")
