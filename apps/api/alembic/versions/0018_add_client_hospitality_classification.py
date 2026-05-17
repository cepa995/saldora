"""Add hospitality classification fields to clients.

The `legal_form` and `bookkeeping_system` columns drive the M20 hospitality
obligation matrix (which legally-required forms apply to a given client).
See SRS §4.19.2.

Both columns are nullable on purpose — existing clients land as
"unclassified" and the agency owner fills them in at first review.
The obligation card shows a "set legal form" prompt when either is NULL.

Allowed values are enforced at the Pydantic / API layer rather than via a
DB check constraint so adding new values (e.g. a future `udruzenje`) is a
code change rather than a migration. The set today:
    legal_form         ∈ {"DOO", "preduzetnik", "paušalac", "drugo"}
    bookkeeping_system ∈ {"dvojno", "prosto"}

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-07
"""

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("legal_form", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("bookkeeping_system", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clients", "bookkeeping_system")
    op.drop_column("clients", "legal_form")
