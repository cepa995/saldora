"""add subscription_status column to organizations

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add subscription_status column to organizations."""
    op.add_column(
        "organizations",
        sa.Column("subscription_status", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Remove subscription_status column from organizations."""
    op.drop_column("organizations", "subscription_status")
