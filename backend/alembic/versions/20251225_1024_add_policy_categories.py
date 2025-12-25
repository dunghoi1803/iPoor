"""Add news and announcement policy categories.

Revision ID: 20251225_1024
Revises: 20251225_1022
Create Date: 2025-12-25 10:24:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20251225_1024"
down_revision = "20251225_1022"
branch_labels = None
depends_on = None

OLD_ENUM_VALUES = ("decree", "circular", "report", "guideline")
NEW_ENUM_VALUES = ("decree", "circular", "report", "guideline", "news", "announcement")


def _alter_enum(table: str, nullable: bool, values: tuple[str, ...]) -> None:
    enum_list = ", ".join(f"'{value}'" for value in values)
    nullable_sql = "NULL" if nullable else "NOT NULL"
    op.execute(
        f"ALTER TABLE {table} MODIFY COLUMN category ENUM({enum_list}) {nullable_sql}"
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        _alter_enum("policies", nullable=False, values=NEW_ENUM_VALUES)
        _alter_enum("policy_drafts", nullable=True, values=NEW_ENUM_VALUES)
        return
    op.alter_column(
        "policies",
        "category",
        existing_type=sa.Enum(*OLD_ENUM_VALUES, name="policycategory"),
        type_=sa.Enum(*NEW_ENUM_VALUES, name="policycategory"),
        existing_nullable=False,
    )
    op.alter_column(
        "policy_drafts",
        "category",
        existing_type=sa.Enum(*OLD_ENUM_VALUES, name="policycategory"),
        type_=sa.Enum(*NEW_ENUM_VALUES, name="policycategory"),
        existing_nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        _alter_enum("policy_drafts", nullable=True, values=OLD_ENUM_VALUES)
        _alter_enum("policies", nullable=False, values=OLD_ENUM_VALUES)
        return
    op.alter_column(
        "policy_drafts",
        "category",
        existing_type=sa.Enum(*NEW_ENUM_VALUES, name="policycategory"),
        type_=sa.Enum(*OLD_ENUM_VALUES, name="policycategory"),
        existing_nullable=True,
    )
    op.alter_column(
        "policies",
        "category",
        existing_type=sa.Enum(*NEW_ENUM_VALUES, name="policycategory"),
        type_=sa.Enum(*OLD_ENUM_VALUES, name="policycategory"),
        existing_nullable=False,
    )
