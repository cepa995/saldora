"""Pydantic schemas for team member management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TeamMemberResponse(BaseModel):
    """Response schema for a team member."""

    id: UUID = Field(description="User UUID")
    email: str = Field(description="Email address")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    role: str = Field(description="Role within the organization")
    email_verified: bool = Field(description="Whether email is verified")
    created_at: datetime = Field(description="When the user joined")

    model_config = {"from_attributes": True}


class UpdateMemberRoleRequest(BaseModel):
    """Request schema for updating a member's role."""

    role: str = Field(
        description="New role: admin, manager, operator, or viewer",
        pattern="^(admin|manager|operator|viewer)$",
    )
