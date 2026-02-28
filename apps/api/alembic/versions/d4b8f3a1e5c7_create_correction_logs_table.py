"""create correction_logs table

Revision ID: d4b8f3a1e5c7
Revises: c3a7e2f19b84
Create Date: 2026-02-28 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b8f3a1e5c7"
down_revision: str | Sequence[str] | None = "c3a7e2f19b84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the correction_logs table."""
    op.create_table(
        "correction_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
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
    )

    op.create_index("ix_correction_logs_invoice_id", "correction_logs", ["invoice_id"])
    op.create_index("ix_correction_logs_organization_id", "correction_logs", ["organization_id"])
    op.create_index("ix_correction_logs_field_name", "correction_logs", ["field_name"])
    op.create_index("ix_correction_logs_created_at", "correction_logs", ["created_at"])


def downgrade() -> None:
    """Drop the correction_logs table."""
    op.drop_index("ix_correction_logs_created_at", table_name="correction_logs")
    op.drop_index("ix_correction_logs_field_name", table_name="correction_logs")
    op.drop_index("ix_correction_logs_organization_id", table_name="correction_logs")
    op.drop_index("ix_correction_logs_invoice_id", table_name="correction_logs")
    op.drop_table("correction_logs")
