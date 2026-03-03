"""add pib to organizations

Revision ID: a1b2c3d4e5f6
Revises: d4b8f3a1e5c7
Create Date: 2026-03-03 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "d4b8f3a1e5c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add pib column to organizations table."""
    op.add_column("organizations", sa.Column("pib", sa.String(20), nullable=True))
    op.create_index("ix_organizations_pib", "organizations", ["pib"])


def downgrade() -> None:
    """Remove pib column from organizations table."""
    op.drop_index("ix_organizations_pib", table_name="organizations")
    op.drop_column("organizations", "pib")
