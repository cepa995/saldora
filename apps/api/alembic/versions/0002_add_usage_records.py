"""add usage_records table and migrate plan names

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create usage_records table and migrate plan names."""
    op.create_table(
        "usage_records",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("invoices_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("api_calls_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("storage_bytes", sa.BigInteger, server_default="0", nullable=False),
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
    )

    op.create_index(
        "uq_usage_org_period",
        "usage_records",
        ["organization_id", "period_start"],
        unique=True,
    )

    # Migrate plan names: professional -> pro, enterprise -> agency
    op.execute("UPDATE organizations SET plan = 'pro' WHERE plan = 'professional'")
    op.execute("UPDATE organizations SET plan = 'agency' WHERE plan = 'enterprise'")


def downgrade() -> None:
    """Drop usage_records table and revert plan names."""
    op.execute("UPDATE organizations SET plan = 'professional' WHERE plan = 'pro'")
    op.execute("UPDATE organizations SET plan = 'enterprise' WHERE plan = 'agency'")

    op.drop_index("uq_usage_org_period", table_name="usage_records")
    op.drop_table("usage_records")
