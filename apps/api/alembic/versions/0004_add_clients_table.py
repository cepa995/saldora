"""Add clients table and client_id FK on invoices

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create clients table and add client_id FK to invoices."""
    op.create_table(
        "clients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("pib", sa.String(20), nullable=False),
        sa.Column("mb", sa.String(20), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("organization_id", "pib", name="uq_client_pib_per_org"),
    )
    op.create_index("ix_clients_org_id", "clients", ["organization_id"])
    op.create_index("ix_clients_pib", "clients", ["pib"])
    op.create_index(
        "ix_clients_org_active",
        "clients",
        ["organization_id", "is_active"],
    )

    # Add client_id FK to invoices
    op.add_column(
        "invoices",
        sa.Column("client_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_invoices_client_id",
        "invoices",
        "clients",
        ["client_id"],
        ["id"],
    )
    op.create_index("ix_invoices_client_id", "invoices", ["client_id"])


def downgrade() -> None:
    """Remove client_id from invoices and drop clients table."""
    op.drop_index("ix_invoices_client_id", "invoices")
    op.drop_constraint("fk_invoices_client_id", "invoices", type_="foreignkey")
    op.drop_column("invoices", "client_id")
    op.drop_table("clients")
