"""Add policy content blocks.

Revision ID: 20251225_0007
Revises: 20251224_0006
Create Date: 2025-12-25 09:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20251225_0007"
down_revision = "20251224_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("policies", sa.Column("content_blocks", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("policies", "content_blocks")
