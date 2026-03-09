"""Pydantic schemas for join request management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JoinRequestCreate(BaseModel):
    """Request schema for submitting a join request."""

    organization_id: UUID = Field(description="Organization to join")
    message: str | None = Field(
        default=None,
        max_length=500,
        description="Optional message to admin",
    )


class JoinRequestResponse(BaseModel):
    """Response schema for a join request."""

    id: UUID = Field(description="Join request UUID")
    organization_id: UUID = Field(description="Target organization")
    user_id: UUID = Field(description="Requesting user")
    message: str | None = Field(default=None, description="Optional message")
    status: str = Field(description="Request status: pending, approved, rejected")
    reviewed_by: UUID | None = Field(default=None, description="Admin who reviewed")
    reviewed_at: datetime | None = Field(default=None, description="Review timestamp")
    created_at: datetime = Field(description="When the request was created")

    # Enriched fields (set in router, not from model)
    user_email: str | None = Field(default=None, description="Requester email")
    user_name: str | None = Field(default=None, description="Requester full name")
    organization_name: str | None = Field(default=None, description="Organization name")

    model_config = {"from_attributes": True}


class OrganizationSearchResult(BaseModel):
    """Public organization info for search results."""

    id: UUID = Field(description="Organization UUID")
    name: str = Field(description="Organization name")
    slug: str = Field(description="URL-friendly identifier")
