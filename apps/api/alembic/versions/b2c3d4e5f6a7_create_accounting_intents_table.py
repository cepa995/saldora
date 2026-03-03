"""create accounting_intents table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-03 10:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the accounting_intents table."""
    op.create_table(
        "accounting_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        # Step 1: Document classification
        sa.Column("document_type", sa.String(30), nullable=False),
        # Step 2: Transaction type
        sa.Column("transaction_type", sa.String(30), nullable=False),
        # Step 3: VAT treatment
        sa.Column("vat_treatment", sa.String(30), nullable=False),
        sa.Column("is_deductible", sa.Boolean(), default=True),
        # Step 4: VAT breakdown and konta
        sa.Column("vat_breakdown", postgresql.JSONB(), server_default="{}"),
        sa.Column("suggested_konta", postgresql.JSONB(), server_default="{}"),
        # Future: Issue #35 and #36
        sa.Column("pdv_book_entries", postgresql.JSONB(), server_default="{}"),
        sa.Column("applied_rules", postgresql.JSONB(), server_default="[]"),
        # Confidence
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False),
        # Review
        sa.Column("requires_review", sa.Boolean(), default=False),
        sa.Column("review_reasons", postgresql.JSONB(), server_default="[]"),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        # Notes
        sa.Column("notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_accounting_intents_invoice_id",
        "accounting_intents",
        ["invoice_id"],
    )
    op.create_index(
        "ix_accounting_intents_organization_id",
        "accounting_intents",
        ["organization_id"],
    )
    op.create_index(
        "ix_accounting_intents_requires_review",
        "accounting_intents",
        ["requires_review"],
        postgresql_where=sa.text("requires_review = true"),
    )
    op.create_index(
        "ix_accounting_intents_doc_txn_type",
        "accounting_intents",
        ["document_type", "transaction_type"],
    )


def downgrade() -> None:
    """Drop the accounting_intents table."""
    op.drop_index("ix_accounting_intents_doc_txn_type", table_name="accounting_intents")
    op.drop_index("ix_accounting_intents_requires_review", table_name="accounting_intents")
    op.drop_index("ix_accounting_intents_organization_id", table_name="accounting_intents")
    op.drop_index("ix_accounting_intents_invoice_id", table_name="accounting_intents")
    op.drop_table("accounting_intents")
