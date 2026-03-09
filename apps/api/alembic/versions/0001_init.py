"""create all tables

Revision ID: 0001
Revises:
Create Date: 2026-03-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables."""
    # 1. organizations (no FK deps)
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("pib", sa.String(20), nullable=True),
        sa.Column("billing_email", sa.String(255), nullable=True),
        sa.Column("payment_provider_customer_id", sa.String(255), nullable=True),
        sa.Column("payment_provider_subscription_id", sa.String(255), nullable=True),
        sa.Column("plan", sa.String(50), server_default="free", nullable=False),
        sa.Column("settings", JSONB, server_default="{}", nullable=False),
        sa.Column("logo_key", sa.String(500), nullable=True),
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
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"], unique=True)

    # 2. users (FK -> organizations)
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), server_default="viewer", nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
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
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 3. invoices (FK -> organizations)
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), server_default="processing", nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("seller", sa.JSON(), nullable=True),
        sa.Column("buyer", sa.JSON(), nullable=True),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=True),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("tax_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("currency", sa.String(3), server_default="RSD", nullable=False),
        sa.Column("exchange_rate", sa.Numeric(15, 6), nullable=True),
        sa.Column("exchange_rate_date", sa.Date(), nullable=True),
        sa.Column("total_amount_rsd", sa.Numeric(15, 2), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=True),
        sa.Column("tax_groups", sa.JSON(), nullable=True),
        sa.Column("document_hash", sa.String(64), nullable=True),
        sa.Column("document_path", sa.String(500), nullable=True),
        sa.Column("document_content_type", sa.String(100), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("field_confidence", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("ocr_engine", sa.String(50), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("raw_ocr_text", sa.Text(), nullable=True),
        sa.Column("raw_llm_output", sa.Text(), nullable=True),
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
    )
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_document_hash", "invoices", ["document_hash"])

    # 4. exchange_rates (standalone)
    op.create_table(
        "exchange_rates",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("buying_rate", sa.Numeric(15, 6), nullable=True),
        sa.Column("middle_rate", sa.Numeric(15, 6), nullable=False),
        sa.Column("selling_rate", sa.Numeric(15, 6), nullable=True),
        sa.Column("unit", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source", sa.String(20), server_default="NBS", nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
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
        sa.UniqueConstraint("currency", "rate_date", name="uq_exchange_rate_currency_date"),
    )
    op.create_index("ix_exchange_rates_currency", "exchange_rates", ["currency"])
    op.create_index("ix_exchange_rates_rate_date", "exchange_rates", ["rate_date"])

    # 5. accounting_intents (FK -> invoices, organizations, users)
    op.create_table(
        "accounting_intents",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("vat_treatment", sa.String(30), nullable=False),
        sa.Column("is_deductible", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("vat_breakdown", JSONB, server_default="{}", nullable=False),
        sa.Column("suggested_konta", JSONB, server_default="{}", nullable=False),
        sa.Column("pdv_book_entries", JSONB, server_default="{}", nullable=False),
        sa.Column("applied_rules", JSONB, server_default="[]", nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False),
        sa.Column("requires_review", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("review_reasons", JSONB, server_default="[]", nullable=False),
        sa.Column(
            "reviewed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
    )
    op.create_index("ix_accounting_intents_invoice_id", "accounting_intents", ["invoice_id"])
    op.create_index(
        "ix_accounting_intents_organization_id", "accounting_intents", ["organization_id"]
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

    # 6. automation_rules (FK -> organizations, users)
    op.create_table(
        "automation_rules",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="50", nullable=False),
        sa.Column("conditions", JSONB, nullable=False),
        sa.Column("actions", JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("execution_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("organization_id", "name", name="uq_rule_name_per_org"),
    )
    op.create_index("ix_automation_rules_org_id", "automation_rules", ["organization_id"])
    op.create_index(
        "ix_automation_rules_org_active",
        "automation_rules",
        ["organization_id", "is_active"],
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index("ix_automation_rules_type", "automation_rules", ["rule_type"])

    # 7. rule_executions (FK -> automation_rules, invoices, accounting_intents)
    op.create_table(
        "rule_executions",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "rule_id",
            UUID(as_uuid=True),
            sa.ForeignKey("automation_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accounting_intent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("accounting_intents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("conditions_matched", JSONB, nullable=False),
        sa.Column("actions_applied", JSONB, nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rule_executions_rule_id", "rule_executions", ["rule_id"])
    op.create_index("ix_rule_executions_invoice_id", "rule_executions", ["invoice_id"])
    op.create_index("ix_rule_executions_executed_at", "rule_executions", ["executed_at"])

    # 8. audit_logs (append-only, FK -> organizations, users)
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # 9. correction_logs (append-only, FK -> invoices, organizations, users)
    op.create_table(
        "correction_logs",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=True),
        sa.Column("corrected_value", sa.Text(), nullable=False),
        sa.Column("model_confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("correction_type", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_correction_logs_invoice_id", "correction_logs", ["invoice_id"])
    op.create_index("ix_correction_logs_organization_id", "correction_logs", ["organization_id"])
    op.create_index("ix_correction_logs_field_name", "correction_logs", ["field_name"])
    op.create_index("ix_correction_logs_created_at", "correction_logs", ["created_at"])

    # 10. export_templates (FK -> organizations, users)
    op.create_table(
        "export_templates",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("fields", JSONB, nullable=False),
        sa.Column("date_format", sa.String(20), nullable=True),
        sa.Column("decimal_separator", sa.String(1), nullable=True),
        sa.Column("supported_formats", JSONB, nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
        sa.UniqueConstraint("organization_id", "name", name="uq_template_name_per_org"),
    )
    op.create_index("ix_export_templates_org_id", "export_templates", ["organization_id"])

    # 11. audit_exports (FK -> organizations, users)
    op.create_table(
        "audit_exports",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="processing", nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("invoice_count", sa.Integer(), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("include_documents", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("include_audit_trail", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("include_vat_summary", sa.Boolean(), server_default="true", nullable=False),
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
    )
    op.create_index("ix_audit_exports_org_id", "audit_exports", ["organization_id"])
    op.create_index("ix_audit_exports_created_at", "audit_exports", ["created_at"])

    # 12. minimax_configs (FK -> organizations)
    op.create_table(
        "minimax_configs",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("client_secret", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("minimax_org_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
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
    )

    # 13. sef_connections (FK -> organizations)
    op.create_table(
        "sef_connections",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("environment", sa.String(20), server_default="production", nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("certificate_path", sa.String(500), nullable=True),
        sa.Column("pib", sa.String(20), nullable=False),
        sa.Column("sync_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sync_interval_minutes", sa.Integer(), server_default="15", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(20), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("total_invoices_synced", sa.Integer(), server_default="0", nullable=False),
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
    )

    # 14. sef_invoices (FK -> organizations, invoices)
    op.create_table(
        "sef_invoices",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sef_id", sa.String(100), nullable=False),
        sa.Column("sef_internal_id", sa.String(100), nullable=True),
        sa.Column("cir_invoice_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("sef_status", sa.String(30), nullable=False),
        sa.Column("sef_status_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("direction", sa.String(10), server_default="INBOUND", nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=True),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("supplier_pib", sa.String(20), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("currency", sa.String(3), server_default="RSD", nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ubl_xml", sa.Text(), nullable=True),
        sa.Column("sef_response_json", JSONB, nullable=True),
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
        sa.UniqueConstraint("organization_id", "sef_id", name="uq_sef_invoices_org_sef_id"),
    )
    op.create_index("ix_sef_invoices_org_id", "sef_invoices", ["organization_id"])
    op.create_index("ix_sef_invoices_status", "sef_invoices", ["status"])
    op.create_index("ix_sef_invoices_sef_status", "sef_invoices", ["sef_status"])
    op.create_index("ix_sef_invoices_invoice_id", "sef_invoices", ["invoice_id"])
    op.create_index("ix_sef_invoices_received_at", "sef_invoices", ["received_at"])

    # 15. invitations (FK -> organizations, users)
    op.create_table(
        "invitations",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="operator", nullable=False),
        sa.Column("token", sa.String(255), unique=True, nullable=False),
        sa.Column(
            "invited_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
    )

    # 16. join_requests (FK -> organizations, users)
    op.create_table(
        "join_requests",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column(
            "reviewed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("join_requests")
    op.drop_table("invitations")
    op.drop_table("sef_invoices")
    op.drop_table("sef_connections")
    op.drop_table("minimax_configs")
    op.drop_table("audit_exports")
    op.drop_table("export_templates")
    op.drop_table("correction_logs")
    op.drop_table("audit_logs")
    op.drop_table("rule_executions")
    op.drop_table("automation_rules")
    op.drop_table("accounting_intents")
    op.drop_table("exchange_rates")
    op.drop_table("invoices")
    op.drop_table("users")
    op.drop_table("organizations")
