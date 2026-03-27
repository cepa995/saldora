"""Add product_catalog table and product_id FK on invoice_line_items

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create product_catalog table and link to invoice_line_items."""
    # Enable pg_trgm extension for fuzzy matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "product_catalog",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("unit_of_measure", sa.String(20), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("aliases", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("selling_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("default_margin_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("match_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pc_org_id", "product_catalog", ["organization_id"])
    op.create_index(
        "ix_pc_org_name", "product_catalog", ["organization_id", "canonical_name"], unique=True
    )
    op.create_index("ix_pc_category", "product_catalog", ["category"])

    # Trigram index for fuzzy search on canonical_name
    op.execute(
        "CREATE INDEX ix_pc_trgm_name ON product_catalog USING gin (canonical_name gin_trgm_ops)"
    )

    # Add product_id FK to invoice_line_items
    op.add_column(
        "invoice_line_items",
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_catalog.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_ili_product_id", "invoice_line_items", ["product_id"])


def downgrade() -> None:
    """Remove product_catalog table and product_id FK."""
    op.drop_index("ix_ili_product_id", table_name="invoice_line_items")
    op.drop_column("invoice_line_items", "product_id")
    op.drop_index("ix_pc_trgm_name", table_name="product_catalog")
    op.drop_index("ix_pc_category", table_name="product_catalog")
    op.drop_index("ix_pc_org_name", table_name="product_catalog")
    op.drop_index("ix_pc_org_id", table_name="product_catalog")
    op.drop_table("product_catalog")
