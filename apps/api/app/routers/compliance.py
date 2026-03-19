"""ZZPL compliance router — consent, deletion requests, DPAs, breach notifications."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.consent_record import ConsentRecord
from app.models.data_processing_agreement import DataProcessingAgreement
from app.models.deletion_request import DeletionRequest
from app.models.user import User
from app.schemas.compliance import (
    BreachNotificationResponse,
    BreachNotificationTemplate,
    ConsentGrant,
    ConsentRecordResponse,
    ConsentRevoke,
    ConsentStatusResponse,
    DeletionRequestCreate,
    DeletionRequestProcess,
    DeletionRequestResponse,
    DPACreate,
    DPAResponse,
    PrivacyPolicyResponse,
)
from app.services import audit
from app.services.compliance import (
    PRIVACY_POLICY_CONTENT,
    PRIVACY_POLICY_EFFECTIVE_DATE,
    PRIVACY_POLICY_VERSION,
    anonymize_user_data,
    get_deletion_retained_categories,
    render_breach_notification,
)

router = APIRouter()


# ---- Consent ----


@router.post(
    "/consent",
    response_model=ConsentRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_consent(
    body: ConsentGrant,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConsentRecordResponse:
    """Grant consent for a specific data processing type.

    Args:
        body: Consent grant details.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user.

    Returns:
        Created consent record.
    """
    record = ConsentRecord(
        organization_id=user.organization_id,
        user_id=user.id,
        consent_type=body.consent_type,
        granted=True,
        granted_at=datetime.now(UTC),
        ip_address=getattr(request.state, "ip_address", None),
        user_agent=getattr(request.state, "user_agent", None),
        consent_text_version=body.consent_text_version,
    )
    db.add(record)

    await audit.log(
        db=db,
        action="consent.grant",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="consent",
        new_values={"consent_type": body.consent_type},
    )

    await db.commit()
    await db.refresh(record)
    return record


@router.post("/consent/revoke", status_code=status.HTTP_200_OK)
async def revoke_consent(
    body: ConsentRevoke,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Revoke consent for a specific data processing type.

    Args:
        body: Consent revocation details.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user.

    Returns:
        Confirmation message.
    """
    if body.consent_type == "basic_processing":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Osnovna obrada podataka ne može biti opozvana",
        )

    record = ConsentRecord(
        organization_id=user.organization_id,
        user_id=user.id,
        consent_type=body.consent_type,
        granted=False,
        revoked_at=datetime.now(UTC),
        ip_address=getattr(request.state, "ip_address", None),
        user_agent=getattr(request.state, "user_agent", None),
    )
    db.add(record)

    await audit.log(
        db=db,
        action="consent.revoke",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="consent",
        new_values={"consent_type": body.consent_type},
    )

    await db.commit()
    return {"message": f"Saglasnost za {body.consent_type} je opozvana"}


@router.get("/consent", response_model=list[ConsentStatusResponse])
async def list_consent_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ConsentStatusResponse]:
    """List current consent status for all types.

    Args:
        db: Database session.
        user: Authenticated user.

    Returns:
        List of consent statuses per type.
    """
    consent_types = ["basic_processing", "analytics", "marketing"]
    statuses = []

    for ct in consent_types:
        result = await db.execute(
            select(ConsentRecord)
            .where(
                ConsentRecord.organization_id == user.organization_id,
                ConsentRecord.user_id == user.id,
                ConsentRecord.consent_type == ct,
            )
            .order_by(ConsentRecord.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        statuses.append(
            ConsentStatusResponse(
                consent_type=ct,
                granted=latest.granted if latest else False,
                granted_at=latest.granted_at if latest else None,
                revoked_at=latest.revoked_at if latest else None,
            )
        )

    return statuses


@router.get("/consent/history", response_model=list[ConsentRecordResponse])
async def list_consent_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> list[ConsentRecordResponse]:
    """List full consent history for the organization (admin only).

    Args:
        db: Database session.
        user: Authenticated admin user.

    Returns:
        List of all consent records.
    """
    result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.organization_id == user.organization_id)
        .order_by(ConsentRecord.created_at.desc())
    )
    return list(result.scalars().all())


# ---- Deletion requests ----


@router.post(
    "/deletion-requests",
    response_model=DeletionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_deletion_request(
    body: DeletionRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeletionRequestResponse:
    """Request deletion of personal data (ZZPL Article 30).

    Args:
        body: Deletion request details.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user.

    Returns:
        Created deletion request.
    """
    existing = await db.execute(
        select(DeletionRequest).where(
            DeletionRequest.user_id == user.id,
            DeletionRequest.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Već postoji zahtev za brisanje na čekanju",
        )

    dr = DeletionRequest(
        user_id=user.id,
        organization_id=user.organization_id,
        request_type=body.request_type,
        status="pending",
        data_categories=body.data_categories,
    )
    db.add(dr)

    await audit.log(
        db=db,
        action="deletion_request.create",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="deletion_request",
        new_values={"request_type": body.request_type},
    )

    await db.commit()
    await db.refresh(dr)
    return dr


@router.get("/deletion-requests", response_model=list[DeletionRequestResponse])
async def list_deletion_requests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> list[DeletionRequestResponse]:
    """List all deletion requests for the organization (admin only).

    Args:
        db: Database session.
        user: Authenticated admin user.

    Returns:
        List of deletion requests.
    """
    result = await db.execute(
        select(DeletionRequest)
        .where(DeletionRequest.organization_id == user.organization_id)
        .order_by(DeletionRequest.created_at.desc())
    )
    return list(result.scalars().all())


@router.get(
    "/deletion-requests/{request_id}",
    response_model=DeletionRequestResponse,
)
async def get_deletion_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> DeletionRequestResponse:
    """Get a specific deletion request (admin only).

    Args:
        request_id: UUID of the deletion request.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Deletion request details.
    """
    result = await db.execute(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id,
            DeletionRequest.organization_id == user.organization_id,
        )
    )
    dr = result.scalar_one_or_none()
    if not dr:
        raise HTTPException(status_code=404, detail="Zahtev nije pronađen")
    return dr


@router.post(
    "/deletion-requests/{request_id}/process",
    response_model=DeletionRequestResponse,
)
async def process_deletion_request(
    request_id: str,
    body: DeletionRequestProcess,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> DeletionRequestResponse:
    """Process a deletion request — complete or reject (admin only).

    When completed, user profile data is anonymized while invoices
    and audit logs are retained per legal requirements.

    Args:
        request_id: UUID of the deletion request.
        body: Processing action and optional reason.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Updated deletion request.
    """
    result = await db.execute(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id,
            DeletionRequest.organization_id == user.organization_id,
        )
    )
    dr = result.scalar_one_or_none()
    if not dr:
        raise HTTPException(status_code=404, detail="Zahtev nije pronađen")

    if dr.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zahtev je već obrađen",
        )

    now = datetime.now(UTC)
    dr.status = body.status
    dr.processed_by = user.id
    dr.processed_at = now
    dr.reason = body.reason

    if body.status == "completed":
        # Anonymize the requesting user's profile data
        target_result = await db.execute(select(User).where(User.id == dr.user_id))
        target_user = target_result.scalar_one_or_none()
        if target_user:
            old_values = anonymize_user_data(target_user)
            await audit.log(
                db=db,
                action="user.anonymize",
                request=request,
                organization_id=user.organization_id,
                user_id=user.id,
                entity_type="user",
                entity_id=dr.user_id,
                old_values=old_values,
                new_values={"status": "anonymized"},
            )

        dr.retained_categories = get_deletion_retained_categories()

    await audit.log(
        db=db,
        action=f"deletion_request.{body.status}",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="deletion_request",
        entity_id=dr.id,
        new_values={"status": body.status, "reason": body.reason},
    )

    await db.commit()
    await db.refresh(dr)
    return dr


# ---- DPA ----


@router.post(
    "/dpa",
    response_model=DPAResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dpa(
    body: DPACreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> DPAResponse:
    """Create a data processing agreement.

    Args:
        body: DPA details.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Created DPA.
    """
    dpa = DataProcessingAgreement(
        organization_id=user.organization_id,
        title=body.title,
        version=body.version,
        effective_from=body.effective_from,
        effective_until=body.effective_until,
        status="draft",
    )
    db.add(dpa)

    await audit.log(
        db=db,
        action="dpa.create",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="dpa",
        new_values={"title": body.title, "version": body.version},
    )

    await db.commit()
    await db.refresh(dpa)
    return dpa


@router.get("/dpa", response_model=list[DPAResponse])
async def list_dpas(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> list[DPAResponse]:
    """List all data processing agreements for the organization.

    Args:
        db: Database session.
        user: Authenticated admin user.

    Returns:
        List of DPAs.
    """
    result = await db.execute(
        select(DataProcessingAgreement)
        .where(DataProcessingAgreement.organization_id == user.organization_id)
        .order_by(DataProcessingAgreement.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/dpa/{dpa_id}", response_model=DPAResponse)
async def get_dpa(
    dpa_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> DPAResponse:
    """Get a specific data processing agreement.

    Args:
        dpa_id: UUID of the DPA.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        DPA details.
    """
    result = await db.execute(
        select(DataProcessingAgreement).where(
            DataProcessingAgreement.id == dpa_id,
            DataProcessingAgreement.organization_id == user.organization_id,
        )
    )
    dpa = result.scalar_one_or_none()
    if not dpa:
        raise HTTPException(status_code=404, detail="Ugovor nije pronađen")
    return dpa


@router.post("/dpa/{dpa_id}/sign", response_model=DPAResponse)
async def sign_dpa(
    dpa_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> DPAResponse:
    """Sign a data processing agreement, activating it.

    Args:
        dpa_id: UUID of the DPA to sign.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Updated DPA with signed status.
    """
    result = await db.execute(
        select(DataProcessingAgreement).where(
            DataProcessingAgreement.id == dpa_id,
            DataProcessingAgreement.organization_id == user.organization_id,
        )
    )
    dpa = result.scalar_one_or_none()
    if not dpa:
        raise HTTPException(status_code=404, detail="Ugovor nije pronađen")

    if dpa.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Samo nacrt ugovora može biti potpisan",
        )

    dpa.signed_by = user.id
    dpa.signed_at = datetime.now(UTC)
    dpa.status = "active"

    await audit.log(
        db=db,
        action="dpa.sign",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="dpa",
        entity_id=dpa.id,
        new_values={"status": "active"},
    )

    await db.commit()
    await db.refresh(dpa)
    return dpa


# ---- Breach notification ----


@router.post(
    "/breach-notification/preview",
    response_model=BreachNotificationResponse,
)
async def preview_breach_notification(
    body: BreachNotificationTemplate,
    _user: User = Depends(require_role("admin")),
) -> BreachNotificationResponse:
    """Generate a breach notification preview in Serbian.

    Args:
        body: Breach incident details.
        _user: Authenticated admin user.

    Returns:
        Rendered notification subject and body.
    """
    return render_breach_notification(body)


# ---- Privacy policy ----


@router.get("/privacy-policy", response_model=PrivacyPolicyResponse)
async def get_privacy_policy() -> PrivacyPolicyResponse:
    """Get the current privacy policy (public endpoint, no auth required).

    Returns:
        Privacy policy content in Serbian with version info.
    """
    return PrivacyPolicyResponse(
        version=PRIVACY_POLICY_VERSION,
        effective_date=PRIVACY_POLICY_EFFECTIVE_DATE,
        content=PRIVACY_POLICY_CONTENT,
    )
