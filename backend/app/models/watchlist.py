"""
Watchlist and WatchlistItem SQLAlchemy models.

Supports multiple named watchlists per user, with unique symbols per watchlist.
User-scoped data isolation enforced via foreign keys and query filters.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Watchlist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-created watchlist of crypto assets."""

    __tablename__ = "watchlists"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="watchlists")
    items: Mapped[list["WatchlistItem"]] = relationship(
        "WatchlistItem",
        back_populates="watchlist",
        cascade="all, delete-orphan",
        order_by="WatchlistItem.created_at",
    )

    def __repr__(self) -> str:
        return f"<Watchlist id={self.id} user_id={self.user_id} name={self.name!r}>"


class WatchlistItem(UUIDPrimaryKeyMixin, Base):
    """A single crypto asset tracked within a watchlist."""

    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol", name="uq_watchlist_symbol"),
    )

    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Ticker / trading pair symbol, e.g. "BTCUSDT", "ETHUSDT", "SOL"
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    added_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    watchlist: Mapped["Watchlist"] = relationship("Watchlist", back_populates="items")

    def __repr__(self) -> str:
        return f"<WatchlistItem id={self.id} watchlist_id={self.watchlist_id} symbol={self.symbol!r}>"
