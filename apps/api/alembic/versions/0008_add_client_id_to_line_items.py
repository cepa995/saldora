"""Add client_id to invoice_line_items for agency client filtering

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add client_id FK and index to invoice_line_items."""
    op.add_column(
        "invoice_line_items",
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_ili_client_id", "invoice_line_items", ["client_id"])

    # Backfill: copy client_id from invoices to line items
    op.execute("""
        UPDATE invoice_line_items ili
        SET client_id = inv.client_id
        FROM invoices inv
        WHERE ili.invoice_id = inv.id
          AND inv.client_id IS NOT NULL
    """)


def downgrade() -> None:
    """Remove client_id from invoice_line_items."""
    op.drop_index("ix_ili_client_id", table_name="invoice_line_items")
    op.drop_column("invoice_line_items", "client_id")
