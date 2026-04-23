"""Add client_events append-only table.

Per-client chronological event stream. Populated whenever any action
in the app touches a specific client. Rendered by the Timeline tab in
the client workspace (M19 — Client-First UI).

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-22
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "event_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "payload",
            sa.dialects.postgresql.JSON,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "actor_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_client_events_org_id", "client_events", ["organization_id"])
    op.create_index("ix_client_events_client_id", "client_events", ["client_id"])
    op.create_index(
        "ix_client_events_client_date",
        "client_events",
        ["client_id", "event_date"],
    )
    op.create_index(
        "ix_client_events_org_date",
        "client_events",
        ["organization_id", "event_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_client_events_org_date", table_name="client_events")
    op.drop_index("ix_client_events_client_date", table_name="client_events")
    op.drop_index("ix_client_events_client_id", table_name="client_events")
    op.drop_index("ix_client_events_org_id", table_name="client_events")
    op.drop_table("client_events")
