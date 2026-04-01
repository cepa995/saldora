"""Product catalog API for item normalization across suppliers.

Uses PostgreSQL pg_trgm for fuzzy matching of item descriptions.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.line_item import InvoiceLineItem
from app.models.product_catalog import ProductCatalog
from app.routers.auth import get_current_user
from app.schemas.product_catalog import (
    ProductCreate,
    ProductMergeSuggestion,
    ProductMergeSuggestionList,
    ProductResponse,
    ProductUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Minimum trigram similarity threshold for merge suggestions
DEFAULT_SIMILARITY_THRESHOLD = 0.4


# ── CRUD ──────────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    category: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProductResponse]:
    """List all products in the organization's catalog.

    Args:
        category: Filter by category.
        search: Fuzzy search on canonical_name.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        List of products.
    """
    query = select(ProductCatalog).where(
        ProductCatalog.organization_id == current_user.organization_id
    )
    if category:
        query = query.where(ProductCatalog.category == category)
    if search:
        query = query.where(ProductCatalog.canonical_name.ilike(f"%{search}%"))
    query = query.order_by(ProductCatalog.canonical_name)

    result = await db.execute(query)
    return [ProductResponse.model_validate(row) for row in result.scalars().all()]


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProductResponse:
    """Create a new product in the catalog.

    Args:
        data: Product creation data.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        Created product.
    """
    product = ProductCatalog(
        organization_id=current_user.organization_id,
        canonical_name=data.canonical_name,
        unit_of_measure=data.unit_of_measure,
        category=data.category,
        aliases=data.aliases,
        selling_price=data.selling_price,
        default_margin_pct=data.default_margin_pct,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProductResponse:
    """Get a single product by ID.

    Args:
        product_id: Product UUID.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        Product details.
    """
    result = await db.execute(
        select(ProductCatalog).where(
            ProductCatalog.id == product_id,
            ProductCatalog.organization_id == current_user.organization_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Proizvod nije pronađen")
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProductResponse:
    """Update a product in the catalog.

    Args:
        product_id: Product UUID.
        data: Fields to update.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        Updated product.
    """
    result = await db.execute(
        select(ProductCatalog).where(
            ProductCatalog.id == product_id,
            ProductCatalog.organization_id == current_user.organization_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Proizvod nije pronađen")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete a product from the catalog.

    Args:
        product_id: Product UUID.
        db: Database session.
        current_user: Authenticated user.
    """
    result = await db.execute(
        delete(ProductCatalog).where(
            ProductCatalog.id == product_id,
            ProductCatalog.organization_id == current_user.organization_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Proizvod nije pronađen")
    await db.commit()


# ── Merge suggestions (trigram matching) ──────────────────────────────────────


@router.get("/suggestions/merge", response_model=ProductMergeSuggestionList)
async def suggest_merges(
    threshold: float = Query(DEFAULT_SIMILARITY_THRESHOLD, ge=0.1, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProductMergeSuggestionList:
    """Find similar item descriptions that might be the same product.

    Uses PostgreSQL pg_trgm trigram similarity to find pairs of line item
    descriptions that look similar but have different text.

    Args:
        threshold: Minimum similarity score (0.0-1.0). Default 0.4.
        limit: Max number of suggestions.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        List of merge suggestions with similarity scores.
    """
    org_id = current_user.organization_id

    # Use raw SQL for the trigram cross-join query (cleaner than ORM for this)
    raw_sql = text("""
        WITH distinct_items AS (
            SELECT DISTINCT ON (description, seller_pib)
                description, seller_name, seller_pib
            FROM invoice_line_items
            WHERE organization_id = :org_id
                AND description IS NOT NULL
                AND description != ''
        )
        SELECT
            a.description AS desc_a,
            b.description AS desc_b,
            similarity(a.description, b.description) AS sim,
            a.seller_name AS supplier_a,
            b.seller_name AS supplier_b
        FROM distinct_items a
        CROSS JOIN distinct_items b
        WHERE a.description < b.description
            AND similarity(a.description, b.description) >= :threshold
        ORDER BY sim DESC
        LIMIT :limit
    """)

    result = await db.execute(
        raw_sql, {"org_id": str(org_id), "threshold": threshold, "limit": limit}
    )
    rows = result.all()

    suggestions = []
    for row in rows:
        # Suggest the shorter name as canonical (usually cleaner)
        a_name = row.desc_a
        b_name = row.desc_b
        suggested = a_name if len(a_name) <= len(b_name) else b_name

        suggestions.append(
            ProductMergeSuggestion(
                description_a=a_name,
                description_b=b_name,
                similarity=round(float(row.sim), 3),
                supplier_a=row.supplier_a,
                supplier_b=row.supplier_b,
                suggested_canonical=suggested,
            )
        )

    return ProductMergeSuggestionList(suggestions=suggestions, total=len(suggestions))


@router.post("/merge", response_model=ProductResponse)
async def merge_items(
    canonical_name: str = Query(..., min_length=1),
    descriptions: list[str] = Query(..., min_length=1),
    category: str | None = Query(None),
    unit_of_measure: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProductResponse:
    """Merge multiple item descriptions into one canonical product.

    Creates (or updates) a product catalog entry and links all matching
    line items to it.

    Args:
        canonical_name: The canonical product name.
        descriptions: List of description strings to merge.
        category: Product category.
        unit_of_measure: Unit of measure.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        The created/updated product.
    """
    org_id = current_user.organization_id

    # Find or create the product
    result = await db.execute(
        select(ProductCatalog).where(
            ProductCatalog.organization_id == org_id,
            ProductCatalog.canonical_name == canonical_name,
        )
    )
    product = result.scalar_one_or_none()

    if product:
        # Merge aliases
        existing_aliases = set(product.aliases or [])
        existing_aliases.update(descriptions)
        product.aliases = list(existing_aliases)
        if category:
            product.category = category
        if unit_of_measure:
            product.unit_of_measure = unit_of_measure
    else:
        product = ProductCatalog(
            organization_id=org_id,
            canonical_name=canonical_name,
            aliases=descriptions,
            category=category,
            unit_of_measure=unit_of_measure,
        )
        db.add(product)
        await db.flush()

    # Link matching line items to this product
    from sqlalchemy import update

    for desc in descriptions:
        stmt = (
            update(InvoiceLineItem)
            .where(
                InvoiceLineItem.organization_id == org_id,
                func.lower(func.trim(InvoiceLineItem.description)) == func.lower(func.trim(desc)),
            )
            .values(product_id=product.id)
        )
        result = await db.execute(stmt)
        product.match_count += result.rowcount

    # Also link items matching the canonical name
    stmt = (
        update(InvoiceLineItem)
        .where(
            InvoiceLineItem.organization_id == org_id,
            func.lower(func.trim(InvoiceLineItem.description))
            == func.lower(func.trim(canonical_name)),
            InvoiceLineItem.product_id.is_(None),
        )
        .values(product_id=product.id)
    )
    result = await db.execute(stmt)
    product.match_count += result.rowcount

    await db.commit()
    await db.refresh(product)

    logger.info(
        "Merged %d descriptions into product '%s' (ID: %s, matched: %d items)",
        len(descriptions),
        canonical_name,
        product.id,
        product.match_count,
    )

    return ProductResponse.model_validate(product)
