"""rename email_verification to email_verified

Revision ID: 6c35df897832
Revises: 98666451fc88
Create Date: 2026-02-17 09:27:11.542879

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c35df897832"
down_revision: str | Sequence[str] | None = "98666451fc88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("users", "email_verification", new_column_name="email_verified")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("users", "email_verified", new_column_name="email_verification")
