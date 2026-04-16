"""Invoice template CRUD router — manage learned extraction templates."""

import logging
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.invoice_template import InvoiceTemplate
from app.models.user import User
from app.schemas.invoice_template import (
    InvoiceTemplateCreate,
    InvoiceTemplateListResponse,
    InvoiceTemplateResponse,
    InvoiceTemplateUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=InvoiceTemplateListResponse)
async def list_templates(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    seller_pib: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List invoice templates for the current organization.

    Args:
        page: Page number (1-indexed).
        per_page: Items per page.
        seller_pib: Filter by seller PIB.
        active_only: Only return active templates.
        db: Database session.
        user: Authenticated user.

    Returns:
        Paginated list of templates.
    """
    conditions = [InvoiceTemplate.organization_id == user.organization_id]
    if active_only:
        conditions.append(InvoiceTemplate.is_active.is_(True))
    if seller_pib:
        conditions.append(InvoiceTemplate.seller_pib == seller_pib)

    count_result = await db.execute(select(func.count(InvoiceTemplate.id)).where(and_(*conditions)))
    total = count_result.scalar() or 0
    total_pages = math.ceil(total / per_page) if total > 0 else 0

    offset = (page - 1) * per_page
    result = await db.execute(
        select(InvoiceTemplate)
        .where(and_(*conditions))
        .order_by(InvoiceTemplate.usage_count.desc())
        .offset(offset)
        .limit(per_page)
    )
    templates = list(result.scalars().all())

    return {
        "data": templates,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }


@router.get("/{template_id}", response_model=InvoiceTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvoiceTemplate:
    """Get a single template by ID.

    Args:
        template_id: Template UUID.
        db: Database session.
        user: Authenticated user.

    Returns:
        Template details.

    Raises:
        HTTPException: 404 if not found or not in user's org.
    """
    result = await db.execute(
        select(InvoiceTemplate).where(
            and_(
                InvoiceTemplate.id == template_id,
                InvoiceTemplate.organization_id == user.organization_id,
            )
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/", response_model=InvoiceTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: InvoiceTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> InvoiceTemplate:
    """Manually create an invoice template.

    Typically templates are auto-learned after LLM extraction, but admins
    can create them manually for known layouts.

    Args:
        body: Template creation data.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Created template.

    Raises:
        HTTPException: 409 if a template with same seller PIB and fingerprint
            already exists for this org.
    """
    # Check for duplicate
    existing = await db.execute(
        select(InvoiceTemplate).where(
            and_(
                InvoiceTemplate.organization_id == user.organization_id,
                InvoiceTemplate.seller_pib == body.seller_pib,
                InvoiceTemplate.layout_fingerprint == body.layout_fingerprint,
                InvoiceTemplate.is_active.is_(True),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Active template already exists for this seller and layout",
        )

    template = InvoiceTemplate(
        organization_id=user.organization_id,
        seller_pib=body.seller_pib,
        seller_name=body.seller_name,
        layout_fingerprint=body.layout_fingerprint,
        field_mappings=body.field_mappings,
        line_item_mappings=body.line_item_mappings,
        sample_invoice_id=body.sample_invoice_id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.patch("/{template_id}", response_model=InvoiceTemplateResponse)
async def update_template(
    template_id: UUID,
    body: InvoiceTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> InvoiceTemplate:
    """Update a template's mappings or active status.

    Args:
        template_id: Template UUID.
        body: Partial update data.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Updated template.

    Raises:
        HTTPException: 404 if not found or not in user's org.
    """
    result = await db.execute(
        select(InvoiceTemplate).where(
            and_(
                InvoiceTemplate.id == template_id,
                InvoiceTemplate.organization_id == user.organization_id,
            )
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    # Reset stats when reactivating
    if body.is_active is True and template.usage_count > 0:
        template.success_count = 0
        template.usage_count = 0
        template.success_rate = 0.0

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> None:
    """Delete a template.

    Args:
        template_id: Template UUID.
        db: Database session.
        user: Authenticated admin user.

    Raises:
        HTTPException: 404 if not found or not in user's org.
    """
    result = await db.execute(
        select(InvoiceTemplate).where(
            and_(
                InvoiceTemplate.id == template_id,
                InvoiceTemplate.organization_id == user.organization_id,
            )
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()
