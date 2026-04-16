"""Make consent_records.organization_id nullable

Users grant consent at registration before creating an organization.

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-15
"""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "consent_records",
        "organization_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "consent_records",
        "organization_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
