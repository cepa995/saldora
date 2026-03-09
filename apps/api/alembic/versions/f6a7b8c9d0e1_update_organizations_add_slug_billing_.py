"""update organizations add slug billing email settings

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-06 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add slug, billing_email, settings to organizations; rename stripe columns."""
    # Add new columns
    op.add_column(
        "organizations",
        sa.Column("slug", sa.String(100), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("billing_email", sa.String(255), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("settings", JSONB, server_default="{}", nullable=False),
    )

    # Generate slugs for existing organizations (use id as fallback)
    op.execute(
        """
        UPDATE organizations
        SET slug = LOWER(REGEXP_REPLACE(
            REGEXP_REPLACE(name, '[^a-zA-Z0-9]+', '-', 'g'),
            '^-|-$', '', 'g'
        ))
        WHERE slug IS NULL
        """
    )
    # Handle any empty slugs by using a portion of the id
    op.execute(
        """
        UPDATE organizations
        SET slug = LEFT(id::text, 8)
        WHERE slug IS NULL OR slug = ''
        """
    )
    # Handle potential duplicates by appending a counter suffix
    op.execute(
        """
        UPDATE organizations o
        SET slug = o.slug || '-' || ROW_NUMBER() OVER (PARTITION BY o.slug ORDER BY o.created_at)
        FROM (
            SELECT slug FROM organizations GROUP BY slug HAVING COUNT(*) > 1
        ) dupes
        WHERE o.slug = dupes.slug
        """
    )

    # Make slug non-nullable and unique
    op.alter_column("organizations", "slug", nullable=False)
    op.create_index("idx_organizations_slug", "organizations", ["slug"], unique=True)

    # Rename stripe columns to generic payment provider columns
    op.alter_column(
        "organizations",
        "stripe_customer_id",
        new_column_name="payment_provider_customer_id",
    )
    op.alter_column(
        "organizations",
        "stripe_subscription_id",
        new_column_name="payment_provider_subscription_id",
    )


def downgrade() -> None:
    """Reverse: remove slug, billing_email, settings; restore stripe columns."""
    # Restore stripe column names
    op.alter_column(
        "organizations",
        "payment_provider_subscription_id",
        new_column_name="stripe_subscription_id",
    )
    op.alter_column(
        "organizations",
        "payment_provider_customer_id",
        new_column_name="stripe_customer_id",
    )

    # Remove new columns
    op.drop_index("idx_organizations_slug", table_name="organizations")
    op.drop_column("organizations", "settings")
    op.drop_column("organizations", "billing_email")
    op.drop_column("organizations", "slug")
