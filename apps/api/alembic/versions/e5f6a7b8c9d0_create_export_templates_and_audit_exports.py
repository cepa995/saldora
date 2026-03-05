"""create export_templates and audit_exports tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-05 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Default template field definitions
_DEFAULT_FIELDS = [
    {"key": "invoice_number", "label": "Broj fakture", "order": 1},
    {"key": "invoice_date", "label": "Datum fakture", "order": 2},
    {"key": "due_date", "label": "Datum valute", "order": 3},
    {"key": "seller_name", "label": "Prodavac", "order": 4},
    {"key": "seller_pib", "label": "PIB prodavca", "order": 5},
    {"key": "seller_address", "label": "Adresa prodavca", "order": 6},
    {"key": "seller_city", "label": "Grad prodavca", "order": 7},
    {"key": "buyer_name", "label": "Kupac", "order": 8},
    {"key": "buyer_pib", "label": "PIB kupca", "order": 9},
    {"key": "subtotal", "label": "Osnovica", "order": 10},
    {"key": "tax_rate", "label": "Stopa PDV (%)", "order": 11},
    {"key": "tax_amount", "label": "Iznos PDV", "order": 12},
    {"key": "total_amount", "label": "Ukupan iznos", "order": 13},
    {"key": "currency", "label": "Valuta", "order": 14},
    {"key": "status", "label": "Status", "order": 15},
    {"key": "confidence_score", "label": "Pouzdanost (%)", "order": 16},
]

_ACCOUNTING_FIELDS = [
    {"key": "invoice_number", "label": "Broj fakture", "order": 1},
    {"key": "seller_name", "label": "Prodavac", "order": 2},
    {"key": "seller_pib", "label": "PIB prodavca", "order": 3},
    {"key": "invoice_date", "label": "Datum fakture", "order": 4},
    {"key": "subtotal", "label": "Osnovica", "order": 5},
    {"key": "tax_amount", "label": "Iznos PDV", "order": 6},
    {"key": "total_amount", "label": "Ukupan iznos", "order": 7},
    {"key": "currency", "label": "Valuta", "order": 8},
]

_TAX_FIELDS = [
    {"key": "invoice_number", "label": "Broj fakture", "order": 1},
    {"key": "invoice_date", "label": "Datum fakture", "order": 2},
    {"key": "seller_name", "label": "Prodavac", "order": 3},
    {"key": "seller_pib", "label": "PIB prodavca", "order": 4},
    {"key": "subtotal", "label": "Osnovica", "order": 5},
    {"key": "tax_rate", "label": "Stopa PDV (%)", "order": 6},
    {"key": "tax_amount", "label": "Iznos PDV", "order": 7},
    {"key": "total_amount", "label": "Ukupan iznos", "order": 8},
]


def upgrade() -> None:
    """Create export_templates and audit_exports tables with seed data."""
    # --- export_templates ---
    op.create_table(
        "export_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("fields", postgresql.JSONB(), nullable=False),
        sa.Column("date_format", sa.String(20), nullable=True),
        sa.Column("decimal_separator", sa.String(1), nullable=True),
        sa.Column("supported_formats", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_export_templates_org_id", "export_templates", ["organization_id"])
    op.create_unique_constraint(
        "uq_template_name_per_org", "export_templates", ["organization_id", "name"]
    )

    # --- audit_exports ---
    op.create_table(
        "audit_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'processing'"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("invoice_count", sa.Integer(), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "include_documents",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "include_audit_trail",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "include_vat_summary",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_exports_org_id", "audit_exports", ["organization_id"])
    op.create_index("ix_audit_exports_created_at", "audit_exports", ["created_at"])

    # --- Seed default templates ---
    from uuid import uuid4

    templates_table = sa.table(
        "export_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("organization_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_default", sa.Boolean),
        sa.column("fields", postgresql.JSONB),
        sa.column("supported_formats", postgresql.JSONB),
        sa.column("created_by", postgresql.UUID(as_uuid=True)),
    )

    op.bulk_insert(
        templates_table,
        [
            {
                "id": str(uuid4()),
                "organization_id": None,
                "name": "Standardni izvoz",
                "description": "Sva polja u standardnom redosledu",
                "is_default": True,
                "fields": _DEFAULT_FIELDS,
                "supported_formats": ["xlsx", "csv", "json"],
                "created_by": None,
            },
            {
                "id": str(uuid4()),
                "organization_id": None,
                "name": "Racunovodstveni izvoz",
                "description": "Polja za knjizenje u racunovodstveni softver",
                "is_default": True,
                "fields": _ACCOUNTING_FIELDS,
                "supported_formats": ["xlsx", "csv", "json"],
                "created_by": None,
            },
            {
                "id": str(uuid4()),
                "organization_id": None,
                "name": "MiniMax izvoz",
                "description": "Format za uvoz u MiniMax racunovodstveni softver",
                "is_default": True,
                "fields": [],
                "supported_formats": ["minimax_xml"],
                "created_by": None,
            },
            {
                "id": str(uuid4()),
                "organization_id": None,
                "name": "PDV evidencija",
                "description": "Format za PDV prijavu",
                "is_default": True,
                "fields": _TAX_FIELDS,
                "supported_formats": ["xlsx", "csv"],
                "created_by": None,
            },
        ],
    )


def downgrade() -> None:
    """Drop export_templates and audit_exports tables."""
    op.drop_index("ix_audit_exports_created_at", table_name="audit_exports")
    op.drop_index("ix_audit_exports_org_id", table_name="audit_exports")
    op.drop_table("audit_exports")

    op.drop_unique_constraint("uq_template_name_per_org", table_name="export_templates")
    op.drop_index("ix_export_templates_org_id", table_name="export_templates")
    op.drop_table("export_templates")
