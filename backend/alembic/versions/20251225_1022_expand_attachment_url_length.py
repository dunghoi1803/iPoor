"""Expand attachment_url length.

Revision ID: 20251225_1022
Revises: 20251225_0008
Create Date: 2025-12-25 10:22:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20251225_1022"
down_revision = "20251225_0008"
branch_labels = None
depends_on = None

NEW_LENGTH = 1024


def upgrade() -> None:
    op.alter_column(
        "policies",
        "attachment_url",
        existing_type=sa.String(length=255),
        type_=sa.String(length=NEW_LENGTH),
        existing_nullable=True,
    )
    op.alter_column(
        "policy_drafts",
        "attachment_url",
        existing_type=sa.String(length=255),
        type_=sa.String(length=NEW_LENGTH),
        existing_nullable=True,
    )
    op.alter_column(
        "households",
        "attachment_url",
        existing_type=sa.String(length=255),
        type_=sa.String(length=NEW_LENGTH),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "households",
        "attachment_url",
        existing_type=sa.String(length=NEW_LENGTH),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "policy_drafts",
        "attachment_url",
        existing_type=sa.String(length=NEW_LENGTH),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "policies",
        "attachment_url",
        existing_type=sa.String(length=NEW_LENGTH),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
