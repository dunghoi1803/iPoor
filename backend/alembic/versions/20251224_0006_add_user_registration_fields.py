"""add user registration fields

Revision ID: 20251224_0006
Revises: 20251223_0005
Create Date: 2025-12-24 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20251224_0006"
down_revision = "20251223_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("org_level", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("org_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("position", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("cccd", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("cccd_image_url", sa.String(length=255), nullable=True))
    op.create_index("ix_users_cccd", "users", ["cccd"])


def downgrade() -> None:
    op.drop_index("ix_users_cccd", table_name="users")
    op.drop_column("users", "cccd_image_url")
    op.drop_column("users", "cccd")
    op.drop_column("users", "position")
    op.drop_column("users", "org_name")
    op.drop_column("users", "org_level")
