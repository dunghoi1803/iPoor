"""Drop policy household and access level"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251223_0003"
down_revision = "20251223_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE policies DROP FOREIGN KEY policies_ibfk_1")
    op.drop_column("policies", "household_id")
    op.drop_column("policies", "access_level")


def downgrade() -> None:
    op.add_column(
        "policies",
        sa.Column("access_level", sa.Enum("public", "internal", name="policyaccesslevel"), nullable=True),
    )
    op.add_column("policies", sa.Column("household_id", sa.Integer(), nullable=True))
    op.execute(
        "ALTER TABLE policies "
        "ADD CONSTRAINT policies_ibfk_1 "
        "FOREIGN KEY (household_id) REFERENCES households (id)"
    )
