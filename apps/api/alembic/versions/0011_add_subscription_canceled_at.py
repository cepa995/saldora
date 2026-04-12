"""Add subscription_canceled_at to organizations

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add canceled_at timestamp for retention policy calculation."""
    op.add_column(
        "organizations",
        sa.Column("subscription_canceled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove canceled_at column."""
    op.drop_column("organizations", "subscription_canceled_at")
