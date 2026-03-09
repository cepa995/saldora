"""Pydantic schemas for invitation management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class InvitationCreate(BaseModel):
    """Request schema for creating an invitation."""

    email: EmailStr = Field(description="Email to invite")
    role: str = Field(
        default="operator",
        description="Role to assign: admin, manager, operator, or viewer",
        pattern="^(admin|manager|operator|viewer)$",
    )


class InvitationResponse(BaseModel):
    """Response schema for an invitation."""

    id: UUID = Field(description="Invitation UUID")
    email: str = Field(description="Invited email address")
    role: str = Field(description="Assigned role")
    status: str = Field(description="Invitation status")
    token: str = Field(description="Invitation token")
    invited_by: UUID = Field(description="User who sent the invitation")
    organization_id: UUID = Field(description="Target organization")
    expires_at: datetime = Field(description="When the invitation expires")
    created_at: datetime = Field(description="When the invitation was created")

    model_config = {"from_attributes": True}


class InvitationPublicInfo(BaseModel):
    """Public info about an invitation (no auth required)."""

    organization_name: str = Field(description="Organization name")
    role: str = Field(description="Role being offered")
    email: str = Field(description="Invited email")
    expires_at: datetime = Field(description="Expiration time")


class AcceptInvitationRequest(BaseModel):
    """Request schema for accepting an invitation as a new user."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    password: str = Field(min_length=8, description="Password for new account")
