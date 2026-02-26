"""add raw_llm_output column to invoices

Revision ID: a77f4d34a5a3
Revises: e94adbad28e1
Create Date: 2026-02-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a77f4d34a5a3"
down_revision: str | Sequence[str] | None = "e94adbad28e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("invoices", sa.Column("raw_llm_output", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("invoices", "raw_llm_output")
