"""Add FULLTEXT indexes for chatbot search optimization

Revision ID: 20260504_0001_chatbot_fts
Revises: 20260503_0012
Create Date: 2026-05-04 09:00:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260504_0001_chatbot_fts"
down_revision: Union[str, None] = "20260503_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if FULLTEXT already exists, if not add it
    op.execute("ALTER TABLE policies ADD FULLTEXT INDEX ix_policies_fts (title, summary, description)")
    op.execute("ALTER TABLE dashboard_aggregates ADD FULLTEXT INDEX ix_dashboard_agg_fts (scope_name)")


def downgrade() -> None:
    op.execute("DROP INDEX ix_policies_fts ON policies")
    op.execute("DROP INDEX ix_dashboard_agg_fts ON dashboard_aggregates")