"""
Watchlist Pydantic schemas for request validation and API responses.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class WatchlistItemCreate(BaseModel):
    """Payload to add a new symbol to a watchlist."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Trading pair symbol (e.g. BTCUSDT, ETH, SOL)",
        examples=["BTCUSDT"],
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional personal notes about this asset",
    )


class WatchlistItemResponse(BaseModel):
    """A single watched item with optional real-time market data enrichment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    watchlist_id: uuid.UUID
    symbol: str
    added_price: Decimal | None = None
    notes: str | None = None
    created_at: datetime

    # Real-time market data enrichment (None if exchange disconnected or data unavailable)
    price: Decimal | None = None
    change_24h_pct: Decimal | None = None
    high_24h: Decimal | None = None
    low_24h: Decimal | None = None
    volume_24h: Decimal | None = None
    quote_asset: str | None = None


class WatchlistCreate(BaseModel):
    """Payload to create a new watchlist."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Watchlist name",
        examples=["Primary Watchlist", "DeFi Core"],
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Optional description",
        examples=["Key tokens to monitor for Q4"],
    )
    symbols: list[str] | None = Field(
        default=None,
        description="Optional list of initial symbols to add",
        examples=[["BTCUSDT", "ETHUSDT"]],
    )


class WatchlistUpdate(BaseModel):
    """Payload to update watchlist metadata."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New watchlist name",
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="New watchlist description",
    )


class WatchlistSummaryResponse(BaseModel):
    """Summary representation of a watchlist in lists."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    item_count: int = 0
    created_at: datetime
    updated_at: datetime


class WatchlistDetailResponse(BaseModel):
    """Full detail of a watchlist including its items and live market metrics."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    items: list[WatchlistItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
