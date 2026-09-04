"""
Market data service.

Retrieves ticker and OHLCV candle data from the exchange provider.
Always uses the user's first active exchange connection.
Returns normalized PrismAI types only.
"""

import json
from datetime import datetime
from decimal import Decimal

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.config import get_settings
from app.exchanges.base import NormalizedCandle, NormalizedTicker
from app.exchanges.registry import get_provider, get_public_market_provider
from app.models.exchange import ConnectedExchange
from app.models.user import User

logger = get_logger(__name__)
settings = get_settings()

_VALID_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"}


class NoExchangeConnectedError(Exception):
    """User has no active exchange connection."""


async def _cache_get(key: str) -> dict | list | None:
    """Read public market data from Redis without making cache failures fatal."""
    client = aioredis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
    try:
        raw = await client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None
    finally:
        await client.aclose()


async def _cache_set(key: str, value: dict | list, ttl_seconds: int) -> None:
    """Cache public market data opportunistically; authoritative fetches still work without Redis."""
    client = aioredis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
    try:
        await client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        pass
    finally:
        await client.aclose()


def _ticker_from_cache(data: dict) -> NormalizedTicker:
    return NormalizedTicker(
        symbol=data["symbol"], base_asset=data["base_asset"], quote_asset=data["quote_asset"],
        price=Decimal(data["price"]), change_24h_pct=Decimal(data["change_24h_pct"]),
        volume_24h=Decimal(data["volume_24h"]), high_24h=Decimal(data["high_24h"]),
        low_24h=Decimal(data["low_24h"]), timestamp=datetime.fromisoformat(data["timestamp"]),
    )


def _ticker_to_cache(ticker: NormalizedTicker) -> dict:
    return {
        "symbol": ticker.symbol, "base_asset": ticker.base_asset, "quote_asset": ticker.quote_asset,
        "price": str(ticker.price), "change_24h_pct": str(ticker.change_24h_pct),
        "volume_24h": str(ticker.volume_24h), "high_24h": str(ticker.high_24h),
        "low_24h": str(ticker.low_24h), "timestamp": ticker.timestamp.isoformat(),
    }


def _candles_from_cache(data: list[dict]) -> list[NormalizedCandle]:
    return [NormalizedCandle(open_time=datetime.fromisoformat(row["open_time"]), open=Decimal(row["open"]),
                             high=Decimal(row["high"]), low=Decimal(row["low"]),
                             close=Decimal(row["close"]), volume=Decimal(row["volume"])) for row in data]


def _candles_to_cache(candles: list[NormalizedCandle]) -> list[dict]:
    return [{"open_time": candle.open_time.isoformat(), "open": str(candle.open), "high": str(candle.high),
             "low": str(candle.low), "close": str(candle.close), "volume": str(candle.volume)} for candle in candles]


async def _get_active_provider(db: AsyncSession, user: User):
    """
    Return the provider for the user's first active exchange connection.

    :raises NoExchangeConnectedError: if no active connection exists.
    """
    result = await db.execute(
        select(ConnectedExchange).where(
            ConnectedExchange.user_id == user.id,
            ConnectedExchange.is_active == True,  # noqa: E712
        ).order_by(ConnectedExchange.created_at).limit(1)
    )
    exchange = result.scalar_one_or_none()
    if exchange is None:
        # Public market endpoints are intentionally credential-free.  This
        # lets authenticated users research an asset before connecting an
        # exchange, while portfolio endpoints remain strictly account scoped.
        return get_public_market_provider()
    return get_provider(
        exchange.exchange_name,
        exchange.encrypted_api_key,
        exchange.encrypted_api_secret,
    )


async def get_ticker(
    db: AsyncSession,
    user: User,
    symbol: str,
) -> NormalizedTicker:
    """
    Fetch 24-hour ticker for *symbol* from the user's active exchange.

    :raises NoExchangeConnectedError: if no exchange is connected.
    :raises ExchangeAPIError: on exchange failures.
    """
    normalized_symbol = symbol.upper().strip()
    cache_key = f"market:ticker:{normalized_symbol}"
    cached = await _cache_get(cache_key)
    if isinstance(cached, dict):
        return _ticker_from_cache(cached)
    provider = await _get_active_provider(db, user)
    ticker = await provider.get_ticker(normalized_symbol)
    await _cache_set(cache_key, _ticker_to_cache(ticker), ttl_seconds=20)
    return ticker


async def get_tickers(
    db: AsyncSession,
    user: User,
    symbols: list[str],
) -> dict[str, NormalizedTicker]:
    """
    Fetch 24-hour tickers for multiple *symbols* in a single batch operation where possible.
    Returns a mapping of symbol (uppercase) -> NormalizedTicker.

    :raises NoExchangeConnectedError: if no exchange is connected.
    """
    if not symbols:
        return {}
    provider = await _get_active_provider(db, user)
    cleaned_symbols = [s.upper().strip() for s in symbols if s.strip()]
    
    # Try bulk provider method
    try:
        tickers = await provider.get_tickers(cleaned_symbols)
        return {t.symbol.upper(): t for t in tickers}
    except Exception as exc:
        logger.warning("Bulk tickers fetch failed, falling back to individual lookups", extra={"error": str(exc)})
        # Fallback to individual calls
        result = {}
        for sym in cleaned_symbols:
            try:
                t = await provider.get_ticker(sym)
                result[t.symbol.upper()] = t
            except Exception:
                continue
        return result


async def get_candles(
    db: AsyncSession,
    user: User,
    symbol: str,
    interval: str = "1d",
    limit: int = 90,
) -> list[NormalizedCandle]:
    """
    Fetch OHLCV candles for *symbol*.

    :raises ValueError: if interval is not a supported value.
    :raises NoExchangeConnectedError: if no exchange is connected.
    """
    if interval not in _VALID_INTERVALS:
        raise ValueError(
            f"Invalid interval '{interval}'. "
            f"Supported: {sorted(_VALID_INTERVALS)}"
        )
    limit = max(1, min(limit, 1000))
    normalized_symbol = symbol.upper().strip()
    cache_key = f"market:candles:{normalized_symbol}:{interval}:{limit}"
    cached = await _cache_get(cache_key)
    if isinstance(cached, list):
        return _candles_from_cache(cached)
    provider = await _get_active_provider(db, user)
    candles = await provider.get_candles(normalized_symbol, interval, limit)
    await _cache_set(cache_key, _candles_to_cache(candles), ttl_seconds=120)
    return candles
