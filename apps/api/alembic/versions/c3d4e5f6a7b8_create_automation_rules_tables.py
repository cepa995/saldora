"""create automation_rules and rule_executions tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-03 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create automation_rules and rule_executions tables."""
    # automation_rules
    op.create_table(
        "automation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        # Rule definition
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        # Rule logic
        sa.Column("conditions", postgresql.JSONB(), nullable=False),
        sa.Column("actions", postgresql.JSONB(), nullable=False),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # Metadata
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        # Statistics
        sa.Column("execution_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
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
    )

    # Unique constraint: one rule name per org
    op.create_unique_constraint(
        "uq_rule_name_per_org",
        "automation_rules",
        ["organization_id", "name"],
    )

    op.create_index("ix_automation_rules_org_id", "automation_rules", ["organization_id"])
    op.create_index(
        "ix_automation_rules_org_active",
        "automation_rules",
        ["organization_id", "is_active"],
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index("ix_automation_rules_type", "automation_rules", ["rule_type"])

    # rule_executions
    op.create_table(
        "rule_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automation_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accounting_intent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounting_intents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Execution details
        sa.Column("conditions_matched", postgresql.JSONB(), nullable=False),
        sa.Column("actions_applied", postgresql.JSONB(), nullable=False),
        # Timing
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
    )

    op.create_index("ix_rule_executions_rule_id", "rule_executions", ["rule_id"])
    op.create_index("ix_rule_executions_invoice_id", "rule_executions", ["invoice_id"])
    op.create_index("ix_rule_executions_executed_at", "rule_executions", ["executed_at"])


def downgrade() -> None:
    """Drop rule_executions and automation_rules tables."""
    op.drop_index("ix_rule_executions_executed_at", table_name="rule_executions")
    op.drop_index("ix_rule_executions_invoice_id", table_name="rule_executions")
    op.drop_index("ix_rule_executions_rule_id", table_name="rule_executions")
    op.drop_table("rule_executions")

    op.drop_index("ix_automation_rules_type", table_name="automation_rules")
    op.drop_index("ix_automation_rules_org_active", table_name="automation_rules")
    op.drop_index("ix_automation_rules_org_id", table_name="automation_rules")
    op.drop_unique_constraint("uq_rule_name_per_org", table_name="automation_rules")
    op.drop_table("automation_rules")
