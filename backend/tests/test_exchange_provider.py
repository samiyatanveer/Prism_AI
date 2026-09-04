"""
Tests: Binance normalizers and provider abstraction.

Verifies:
- Normalized types contain no Binance-specific field names
- All normalizer edge cases (zero balances filtered, asset pair splitting, etc.)
- NormalizedBalance.estimated_usd_value defaults to None from normalizer
"""

from decimal import Decimal
from datetime import datetime, timezone

import pytest

from app.exchanges.binance.normalizers import (
    normalize_ticker,
    normalize_candle,
    normalize_candles,
    normalize_balances,
)
from app.exchanges.base import NormalizedTicker, NormalizedCandle, NormalizedBalance
from tests.conftest import (
    BINANCE_TICKER_RESPONSE,
    BINANCE_KLINES_RESPONSE,
    BINANCE_ACCOUNT_RESPONSE,
    BINANCE_EMPTY_ACCOUNT_RESPONSE,
)


class TestNormalizeTicker:
    def test_basic_fields(self):
        ticker = normalize_ticker(BINANCE_TICKER_RESPONSE)
        assert isinstance(ticker, NormalizedTicker)
        assert ticker.symbol == "BTCUSDT"
        assert ticker.base_asset == "BTC"
        assert ticker.quote_asset == "USDT"
        assert ticker.price == Decimal("67000.00")
        assert ticker.change_24h_pct == Decimal("2.5")
        assert ticker.volume_24h == Decimal("1234.56")
        assert ticker.high_24h == Decimal("68000.00")
        assert ticker.low_24h == Decimal("65000.00")

    def test_no_binance_field_names_in_result(self):
        """The normalized type must not expose any Binance-specific field names."""
        ticker = normalize_ticker(BINANCE_TICKER_RESPONSE)
        ticker_dict = ticker.__dict__ if hasattr(ticker, "__dict__") else {}
        binance_fields = {"lastPrice", "priceChangePercent", "highPrice", "lowPrice"}
        for field in binance_fields:
            assert field not in ticker_dict, f"Binance field '{field}' leaked into normalized type"

    def test_eth_btc_pair_splitting(self):
        raw = {**BINANCE_TICKER_RESPONSE, "symbol": "ETHBTC", "lastPrice": "0.05"}
        ticker = normalize_ticker(raw)
        assert ticker.base_asset == "ETH"
        assert ticker.quote_asset == "BTC"

    def test_unknown_quote_asset(self):
        raw = {**BINANCE_TICKER_RESPONSE, "symbol": "UNKNOWNPAIR"}
        ticker = normalize_ticker(raw)
        # Falls back to empty quote asset, full symbol as base
        assert ticker.symbol == "UNKNOWNPAIR"

    def test_missing_fields_default_to_zero(self):
        ticker = normalize_ticker({"symbol": "BTCUSDT"})
        assert ticker.price == Decimal("0")
        assert ticker.change_24h_pct == Decimal("0")


class TestNormalizeCandle:
    def test_single_candle(self):
        candle = normalize_candle(BINANCE_KLINES_RESPONSE[0])
        assert isinstance(candle, NormalizedCandle)
        assert candle.open == Decimal("65000.00")
        assert candle.high == Decimal("68000.00")
        assert candle.low == Decimal("64000.00")
        assert candle.close == Decimal("67000.00")
        assert candle.volume == Decimal("100.5")
        assert isinstance(candle.open_time, datetime)
        assert candle.open_time.tzinfo is not None  # timezone-aware

    def test_candle_list(self):
        candles = normalize_candles(BINANCE_KLINES_RESPONSE * 3)
        assert len(candles) == 3
        assert all(isinstance(c, NormalizedCandle) for c in candles)


class TestNormalizeBalances:
    def test_filters_zero_balances(self):
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        assets = [b.asset for b in balances]
        assert "ETH" not in assets  # ETH has zero free and locked

    def test_non_zero_balances_returned(self):
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        assert len(balances) == 2
        btc = next(b for b in balances if b.asset == "BTC")
        assert btc.free == Decimal("0.5")
        assert btc.locked == Decimal("0.0")

    def test_usd_value_always_none_from_normalizer(self):
        """Normalizer must never set estimated_usd_value — that's portfolio service's job."""
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        for b in balances:
            assert b.estimated_usd_value is None

    def test_empty_account_returns_empty_list(self):
        balances = normalize_balances(BINANCE_EMPTY_ACCOUNT_RESPONSE)
        assert balances == []

    def test_missing_balances_key(self):
        balances = normalize_balances({})
        assert balances == []
