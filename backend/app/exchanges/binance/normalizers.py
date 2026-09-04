"""
Binance response normalizers.

Converts raw Binance API response dicts into PrismAI-owned normalized types.
All Binance-specific field names are contained in this file only.
No Binance field names are exposed to callers.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.exchanges.base import NormalizedBalance, NormalizedCandle, NormalizedTicker


def _dec(value: str | float | int) -> Decimal:
    """Safe Decimal conversion — returns Decimal('0') on failure."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def normalize_ticker(raw: dict) -> NormalizedTicker:
    """
    Normalize a Binance 24hr ticker response dict.

    Expected Binance fields:
      symbol, lastPrice, priceChangePercent, volume, highPrice, lowPrice
    """
    symbol: str = raw.get("symbol", "")

    # Derive base/quote asset from the symbol string.
    # Binance does not return these separately in the 24hr ticker endpoint.
    # Common quote assets ordered by length to ensure correct splitting.
    quote_asset = ""
    base_asset = symbol
    for q in ("USDT", "BUSD", "BTC", "ETH", "BNB", "USDC", "TUSD"):
        if symbol.endswith(q):
            quote_asset = q
            base_asset = symbol[: -len(q)]
            break

    return NormalizedTicker(
        symbol=symbol,
        base_asset=base_asset,
        quote_asset=quote_asset,
        price=_dec(raw.get("lastPrice", "0")),
        change_24h_pct=_dec(raw.get("priceChangePercent", "0")),
        volume_24h=_dec(raw.get("volume", "0")),
        high_24h=_dec(raw.get("highPrice", "0")),
        low_24h=_dec(raw.get("lowPrice", "0")),
        timestamp=datetime.now(timezone.utc),
    )


def normalize_candle(raw_kline: list) -> NormalizedCandle:
    """
    Normalize a single Binance kline array entry.

    Binance kline array format (index → field):
      0  open_time (ms timestamp)
      1  open
      2  high
      3  low
      4  close
      5  volume
      ... (remaining fields ignored)
    """
    open_time_ms = int(raw_kline[0])
    open_time = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)

    return NormalizedCandle(
        open_time=open_time,
        open=_dec(raw_kline[1]),
        high=_dec(raw_kline[2]),
        low=_dec(raw_kline[3]),
        close=_dec(raw_kline[4]),
        volume=_dec(raw_kline[5]),
    )


def normalize_candles(raw_klines: list[list]) -> list[NormalizedCandle]:
    """Normalize a list of Binance kline arrays."""
    return [normalize_candle(k) for k in raw_klines]


def normalize_balances(raw_account: dict) -> list[NormalizedBalance]:
    """
    Normalize Binance account balances.

    Binance returns all assets; we filter to non-zero balances only.
    ``estimated_usd_value`` is always None here — USD valuation is a
    separate concern handled by the portfolio service.

    Binance account field: "balances" → list of {"asset", "free", "locked"}
    """
    balances = []
    for entry in raw_account.get("balances", []):
        free = _dec(entry.get("free", "0"))
        locked = _dec(entry.get("locked", "0"))
        if free > 0 or locked > 0:
            balances.append(
                NormalizedBalance(
                    asset=entry.get("asset", ""),
                    free=free,
                    locked=locked,
                    estimated_usd_value=None,  # Populated by portfolio service if needed
                )
            )
    return balances
