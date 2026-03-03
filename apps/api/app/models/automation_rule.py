"""
AutomationRule and RuleExecution models.

Organization-specific automation rules that customize invoice processing
(SRS Section 4.11). Rules can auto-assign konta, set VAT treatment,
flag invoices for review, or auto-approve based on configurable conditions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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


class AutomationRule(Base, UUIDMixin, TimestampMixin):
    """Organization-specific automation rule for invoice processing.

    Rules are evaluated in priority order (lower = first) during invoice
    verification. Each rule has conditions (when to apply) and actions
    (what to do).
    """

    __tablename__ = "automation_rules"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )

    # Rule definition
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # KONTO_ASSIGNMENT, VAT_TREATMENT, AUTO_APPROVE,
    # FLAG_FOR_REVIEW, DOCUMENT_TYPE, CUSTOM_FIELD
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Rule logic (JSON)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    actions: Mapped[list] = mapped_column(JSONB, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Statistics
    execution_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped[Organization] = relationship()
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    executions: Mapped[list[RuleExecution]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_rule_name_per_org"),
        Index("ix_automation_rules_org_id", "organization_id"),
        Index(
            "ix_automation_rules_org_active",
            "organization_id",
            "is_active",
            postgresql_where="is_active = true",
        ),
        Index("ix_automation_rules_type", "rule_type"),
    )


class RuleExecution(Base, UUIDMixin):
    """Audit log entry for a single rule execution against an invoice.

    Created each time a rule matches an invoice during verification.
    Provides an audit trail of which rules were applied and what actions
    were taken.
    """

    __tablename__ = "rule_executions"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    accounting_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounting_intents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Execution details
    conditions_matched: Mapped[dict] = mapped_column(JSONB, nullable=False)
    actions_applied: Mapped[list] = mapped_column(JSONB, nullable=False)

    # Timing
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    rule: Mapped[AutomationRule] = relationship(back_populates="executions")

    __table_args__ = (
        Index("ix_rule_executions_rule_id", "rule_id"),
        Index("ix_rule_executions_invoice_id", "invoice_id"),
        Index("ix_rule_executions_executed_at", "executed_at"),
    )
