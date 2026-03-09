"""Organization settings router."""

import asyncio
import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationResponse, OrganizationUpdate
from app.services import audit
from app.services.storage import delete_document, get_presigned_url, upload_logo

router = APIRouter()


def _slugify(text: str) -> str:
    """Generate a URL-friendly slug from text.

    Args:
        text: The input text to slugify.

    Returns:
        A lowercase, hyphenated slug safe for URLs.
    """
    slug = text.lower().strip()
    # Replace common Serbian Latin characters
    replacements = {
        "č": "c",
        "ć": "c",
        "đ": "dj",
        "š": "s",
        "ž": "z",
        "Č": "c",
        "Ć": "c",
        "Đ": "dj",
        "Š": "s",
        "Ž": "z",
    }
    for char, replacement in replacements.items():
        slug = slug.replace(char, replacement)
    # Replace non-alphanumeric with hyphens and collapse multiples
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


async def _generate_unique_slug(db: AsyncSession, name: str, exclude_id: str | None = None) -> str:
    """Generate a unique slug for an organization.

    Args:
        db: Database session.
        name: The organization name to derive the slug from.
        exclude_id: Organization ID to exclude from uniqueness check (for updates).

    Returns:
        A unique slug string.
    """
    base_slug = _slugify(name)
    if not base_slug:
        base_slug = "org"

    slug = base_slug
    counter = 1
    while True:
        query = select(Organization.id).where(Organization.slug == slug)
        if exclude_id:
            query = query.where(Organization.id != exclude_id)
        result = await db.execute(query)
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """Get the current user's organization details.

    Args:
        db: Database session.
        user: Authenticated user.

    Returns:
        Organization details including name, slug, billing email, and settings.
    """
    result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    logo_url = None
    if org.logo_key:
        logo_url = await asyncio.to_thread(get_presigned_url, org.logo_key)

    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        pib=org.pib,
        billing_email=org.billing_email,
        plan=org.plan,
        settings=org.settings or {},
        logo_url=logo_url,
    )


@router.patch("/current", response_model=OrganizationResponse)
async def update_organization(
    body: OrganizationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> OrganizationResponse:
    """Update the current user's organization settings.

    Only administrators can update organization settings.

    Args:
        body: Fields to update (name, billing_email, pib, settings).
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Updated organization details.
    """
    result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    old_values: dict = {}
    new_values: dict = {}
    update_data = body.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        old = getattr(org, field)
        if old != value:
            old_values[field] = old
            new_values[field] = value
            setattr(org, field, value)

    # Regenerate slug if name changed
    if "name" in new_values:
        old_values["slug"] = org.slug
        org.slug = await _generate_unique_slug(db, org.name, exclude_id=str(org.id))
        new_values["slug"] = org.slug

    if new_values:
        await audit.log(
            db=db,
            action="organization.update",
            request=request,
            organization_id=org.id,
            user_id=user.id,
            entity_type="organization",
            entity_id=org.id,
            old_values=old_values,
            new_values=new_values,
        )
        await db.commit()
        await db.refresh(org)

    logo_url = None
    if org.logo_key:
        logo_url = await asyncio.to_thread(get_presigned_url, org.logo_key)

    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        pib=org.pib,
        billing_email=org.billing_email,
        plan=org.plan,
        settings=org.settings or {},
        logo_url=logo_url,
    )


_LOGO_MAX_SIZE = 2 * 1024 * 1024  # 2 MB
_LOGO_ALLOWED_TYPES = {"image/png", "image/jpeg"}


@router.post("/current/logo")
async def upload_organization_logo(
    file: Annotated[UploadFile, File(description="Organization logo (PNG or JPG, max 2 MB)")],
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict:
    """Upload or replace the organization logo.

    Args:
        file: Image file (PNG or JPG, max 2 MB).
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Dict with the presigned logo URL.
    """
    if file.content_type not in _LOGO_ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG and JPG images are allowed",
        )

    content = await file.read()
    if len(content) > _LOGO_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must not exceed 2 MB",
        )

    result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Delete old logo if exists
    if org.logo_key:
        await asyncio.to_thread(delete_document, org.logo_key)

    # Upload new logo
    key = await asyncio.to_thread(upload_logo, user.organization_id, content, file.content_type)
    org.logo_key = key

    await audit.log(
        db=db,
        action="organization.logo_upload",
        request=request,
        organization_id=org.id,
        user_id=user.id,
        entity_type="organization",
        entity_id=org.id,
        new_values={"logo_key": key},
    )
    await db.commit()

    logo_url = await asyncio.to_thread(get_presigned_url, key)
    return {"logo_url": logo_url}


@router.delete("/current/logo")
async def delete_organization_logo(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict:
    """Remove the organization logo.

    Args:
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Success message.
    """
    result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if not org.logo_key:
        return {"message": "No logo to remove"}

    await asyncio.to_thread(delete_document, org.logo_key)
    old_key = org.logo_key
    org.logo_key = None

    await audit.log(
        db=db,
        action="organization.logo_delete",
        request=request,
        organization_id=org.id,
        user_id=user.id,
        entity_type="organization",
        entity_id=org.id,
        old_values={"logo_key": old_key},
    )
    await db.commit()

    return {"message": "Logo removed"}
