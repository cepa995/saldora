"""Add ZZPL compliance tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-18
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create consent_records, deletion_requests, and data_processing_agreements tables."""
    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
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
        sa.Column("consent_type", sa.String(50), nullable=False),
        sa.Column("granted", sa.Boolean, nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("consent_text_version", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_consent_records_org_id", "consent_records", ["organization_id"])
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index("ix_consent_records_type", "consent_records", ["consent_type"])

    op.create_table(
        "deletion_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("request_type", sa.String(30), nullable=False, server_default="user_only"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("data_categories", postgresql.JSON, nullable=True),
        sa.Column("retained_categories", postgresql.JSON, nullable=True),
        sa.Column(
            "processed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_deletion_requests_user_id", "deletion_requests", ["user_id"])
    op.create_index("ix_deletion_requests_status", "deletion_requests", ["status"])
    op.create_index("ix_deletion_requests_org_id", "deletion_requests", ["organization_id"])

    op.create_table(
        "data_processing_agreements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column(
            "signed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_until", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("file_key", sa.String(500), nullable=True),
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
    op.create_index("ix_dpa_org_id", "data_processing_agreements", ["organization_id"])
    op.create_index("ix_dpa_status", "data_processing_agreements", ["status"])


def downgrade() -> None:
    """Drop ZZPL compliance tables."""
    op.drop_table("data_processing_agreements")
    op.drop_table("deletion_requests")
    op.drop_table("consent_records")
