"""Add household detail fields and attachment"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251223_0004"
down_revision = "20251223_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("households", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("households", sa.Column("gender", sa.String(length=16), nullable=True))
    op.add_column("households", sa.Column("id_card", sa.String(length=20), nullable=True))
    op.add_column("households", sa.Column("score_b1", sa.Integer(), nullable=True))
    op.add_column("households", sa.Column("score_b2", sa.Integer(), nullable=True))
    op.add_column("households", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("households", sa.Column("area", sa.String(length=120), nullable=True))
    op.add_column("households", sa.Column("village", sa.String(length=255), nullable=True))
    op.add_column("households", sa.Column("officer", sa.String(length=255), nullable=True))
    op.add_column("households", sa.Column("remark", sa.Text(), nullable=True))
    op.add_column("households", sa.Column("attachment_url", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("households", "attachment_url")
    op.drop_column("households", "remark")
    op.drop_column("households", "officer")
    op.drop_column("households", "village")
    op.drop_column("households", "area")
    op.drop_column("households", "note")
    op.drop_column("households", "score_b2")
    op.drop_column("households", "score_b1")
    op.drop_column("households", "id_card")
    op.drop_column("households", "gender")
    op.drop_column("households", "birth_date")
