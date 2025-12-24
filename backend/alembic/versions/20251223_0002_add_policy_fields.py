"""Add policy summary, tags, access flags"""

from alembic import op
import sqlalchemy as sa

from app.constants import POLICY_SUMMARY_MAX_LENGTH

# revision identifiers, used by Alembic.
revision = "20251223_0002"
down_revision = "20240210_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "policies",
        sa.Column("summary", sa.String(length=POLICY_SUMMARY_MAX_LENGTH), nullable=True),
    )
    op.add_column(
        "policies",
        sa.Column("tags", sa.JSON(), nullable=True),
    )
    op.add_column(
        "policies",
        sa.Column("is_public", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "policies",
        sa.Column("access_level", sa.Enum("public", "internal", name="policyaccesslevel"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("policies", "access_level")
    op.drop_column("policies", "is_public")
    op.drop_column("policies", "tags")
    op.drop_column("policies", "summary")
