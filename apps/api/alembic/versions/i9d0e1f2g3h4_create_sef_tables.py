"""create sef_connections and sef_invoices tables

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-03-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i9d0e1f2g3h4"
down_revision: str = "h8c9d0e1f2g3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create sef_connections and sef_invoices tables."""
    # SEF connections — one per organization
    op.create_table(
        "sef_connections",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("environment", sa.String(20), nullable=False, server_default="production"),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("certificate_path", sa.String(500), nullable=True),
        sa.Column("pib", sa.String(20), nullable=False),
        sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "sync_interval_minutes",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("15"),
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(20), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column(
            "total_invoices_synced",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("0"),
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", name="uq_sef_connections_org"),
    )

    # SEF invoices — incoming/outgoing invoices linked to SEF
    op.create_table(
        "sef_invoices",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=True),
        sa.Column("sef_id", sa.String(100), nullable=False),
        sa.Column("sef_internal_id", sa.String(100), nullable=True),
        sa.Column("cir_invoice_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("sef_status", sa.String(30), nullable=False),
        sa.Column("sef_status_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False, server_default="INBOUND"),
        sa.Column("invoice_number", sa.String(100), nullable=True),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("supplier_pib", sa.String(20), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RSD"),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ubl_xml", sa.Text(), nullable=True),
        sa.Column("sef_response_json", postgresql.JSONB(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "sef_id", name="uq_sef_invoices_org_sef_id"),
    )

    op.create_index("ix_sef_invoices_org_id", "sef_invoices", ["organization_id"])
    op.create_index("ix_sef_invoices_status", "sef_invoices", ["status"])
    op.create_index("ix_sef_invoices_sef_status", "sef_invoices", ["sef_status"])
    op.create_index("ix_sef_invoices_invoice_id", "sef_invoices", ["invoice_id"])
    op.create_index("ix_sef_invoices_received_at", "sef_invoices", ["received_at"])


def downgrade() -> None:
    """Drop sef_invoices and sef_connections tables."""
    op.drop_index("ix_sef_invoices_received_at", table_name="sef_invoices")
    op.drop_index("ix_sef_invoices_invoice_id", table_name="sef_invoices")
    op.drop_index("ix_sef_invoices_sef_status", table_name="sef_invoices")
    op.drop_index("ix_sef_invoices_status", table_name="sef_invoices")
    op.drop_index("ix_sef_invoices_org_id", table_name="sef_invoices")
    op.drop_table("sef_invoices")
    op.drop_table("sef_connections")
