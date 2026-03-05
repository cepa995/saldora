"""
ExportTemplate model.

Database-backed export templates that allow organizations to customize
which fields appear in exported files, their display order, and labels.
System default templates have organization_id=NULL and is_default=True.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class ExportTemplate(Base, UUIDMixin, TimestampMixin):
    """Custom or system-default export template.

    Templates define which invoice fields to include in an export,
    their display order, and custom column labels. System defaults
    (organization_id=NULL) are available to all organizations.

    Attributes:
        organization_id: Owning organization, or NULL for system defaults.
        name: Template display name, unique per organization.
        description: Optional longer description.
        is_default: True for system-provided templates (cannot be modified).
        fields: Ordered list of field definitions [{key, label, order}].
        date_format: Optional date format override (DD.MM.YYYY or YYYY-MM-DD).
        decimal_separator: Optional decimal separator override (',' or '.').
        supported_formats: Export formats this template supports.
        created_by: User who created the template, NULL for system defaults.
    """

    __tablename__ = "export_templates"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Ordered field definitions: [{key: str, label: str, order: int}, ...]
    fields: Mapped[list] = mapped_column(JSONB, nullable=False)

    # Format overrides (applied when using this template)
    date_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decimal_separator: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Which export formats this template can be used with
    supported_formats: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Creator (NULL for system defaults)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped[Organization | None] = relationship()
    creator: Mapped[User | None] = relationship(foreign_keys=[created_by])

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_template_name_per_org"),
        Index("ix_export_templates_org_id", "organization_id"),
    )
