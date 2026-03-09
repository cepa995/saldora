"""create exchange_rates table and add exchange rate fields to invoices

Revision ID: k1f2g3h4i5j6
Revises: j0e1f2g3h4i5
Create Date: 2026-03-09 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "k1f2g3h4i5j6"
down_revision: str | Sequence[str] | None = "j0e1f2g3h4i5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create exchange_rates table and add exchange rate columns to invoices."""
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, index=True),
        sa.Column("rate_date", sa.Date(), nullable=False, index=True),
        sa.Column("buying_rate", sa.Numeric(15, 6), nullable=True),
        sa.Column("middle_rate", sa.Numeric(15, 6), nullable=False),
        sa.Column("selling_rate", sa.Numeric(15, 6), nullable=True),
        sa.Column("unit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(20), nullable=False, server_default="NBS"),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("currency", "rate_date", name="uq_exchange_rate_currency_date"),
    )

    # Add exchange rate fields to invoices
    op.add_column(
        "invoices",
        sa.Column("exchange_rate", sa.Numeric(15, 6), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("exchange_rate_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("total_amount_rsd", sa.Numeric(15, 2), nullable=True),
    )


def downgrade() -> None:
    """Drop exchange_rates table and remove exchange rate columns from invoices."""
    op.drop_column("invoices", "total_amount_rsd")
    op.drop_column("invoices", "exchange_rate_date")
    op.drop_column("invoices", "exchange_rate")
    op.drop_table("exchange_rates")
