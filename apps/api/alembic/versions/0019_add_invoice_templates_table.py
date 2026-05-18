"""Add invoice_templates table

Stores learned invoice layouts for template-based extraction
(LLM bypass). Each template maps a seller PIB + layout fingerprint
to field extraction rules.

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-23
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoice_templates",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seller_pib", sa.String(20), nullable=False),
        sa.Column("seller_name", sa.String(255), nullable=True),
        sa.Column("layout_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "field_mappings",
            sa.dialects.postgresql.JSON(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("line_item_mappings", sa.dialects.postgresql.JSON(), nullable=True),
        sa.Column(
            "sample_invoice_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Lookup by org + seller PIB (most common query)
    op.create_index(
        "ix_invoice_templates_org_seller",
        "invoice_templates",
        ["organization_id", "seller_pib"],
    )

    # Lookup by fingerprint for exact match
    op.create_index(
        "ix_invoice_templates_fingerprint",
        "invoice_templates",
        ["layout_fingerprint"],
    )

    # Unique constraint: one active template per org + seller + fingerprint
    op.create_index(
        "ix_invoice_templates_unique_active",
        "invoice_templates",
        ["organization_id", "seller_pib", "layout_fingerprint"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_invoice_templates_unique_active", table_name="invoice_templates")
    op.drop_index("ix_invoice_templates_fingerprint", table_name="invoice_templates")
    op.drop_index("ix_invoice_templates_org_seller", table_name="invoice_templates")
    op.drop_table("invoice_templates")
