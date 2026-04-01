"""Add scheduled_export_logs table for automated archive tracking

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create scheduled_export_logs table."""
    op.create_table(
        "scheduled_export_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column(
            "delivery_method",
            sa.String(20),
            nullable=False,
            server_default="email",
        ),
        sa.Column("delivered_to", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("invoice_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sel_org_id", "scheduled_export_logs", ["organization_id"])
    op.create_index("ix_sel_period", "scheduled_export_logs", ["period"])


def downgrade() -> None:
    """Drop scheduled_export_logs table."""
    op.drop_index("ix_sel_period", table_name="scheduled_export_logs")
    op.drop_index("ix_sel_org_id", table_name="scheduled_export_logs")
    op.drop_table("scheduled_export_logs")
