"""Add flipbook_url to policies and policy_drafts.

Revision ID: 20251225_1026
Revises: 20251225_1024
Create Date: 2025-12-25 10:26:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20251225_1026"
down_revision = "20251225_1024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("policies", sa.Column("flipbook_url", sa.String(length=1024), nullable=True))
    op.add_column("policy_drafts", sa.Column("flipbook_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("policy_drafts", "flipbook_url")
    op.drop_column("policies", "flipbook_url")
