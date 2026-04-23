"""Backfill due_date to invoice_date where due_date is null.

From the product semantics: an invoice without an explicit payment term is
interpreted as due the same day it was issued (cash / POS receipts). The
OCR worker now applies this at finalization for new invoices; this
migration aligns historical rows so past-due detection is consistent
across the whole dataset.

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-22
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE invoices
        SET due_date = invoice_date
        WHERE due_date IS NULL
          AND invoice_date IS NOT NULL
        """
    )


def downgrade() -> None:
    # Intentional no-op: we can't tell which rows were previously null vs
    # which genuinely had due_date == invoice_date. Leaving both states as
    # "explicit same-day" is safe for all downstream consumers.
    pass
