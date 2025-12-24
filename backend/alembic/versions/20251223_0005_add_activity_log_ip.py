"""Add ip address to activity logs"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251223_0005"
down_revision = "20251223_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activity_logs", sa.Column("ip_address", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("activity_logs", "ip_address")
