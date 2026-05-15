"""Add human_score, features columns and unique constraint on h3_index.

Revision ID: 003
Revises: 002
Create Date: 2026-05-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add human_score, features columns and unique constraint on h3_index."""

    op.add_column(
        "spots_annotated",
        sa.Column("human_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "spots_annotated",
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_unique_constraint(
        "uq_spots_annotated_h3_index", "spots_annotated", ["h3_index"]
    )


def downgrade() -> None:
    """Drop unique constraint, human_score, and features columns."""

    op.drop_constraint("uq_spots_annotated_h3_index", "spots_annotated", type_="unique")
    op.drop_column("spots_annotated", "features")
    op.drop_column("spots_annotated", "human_score")
