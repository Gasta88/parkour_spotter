"""Create Phase 2 tables: cell_feature, model, model_evaluation, training_run.

Revision ID: 002
Revises: 001
Create Date: 2026-05-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 2 tables."""

    op.create_table(
        "cell_feature",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("h3_index", sa.String(length=16), nullable=False),
        sa.Column("osm_file_hash", sa.String(), nullable=False),
        sa.Column("walls_count", sa.Integer(), default=0, nullable=False),
        sa.Column("walls_total_length_m", sa.Float(), default=0.0, nullable=False),
        sa.Column("rails_count", sa.Integer(), default=0, nullable=False),
        sa.Column("rails_total_length_m", sa.Float(), default=0.0, nullable=False),
        sa.Column("gaps_count", sa.Integer(), default=0, nullable=False),
        sa.Column("gaps_total_length_m", sa.Float(), default=0.0, nullable=False),
        sa.Column("stairs_count", sa.Integer(), default=0, nullable=False),
        sa.Column("stairs_total_length_m", sa.Float(), default=0.0, nullable=False),
        sa.Column("vaults_count", sa.Integer(), default=0, nullable=False),
        sa.Column("vaults_total_area_m2", sa.Float(), default=0.0, nullable=False),
        sa.Column("open_spaces_count", sa.Integer(), default=0, nullable=False),
        sa.Column("open_spaces_total_area_m2", sa.Float(), default=0.0, nullable=False),
        sa.Column("h3_res8_parent", sa.String(length=15), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("h3_index", "osm_file_hash", name="uq_cell_feature_h3_osm"),
    )
    op.create_index("ix_cell_feature_h3_index", "cell_feature", ["h3_index"])
    op.create_index("ix_cell_feature_osm_file_hash", "cell_feature", ["osm_file_hash"])
    op.create_index("ix_cell_feature_res8_parent", "cell_feature", ["h3_res8_parent"])

    op.create_table(
        "model",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_type", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("feature_list", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "hyperparameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("is_active", sa.Boolean(), default=False, nullable=False),
        sa.Column("status", sa.String(), default="pending", nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_model_name_version"),
    )
    op.create_index("ix_model_model_type", "model", ["model_type"])
    op.create_index("ix_model_name", "model", ["name"])
    op.create_index("ix_model_is_active", "model", ["is_active"])

    op.create_table(
        "model_evaluation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("roc_auc", sa.Float(), nullable=True),
        sa.Column(
            "confusion_matrix", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "feature_importance", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["model.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_evaluation_model_id", "model_evaluation", ["model_id"])

    op.create_table(
        "training_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "train_test_split", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("status", sa.String(), default="running", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["model.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["model_evaluation.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_run_model_id", "training_run", ["model_id"])
    op.create_index("ix_training_run_evaluation_id", "training_run", ["evaluation_id"])
    op.create_index("ix_training_run_status", "training_run", ["status"])


def downgrade() -> None:
    """Drop Phase 2 tables."""
    op.drop_index("ix_training_run_status", table_name="training_run")
    op.drop_index("ix_training_run_evaluation_id", table_name="training_run")
    op.drop_index("ix_training_run_model_id", table_name="training_run")
    op.drop_table("training_run")

    op.drop_index("ix_model_evaluation_model_id", table_name="model_evaluation")
    op.drop_table("model_evaluation")

    op.drop_index("ix_model_is_active", table_name="model")
    op.drop_index("ix_model_name", table_name="model")
    op.drop_index("ix_model_model_type", table_name="model")
    op.drop_table("model")

    op.drop_index("ix_cell_feature_res8_parent", table_name="cell_feature")
    op.drop_index("ix_cell_feature_osm_file_hash", table_name="cell_feature")
    op.drop_index("ix_cell_feature_h3_index", table_name="cell_feature")
    op.drop_table("cell_feature")
