"""RuleClientAssociation: many-to-many link between automation rules and clients.

A rule with *zero* client associations is "global" — it applies to every
invoice in the organization. A rule with one or more associations is
"scoped" — it only fires for invoices whose ``client_id`` matches one of
the attached clients. This lets an agency keep most generic rules unattached
(applies everywhere) and only scope exception rules to specific clients.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class RuleClientAssociation(Base, UUIDMixin):
    """Attaches an automation rule to a specific client."""

    __tablename__ = "rule_client_associations"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("rule_id", "client_id", name="uq_rule_client"),
        Index("ix_rule_client_rule_id", "rule_id"),
        Index("ix_rule_client_client_id", "client_id"),
    )
