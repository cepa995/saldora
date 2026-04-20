"""Add paušal invoice issuance: customers, invoice_counters, Client/Invoice fields

Customers: buyers of paušal invoices, owned by a paušalac Client.
InvoiceCounter: per-client-per-year atomic sequence for invoice numbering.
Adds bank_account and activity_code to clients (nullable, paušal-only).
Widens invoices.status check to include 'issued' and 'cancelled'.

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-20
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Client extensions (paušal-only; nullable) ----
    op.add_column("clients", sa.Column("bank_account", sa.String(length=40), nullable=True))
    op.add_column("clients", sa.Column("activity_code", sa.String(length=10), nullable=True))

    # ---- Customers table ----
    op.create_table(
        "customers",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
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
        sa.Column(
            "client_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_natural_person", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pib", sa.String(length=20), nullable=True),
        sa.Column("mb", sa.String(length=20), nullable=True),
        sa.Column("jmbg", sa.String(length=13), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=False, server_default="RS"),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_customers_client_id", "customers", ["client_id"])
    op.create_index("ix_customers_org_id", "customers", ["organization_id"])
    op.create_index(
        "ix_customers_client_active",
        "customers",
        ["client_id", "is_active"],
    )

    # ---- Invoice counters ----
    op.create_table(
        "invoice_counters",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
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
        sa.Column(
            "client_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("client_id", "year", name="uq_invoice_counter_client_year"),
    )
    op.create_index("ix_invoice_counters_client_year", "invoice_counters", ["client_id", "year"])

    # ---- Widen invoices.status values ----
    # Previously: processing, review, verified, exported, error
    # Adding: issued, cancelled (for outgoing direction)
    # The enum is enforced by app logic, not a DB check constraint on main branch,
    # so no constraint changes needed here. Emit a no-op for clarity.


def downgrade() -> None:
    op.drop_index("ix_invoice_counters_client_year", table_name="invoice_counters")
    op.drop_table("invoice_counters")

    op.drop_index("ix_customers_client_active", table_name="customers")
    op.drop_index("ix_customers_org_id", table_name="customers")
    op.drop_index("ix_customers_client_id", table_name="customers")
    op.drop_table("customers")

    op.drop_column("clients", "activity_code")
    op.drop_column("clients", "bank_account")
