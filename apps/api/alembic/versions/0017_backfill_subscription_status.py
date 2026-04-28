"""Backfill subscription_status for legacy orgs.

The /auth/create-organization endpoint now lands new orgs in
subscription_status="pending" so they go through manual admin approval
before the require_role dep lets them use mutational routes. Pre-existing
organizations (created before this change) have subscription_status NULL
and would otherwise be locked out of the app on the next deploy.

Set every NULL row to "active" so existing customers keep working. New
registrations from this commit forward get "pending" via the auth code,
not via the column default.

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-28
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE organizations
        SET subscription_status = 'active'
        WHERE subscription_status IS NULL
        """
    )


def downgrade() -> None:
    # Intentional no-op: we cannot tell which rows were originally NULL vs
    # which were explicitly set to "active" before this migration ran. The
    # forward state is the safe one to leave in place.
    pass
