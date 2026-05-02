"""Add dashboard aggregate table and query indexes

Revision ID: 20260502_0010
Revises: e56b844fc070
Create Date: 2026-05-02 13:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.constants import PovertyStatus


revision: str = "20260502_0010"
down_revision: Union[str, None] = "e56b844fc070"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboard_aggregates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("scope_name", sa.String(length=120), nullable=False),
        sa.Column("survey_year", sa.Integer(), nullable=False),
        sa.Column("poverty_status", sa.Enum(PovertyStatus), nullable=False),
        sa.Column("household_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_dashboard_agg_scope_year_status",
        "dashboard_aggregates",
        ["scope_type", "scope_name", "survey_year", "poverty_status"],
        unique=True,
    )
    op.create_index("ix_dashboard_agg_year", "dashboard_aggregates", ["survey_year"])

    op.create_index(
        "ix_survey_year_status_household",
        "household_surveys",
        ["survey_year", "poverty_status", "household_id"],
        unique=False,
    )
    op.create_index(
        "ix_survey_household_year",
        "household_surveys",
        ["household_id", "survey_year"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_survey_household_year", table_name="household_surveys")
    op.drop_index("ix_survey_year_status_household", table_name="household_surveys")
    op.drop_index("ix_dashboard_agg_year", table_name="dashboard_aggregates")
    op.drop_index("ix_dashboard_agg_scope_year_status", table_name="dashboard_aggregates")
    op.drop_table("dashboard_aggregates")
