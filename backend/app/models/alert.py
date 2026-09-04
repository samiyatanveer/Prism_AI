"""
Alert SQLAlchemy model.

Stores price and condition threshold alerts configured by users.
Strict user isolation enforced via foreign keys and query filters.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AlertCondition(str, PyEnum):
    ABOVE = "above"
    BELOW = "below"


class AlertStatus(str, PyEnum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISABLED = "disabled"


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-configured price threshold alert."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_user_id_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Crypto symbol, e.g. "BTCUSDT", "ETHUSDT"
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    # "above" | "below"
    condition: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=AlertCondition.ABOVE.value,
    )
    # "active" | "triggered" | "disabled"
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AlertStatus.ACTIVE.value,
    )
    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    triggered_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert id={self.id} user_id={self.user_id} symbol={self.symbol!r} condition={self.condition!r} target={self.target_price} status={self.status!r}>"
