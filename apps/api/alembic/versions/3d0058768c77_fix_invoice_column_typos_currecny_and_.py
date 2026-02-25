"""fix invoice column typos currecny and document_paht

Revision ID: 3d0058768c77
Revises: 6c35df897832
Create Date: 2026-02-25 14:10:02.389799

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d0058768c77"
down_revision: str | Sequence[str] | None = "6c35df897832"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("invoices", "currecny", new_column_name="currency")
    op.alter_column("invoices", "document_paht", new_column_name="document_path")


def downgrade() -> None:
    op.alter_column("invoices", "currency", new_column_name="currecny")
    op.alter_column("invoices", "document_path", new_column_name="document_paht")
