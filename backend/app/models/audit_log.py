"""Audit log model — tamper-evident record of sensitive operations."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AuditLog(Base):
    """
    Immutable audit trail for security-sensitive actions.

    Rows are INSERT-only — never UPDATE or DELETE.
    user_id is nullable to support pre-authentication events (e.g. failed logins).
    Sensitive data (passwords, tokens, credentials) must NEVER appear in any field.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Who performed the action — nullable for unauthenticated events
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # What happened
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. "user", "exchange", "session"
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # UUID or name of the affected resource
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Optional structured outcome details (no secrets)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action!r}"
            f" user_id={self.user_id} created_at={self.created_at}>"
        )
