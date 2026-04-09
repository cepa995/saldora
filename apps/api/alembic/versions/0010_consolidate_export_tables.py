"""Consolidate audit_exports into scheduled_export_logs, drop SEF tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add audit columns to scheduled_export_logs, drop audit_exports + SEF tables."""
    # Add new columns to scheduled_export_logs
    op.add_column(
        "scheduled_export_logs",
        sa.Column("export_type", sa.String(20), server_default="scheduled", nullable=False),
    )
    op.add_column(
        "scheduled_export_logs",
        sa.Column("requested_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.add_column("scheduled_export_logs", sa.Column("date_from", sa.Date()))
    op.add_column("scheduled_export_logs", sa.Column("date_to", sa.Date()))
    op.add_column("scheduled_export_logs", sa.Column("reason", sa.Text()))
    op.add_column("scheduled_export_logs", sa.Column("file_path", sa.String(500)))
    op.add_column("scheduled_export_logs", sa.Column("download_url", sa.Text()))
    op.add_column(
        "scheduled_export_logs",
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "scheduled_export_logs",
        sa.Column("include_documents", sa.Boolean(), server_default="true"),
    )
    op.add_column(
        "scheduled_export_logs",
        sa.Column("include_audit_trail", sa.Boolean(), server_default="true"),
    )
    op.add_column(
        "scheduled_export_logs",
        sa.Column("include_vat_summary", sa.Boolean(), server_default="true"),
    )

    op.create_index("ix_sel_export_type", "scheduled_export_logs", ["export_type"])
    op.create_index("ix_sel_requested_by", "scheduled_export_logs", ["requested_by"])

    # Migrate audit_exports data
    op.execute("""
        INSERT INTO scheduled_export_logs (
            id, organization_id, period, delivery_method, delivered_to,
            file_size_bytes, invoice_count, status, delivered_at,
            export_type, requested_by, date_from, date_to, reason,
            file_path, download_url, expires_at,
            include_documents, include_audit_trail, include_vat_summary
        )
        SELECT
            id, organization_id,
            TO_CHAR(date_from, 'YYYY-MM'),
            'manual', '',
            file_size_bytes, invoice_count, status, created_at,
            'manual', requested_by, date_from, date_to, reason,
            file_path, download_url, expires_at,
            include_documents, include_audit_trail, include_vat_summary
        FROM audit_exports
        WHERE NOT EXISTS (
            SELECT 1 FROM scheduled_export_logs sel WHERE sel.id = audit_exports.id
        )
    """)

    # Drop old tables
    op.drop_table("audit_exports")
    op.drop_table("sef_invoices")
    op.drop_table("sef_connections")


def downgrade() -> None:
    """Reverse: recreate dropped tables, remove added columns."""
    # Recreate sef_connections
    op.create_table(
        "sef_connections",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Recreate sef_invoices
    op.create_table(
        "sef_invoices",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("invoice_id", sa.UUID(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Recreate audit_exports (minimal)
    op.create_table(
        "audit_exports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("requested_by", sa.UUID(), sa.ForeignKey("users.id")),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.String(20), server_default="processing"),
        sa.Column("file_path", sa.String(500)),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("invoice_count", sa.Integer()),
        sa.Column("download_url", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("include_documents", sa.Boolean(), server_default="true"),
        sa.Column("include_audit_trail", sa.Boolean(), server_default="true"),
        sa.Column("include_vat_summary", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Remove added columns
    op.drop_index("ix_sel_requested_by", table_name="scheduled_export_logs")
    op.drop_index("ix_sel_export_type", table_name="scheduled_export_logs")
    op.drop_column("scheduled_export_logs", "include_vat_summary")
    op.drop_column("scheduled_export_logs", "include_audit_trail")
    op.drop_column("scheduled_export_logs", "include_documents")
    op.drop_column("scheduled_export_logs", "expires_at")
    op.drop_column("scheduled_export_logs", "download_url")
    op.drop_column("scheduled_export_logs", "file_path")
    op.drop_column("scheduled_export_logs", "reason")
    op.drop_column("scheduled_export_logs", "date_to")
    op.drop_column("scheduled_export_logs", "date_from")
    op.drop_column("scheduled_export_logs", "requested_by")
    op.drop_column("scheduled_export_logs", "export_type")
