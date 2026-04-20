"""Add client_type to clients and direction to invoices

Enables paušalci (flat-rate entrepreneurs) as a distinct client type
and distinguishes incoming vs outgoing invoices.

Existing rows default to client_type='vat_payer' and direction='incoming'.

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-20
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column(
            "client_type",
            sa.String(length=20),
            nullable=False,
            server_default="vat_payer",
        ),
    )
    op.create_check_constraint(
        "ck_clients_client_type",
        "clients",
        "client_type IN ('vat_payer', 'pausalac', 'foreign_entity', 'non_profit')",
    )
    op.create_index(
        "ix_clients_org_type",
        "clients",
        ["organization_id", "client_type"],
    )

    op.add_column(
        "invoices",
        sa.Column(
            "direction",
            sa.String(length=20),
            nullable=False,
            server_default="incoming",
        ),
    )
    op.create_check_constraint(
        "ck_invoices_direction",
        "invoices",
        "direction IN ('incoming', 'outgoing')",
    )
    op.create_index("ix_invoices_direction", "invoices", ["direction"])


def downgrade() -> None:
    op.drop_index("ix_invoices_direction", table_name="invoices")
    op.drop_constraint("ck_invoices_direction", "invoices", type_="check")
    op.drop_column("invoices", "direction")

    op.drop_index("ix_clients_org_type", table_name="clients")
    op.drop_constraint("ck_clients_client_type", "clients", type_="check")
    op.drop_column("clients", "client_type")
