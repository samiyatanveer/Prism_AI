"""
Tests: Market service — ticker and candle retrieval with mocked provider.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.exchanges.base import ExchangeAPIError, ExchangeRateLimitError
from app.exchanges.binance.normalizers import normalize_ticker, normalize_candles
from tests.conftest import BINANCE_TICKER_RESPONSE, BINANCE_KLINES_RESPONSE


class TestNormalizedTickerFields:
    """Verify ticker normalization produces correct PrismAI field names."""

    def test_ticker_has_correct_fields(self):
        ticker = normalize_ticker(BINANCE_TICKER_RESPONSE)
        # These are PrismAI-owned field names — must be present
        assert hasattr(ticker, "symbol")
        assert hasattr(ticker, "base_asset")
        assert hasattr(ticker, "quote_asset")
        assert hasattr(ticker, "price")
        assert hasattr(ticker, "change_24h_pct")
        assert hasattr(ticker, "volume_24h")
        assert hasattr(ticker, "high_24h")
        assert hasattr(ticker, "low_24h")
        assert hasattr(ticker, "timestamp")

    def test_price_is_decimal(self):
        ticker = normalize_ticker(BINANCE_TICKER_RESPONSE)
        assert isinstance(ticker.price, Decimal)

    def test_change_pct_sign(self):
        raw = {**BINANCE_TICKER_RESPONSE, "priceChangePercent": "-3.14"}
        ticker = normalize_ticker(raw)
        assert ticker.change_24h_pct == Decimal("-3.14")


class TestNormalizedCandleFields:
    """Verify candle normalization produces correct PrismAI field names."""

    def test_candle_has_correct_fields(self):
        candles = normalize_candles(BINANCE_KLINES_RESPONSE)
        c = candles[0]
        assert hasattr(c, "open_time")
        assert hasattr(c, "open")
        assert hasattr(c, "high")
        assert hasattr(c, "low")
        assert hasattr(c, "close")
        assert hasattr(c, "volume")

    def test_all_prices_are_decimal(self):
        candles = normalize_candles(BINANCE_KLINES_RESPONSE)
        c = candles[0]
        assert all(isinstance(v, Decimal) for v in [c.open, c.high, c.low, c.close, c.volume])

    def test_ohlcv_values_correct(self):
        candles = normalize_candles(BINANCE_KLINES_RESPONSE)
        c = candles[0]
        assert c.open == Decimal("65000.00")
        assert c.high == Decimal("68000.00")
        assert c.low == Decimal("64000.00")
        assert c.close == Decimal("67000.00")
        assert c.volume == Decimal("100.5")


class TestIntervalValidation:
    """Valid and invalid interval values."""

    def test_valid_intervals(self):
        from app.services.market_service import _VALID_INTERVALS
        for i in ["1m", "15m", "1h", "4h", "1d", "1w"]:
            assert i in _VALID_INTERVALS

    def test_invalid_interval_detected(self):
        from app.services.market_service import _VALID_INTERVALS
        assert "10x" not in _VALID_INTERVALS
        assert "daily" not in _VALID_INTERVALS
