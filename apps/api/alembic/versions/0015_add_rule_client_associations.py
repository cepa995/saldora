"""Add rule_client_associations join table.

Many-to-many between automation_rules and clients. A rule with zero
associations is global (applies to all invoices in the org); a rule with
one or more associations is client-scoped (applies only to invoices
whose client_id matches one of the attached clients).

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-22
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rule_client_associations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rule_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automation_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("rule_id", "client_id", name="uq_rule_client"),
    )
    op.create_index(
        "ix_rule_client_rule_id",
        "rule_client_associations",
        ["rule_id"],
    )
    op.create_index(
        "ix_rule_client_client_id",
        "rule_client_associations",
        ["client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_rule_client_client_id", table_name="rule_client_associations")
    op.drop_index("ix_rule_client_rule_id", table_name="rule_client_associations")
    op.drop_table("rule_client_associations")
