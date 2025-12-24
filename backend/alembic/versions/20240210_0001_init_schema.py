"""Init schema and seed admin user"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa

from app.constants import CollectionStatus, PolicyCategory, PovertyStatus, Roles
from app.utils.security import get_password_hash
from app.config import get_settings

# revision identifiers, used by Alembic.
revision = "20240210_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum(Roles), nullable=False, server_default=Roles.PROVINCE_OFFICER.value),
        sa.Column("province", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column("commune", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )

    op.create_table(
        "households",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("head_name", sa.String(length=255), nullable=False),
        sa.Column("address_line", sa.Text(), nullable=True),
        sa.Column("province", sa.String(length=120), nullable=False),
        sa.Column("district", sa.String(length=120), nullable=False),
        sa.Column("commune", sa.String(length=120), nullable=False),
        sa.Column("poverty_status", sa.Enum(PovertyStatus), nullable=False),
        sa.Column("ethnicity", sa.String(length=120), nullable=True),
        sa.Column("members_count", sa.Integer(), nullable=True),
        sa.Column("income_per_capita", sa.Float(), nullable=True),
        sa.Column("last_surveyed_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.Enum(PolicyCategory), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("issued_by", sa.String(length=255), nullable=True),
        sa.Column("attachment_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )

    op.create_table(
        "data_collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("households.id"), nullable=False),
        sa.Column("collector_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum(CollectionStatus),
            nullable=False,
            server_default=CollectionStatus.DRAFT.value,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # seed admin user
    settings = get_settings()
    admin_email = settings.admin_email
    admin_password = settings.admin_password
    admin_full_name = settings.admin_full_name

    if not admin_email or not admin_password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must be set for initial migration.")

    bind = op.get_bind()
    hashed_password = get_password_hash(admin_password)
    bind.execute(
        sa.text(
            """
            INSERT INTO users (email, full_name, hashed_password, role, is_active, created_at)
            VALUES (:email, :full_name, :hashed_password, :role, :is_active, :created_at)
            ON DUPLICATE KEY UPDATE full_name=VALUES(full_name)
            """
        ),
        {
            "email": admin_email,
            "full_name": admin_full_name,
            "hashed_password": hashed_password,
            "role": Roles.ADMIN.value,
            "is_active": True,
            "created_at": datetime.utcnow(),
        },
    )


def downgrade() -> None:
    op.drop_table("data_collections")
    op.drop_table("activity_logs")
    op.drop_table("policies")
    op.drop_table("households")
    op.drop_table("users")
