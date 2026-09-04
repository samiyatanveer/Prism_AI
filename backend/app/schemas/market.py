"""Market data response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TickerResponse(BaseModel):
    """24-hour ticker statistics."""

    symbol: str
    base_asset: str
    quote_asset: str
    price: Decimal
    change_24h_pct: Decimal
    volume_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    timestamp: datetime


class CandleResponse(BaseModel):
    """Single OHLCV candlestick."""

    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class CandlesResponse(BaseModel):
    """Candlestick list response."""

    symbol: str
    interval: str
    candles: list[CandleResponse]

    model_config = {"from_attributes": True}
