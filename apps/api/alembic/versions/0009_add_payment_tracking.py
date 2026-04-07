"""Add payment tracking fields to invoices

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-05
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add payment_status, paid_amount, paid_date, payment_notes columns."""
    op.add_column(
        "invoices",
        sa.Column(
            "payment_status",
            sa.String(20),
            nullable=False,
            server_default="unpaid",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column("paid_amount", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("paid_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("payment_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_invoices_payment_status", "invoices", ["payment_status"])
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])


def downgrade() -> None:
    """Remove payment tracking columns."""
    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_payment_status", table_name="invoices")
    op.drop_column("invoices", "payment_notes")
    op.drop_column("invoices", "paid_date")
    op.drop_column("invoices", "paid_amount")
    op.drop_column("invoices", "payment_status")
