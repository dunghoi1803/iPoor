"""Add policy drafts.

Revision ID: 20251225_0008
Revises: 20251225_0007
Create Date: 2025-12-25 10:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20251225_0008"
down_revision = "20251225_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("category", sa.Enum("decree", "circular", "report", "guideline", name="policycategory"), nullable=True),
        sa.Column("summary", sa.String(length=300), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_blocks", sa.JSON(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("issued_by", sa.String(length=255), nullable=True),
        sa.Column("attachment_url", sa.String(length=255), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_policy_drafts_id"), "policy_drafts", ["id"], unique=False)
    op.create_index(op.f("ix_policy_drafts_policy_id"), "policy_drafts", ["policy_id"], unique=False)
    op.create_index(op.f("ix_policy_drafts_user_id"), "policy_drafts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_policy_drafts_user_id"), table_name="policy_drafts")
    op.drop_index(op.f("ix_policy_drafts_policy_id"), table_name="policy_drafts")
    op.drop_index(op.f("ix_policy_drafts_id"), table_name="policy_drafts")
    op.drop_table("policy_drafts")
