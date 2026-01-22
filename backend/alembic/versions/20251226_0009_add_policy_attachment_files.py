"""Add policy attachment files.

Revision ID: 20251226_0009
Revises: 20251225_1026
Create Date: 2025-12-26 00:09:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20251226_0009"
down_revision = "20251225_1026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("policies", sa.Column("attachment_files", sa.JSON(), nullable=True))
    op.add_column("policy_drafts", sa.Column("attachment_files", sa.JSON(), nullable=True))
    op.drop_column("policies", "attachment_url")
    op.drop_column("policy_drafts", "attachment_url")


def downgrade() -> None:
    op.add_column("policy_drafts", sa.Column("attachment_url", sa.String(length=1024), nullable=True))
    op.add_column("policies", sa.Column("attachment_url", sa.String(length=1024), nullable=True))
    op.drop_column("policy_drafts", "attachment_files")
    op.drop_column("policies", "attachment_files")
