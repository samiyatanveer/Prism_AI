"""
Complaint and ComplaintMessage SQLAlchemy models.

Stores user support tickets, issue reports, complaints, and threaded responses.
Strict user isolation enforced via foreign keys and query filters, with role-based admin access.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ComplaintCategory(str, PyEnum):
    ACCOUNT_SECURITY = "Account & Security"
    EXCHANGE_CONNECTION = "Exchange Connection"
    MARKET_DATA = "Market & Charts Data"
    AI_ASSISTANT = "AI Assistant & Analyses"
    PORTFOLIO_TRACKING = "Portfolio Tracking"
    BUG_REPORT = "Bug Report"
    GENERAL_INQUIRY = "General Inquiry"


class ComplaintPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ComplaintStatus(str, PyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Complaint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-submitted complaint or support inquiry."""

    __tablename__ = "complaints"
    __table_args__ = (
        Index("ix_complaints_user_id_status", "user_id", "status"),
        Index("ix_complaints_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ComplaintCategory.GENERAL_INQUIRY.value,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ComplaintPriority.MEDIUM.value,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ComplaintStatus.OPEN.value,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="complaints")
    messages: Mapped[list["ComplaintMessage"]] = relationship(
        "ComplaintMessage",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintMessage.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<Complaint id={self.id} user_id={self.user_id} subject={self.subject!r} status={self.status!r}>"


class ComplaintMessage(UUIDPrimaryKeyMixin, Base):
    """A single threaded message within a complaint conversation."""

    __tablename__ = "complaint_messages"
    __table_args__ = (
        Index("ix_complaint_messages_complaint_id", "complaint_id"),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # "user" | "admin" | "support"
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    complaint = relationship("Complaint", back_populates="messages")
    sender = relationship("User")

    def __repr__(self) -> str:
        return f"<ComplaintMessage id={self.id} complaint_id={self.complaint_id} role={self.sender_role!r}>"
