"""ZZPL compliance schemas for consent, deletion requests, DPAs, and breach notifications."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ---- Consent ----


CONSENT_TYPES = Literal["basic_processing", "analytics", "marketing"]


class ConsentGrant(BaseModel):
    """Request body for granting consent."""

    consent_type: CONSENT_TYPES = Field(description="Type of consent to grant")
    consent_text_version: str | None = Field(
        default=None, description="Version of the consent text shown to user"
    )


class ConsentRevoke(BaseModel):
    """Request body for revoking consent."""

    consent_type: CONSENT_TYPES = Field(description="Type of consent to revoke")


class ConsentStatusResponse(BaseModel):
    """Current consent status for a single type."""

    consent_type: str = Field(description="Consent type identifier")
    granted: bool = Field(description="Whether consent is currently active")
    granted_at: datetime | None = Field(description="When consent was last granted")
    revoked_at: datetime | None = Field(description="When consent was last revoked")


class ConsentRecordResponse(BaseModel):
    """Full consent record for history."""

    id: UUID
    user_id: UUID
    consent_type: str
    granted: bool
    granted_at: datetime | None
    revoked_at: datetime | None
    ip_address: str | None
    consent_text_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Deletion requests ----


DELETION_REQUEST_TYPES = Literal["user_only", "full_org", "specific_data"]


class DeletionRequestCreate(BaseModel):
    """Request body for creating a data deletion request."""

    request_type: DELETION_REQUEST_TYPES = Field(
        default="user_only", description="Scope of deletion"
    )
    data_categories: list[str] | None = Field(
        default=None,
        description="Specific data categories to delete (for specific_data type)",
    )


class DeletionRequestResponse(BaseModel):
    """Deletion request details."""

    id: UUID
    user_id: UUID
    organization_id: UUID | None
    request_type: str
    status: str
    data_categories: dict | None
    retained_categories: dict | None
    processed_by: UUID | None
    processed_at: datetime | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeletionRequestProcess(BaseModel):
    """Request body for processing a deletion request (admin)."""

    status: Literal["completed", "rejected"] = Field(description="New status")
    reason: str | None = Field(default=None, description="Reason for rejection or processing notes")


# ---- DPA ----


class DPACreate(BaseModel):
    """Request body for creating a data processing agreement."""

    title: str = Field(description="Agreement title", max_length=255)
    version: str = Field(description="Agreement version", max_length=20)
    effective_from: date = Field(description="Start date of the agreement")
    effective_until: date | None = Field(default=None, description="End date of the agreement")


class DPAResponse(BaseModel):
    """Data processing agreement details."""

    id: UUID
    organization_id: UUID
    title: str
    version: str
    content_hash: str | None
    signed_by: UUID | None
    signed_at: datetime | None
    effective_from: date
    effective_until: date | None
    status: str
    file_key: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---- Breach notification ----


class BreachNotificationTemplate(BaseModel):
    """Input for generating a breach notification preview."""

    incident_date: date = Field(description="Date of the incident")
    description: str = Field(description="Description of the breach")
    affected_data_types: list[str] = Field(description="Types of personal data affected")
    measures_taken: str = Field(description="Measures taken to address the breach")
    recommendations: str = Field(description="Recommendations for affected users")


class BreachNotificationResponse(BaseModel):
    """Rendered breach notification in Serbian."""

    subject: str = Field(description="Notification subject line")
    body: str = Field(description="Full notification body in Serbian")


# ---- Privacy policy ----


class PrivacyPolicyResponse(BaseModel):
    """Current privacy policy."""

    version: str = Field(description="Policy version identifier")
    effective_date: date = Field(description="Date the policy became effective")
    content: str = Field(description="Policy content in Serbian")
