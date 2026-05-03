"""Add ml training runs history table

Revision ID: 20260503_0012
Revises: 20260503_0011
Create Date: 2026-05-03 11:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260503_0012"
down_revision: Union[str, None] = "20260503_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_training_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("schedule_type", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("predicted_for_year", sa.Integer(), nullable=True),
        sa.Column("pr_auc", sa.Float(), nullable=True),
        sa.Column("train_rows", sa.Integer(), nullable=True),
        sa.Column("prediction_rows", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_ml_training_runs_model_version", "ml_training_runs", ["model_version"])
    op.create_index("ix_ml_training_runs_status", "ml_training_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ml_training_runs_status", table_name="ml_training_runs")
    op.drop_index("ix_ml_training_runs_model_version", table_name="ml_training_runs")
    op.drop_table("ml_training_runs")
