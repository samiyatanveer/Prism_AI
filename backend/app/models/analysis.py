"""
Analysis SQLAlchemy model.

Stores structured AI intelligence and technical analysis reports generated for users.
Strict user isolation enforced via foreign keys and query filters.
"""

import uuid
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, Index, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AssessmentCategory(str, PyEnum):
    BUY_GRADUALLY = "Buy Gradually"
    HOLD = "Hold"
    CONSIDER_SELLING = "Consider Selling"
    INSUFFICIENT_CONTEXT = "Insufficient Context"


class RiskLevel(str, PyEnum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"


class Analysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A saved AI intelligence and technical analysis report."""

    __tablename__ = "analyses"
    __table_args__ = (
        Index("ix_analyses_user_id_symbol", "user_id", "symbol"),
        Index("ix_analyses_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Crypto symbol, e.g. "BTCUSDT", "ETHUSDT"
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    # "Buy Gradually" | "Hold" | "Consider Selling" | "Insufficient Context"
    assessment: Mapped[str] = mapped_column(String(30), nullable=False)
    # "Low" | "Moderate" | "High"
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RiskLevel.MODERATE.value,
    )
    market_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1D")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured data
    key_price_levels: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    technical_indicators: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} user_id={self.user_id} symbol={self.symbol!r} assessment={self.assessment!r} price={self.market_price}>"
