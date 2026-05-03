"""Add risk scoring tables for dashboard explanations

Revision ID: 20260503_0011
Revises: 20260502_0010
Create Date: 2026-05-03 10:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260503_0011"
down_revision: Union[str, None] = "20260502_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "household_risk_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("survey_year", sa.Integer(), nullable=False),
        sa.Column("predicted_for_year", sa.Integer(), nullable=False),
        sa.Column("scope_region", sa.String(length=120), nullable=True),
        sa.Column("scope_province", sa.String(length=120), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_band", sa.String(length=24), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_household_risk_scores_household_id", "household_risk_scores", ["household_id"])
    op.create_index("ix_household_risk_scores_predicted_for_year", "household_risk_scores", ["predicted_for_year"])
    op.create_index("ix_household_risk_scores_scope_province", "household_risk_scores", ["scope_province"])
    op.create_index("ix_household_risk_scores_scope_region", "household_risk_scores", ["scope_region"])
    op.create_index("ix_household_risk_scores_risk_band", "household_risk_scores", ["risk_band"])
    op.create_index(
        "ix_risk_household_target_year",
        "household_risk_scores",
        ["household_id", "predicted_for_year"],
        unique=True,
    )

    op.create_table(
        "risk_reason_aggregates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("scope_name", sa.String(length=120), nullable=False),
        sa.Column("predicted_for_year", sa.Integer(), nullable=False),
        sa.Column("reason_key", sa.String(length=64), nullable=False),
        sa.Column("reason_label", sa.String(length=255), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("affected_households", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_risk_reason_aggregates_scope_name", "risk_reason_aggregates", ["scope_name"])
    op.create_index("ix_risk_reason_aggregates_scope_type", "risk_reason_aggregates", ["scope_type"])
    op.create_index("ix_risk_reason_aggregates_predicted_for_year", "risk_reason_aggregates", ["predicted_for_year"])
    op.create_index(
        "ix_reason_scope_year_key",
        "risk_reason_aggregates",
        ["scope_type", "scope_name", "predicted_for_year", "reason_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_reason_scope_year_key", table_name="risk_reason_aggregates")
    op.drop_index("ix_risk_reason_aggregates_predicted_for_year", table_name="risk_reason_aggregates")
    op.drop_index("ix_risk_reason_aggregates_scope_type", table_name="risk_reason_aggregates")
    op.drop_index("ix_risk_reason_aggregates_scope_name", table_name="risk_reason_aggregates")
    op.drop_table("risk_reason_aggregates")

    op.drop_index("ix_risk_household_target_year", table_name="household_risk_scores")
    op.drop_index("ix_household_risk_scores_risk_band", table_name="household_risk_scores")
    op.drop_index("ix_household_risk_scores_scope_region", table_name="household_risk_scores")
    op.drop_index("ix_household_risk_scores_scope_province", table_name="household_risk_scores")
    op.drop_index("ix_household_risk_scores_predicted_for_year", table_name="household_risk_scores")
    op.drop_index("ix_household_risk_scores_household_id", table_name="household_risk_scores")
    op.drop_table("household_risk_scores")
