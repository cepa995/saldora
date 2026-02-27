"""add tax_groups column to invoices

Revision ID: b8e3f1a2c4d6
Revises: a77f4d34a5a3
Create Date: 2026-02-26 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e3f1a2c4d6"
down_revision: str | Sequence[str] | None = "a77f4d34a5a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("invoices", sa.Column("tax_groups", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("invoices", "tax_groups")
