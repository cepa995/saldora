"""make organization_id nullable and add logo_key

Revision ID: j0e1f2g3h4i5
Revises: h8c9d0e1f2g3
Create Date: 2026-03-08 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "j0e1f2g3h4i5"
down_revision: str | Sequence[str] | None = "i9d0e1f2g3h4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make users.organization_id nullable and add organizations.logo_key."""
    op.alter_column(
        "users",
        "organization_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.add_column(
        "organizations",
        sa.Column("logo_key", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    """Revert: make organization_id NOT NULL and drop logo_key."""
    op.drop_column("organizations", "logo_key")
    op.alter_column(
        "users",
        "organization_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
