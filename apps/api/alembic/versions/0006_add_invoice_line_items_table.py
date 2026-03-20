"""Add invoice_line_items table

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create invoice_line_items table for denormalized line item reporting."""
    op.create_table(
        "invoice_line_items",
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
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=True),
        sa.Column("unit_price", sa.Numeric(15, 4), nullable=True),
        sa.Column("discount", sa.Numeric(5, 2), nullable=True),
        sa.Column("tax_base", sa.Numeric(15, 2), nullable=True),
        sa.Column("total", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("tax_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("seller_name", sa.String(255), nullable=True),
        sa.Column("seller_pib", sa.String(20), nullable=True),
        sa.Column("invoice_date", sa.Date, nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RSD"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ili_invoice_id", "invoice_line_items", ["invoice_id"])
    op.create_index("ix_ili_org_id", "invoice_line_items", ["organization_id"])
    op.create_index("ix_ili_description", "invoice_line_items", ["description"])
    op.create_index("ix_ili_seller_pib", "invoice_line_items", ["seller_pib"])
    op.create_index("ix_ili_invoice_date", "invoice_line_items", ["invoice_date"])
    op.create_index(
        "ix_ili_org_date",
        "invoice_line_items",
        ["organization_id", "invoice_date"],
    )


def downgrade() -> None:
    """Drop invoice_line_items table."""
    op.drop_table("invoice_line_items")
