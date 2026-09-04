import os

# Configure test environment variables before any app module imports get_settings()
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://prism_user:test_pass@localhost:5432/prism_ai_test")
os.environ.setdefault("SECRET_KEY", "test_secret_key_0123456789abcdef0123456789abcdef")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("GROQ_API_KEY", "gsk_test_key_for_unit_tests")

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.exchanges.base import (
    NormalizedBalance,
    NormalizedCandle,
    NormalizedTicker,
)
from datetime import datetime, timezone


# ── Fixture: fake encrypted credential blobs ──────────────────────────────────
# These are valid AES-256-GCM encrypted values produced by encrypt_credential().
# They allow tests to exercise the full service layer without real Binance keys.

@pytest.fixture
def encrypted_key():
    from app.core.security import encrypt_credential
    return encrypt_credential("fake_api_key_for_testing_purposes_only")


@pytest.fixture
def encrypted_secret():
    from app.core.security import encrypt_credential
    return encrypt_credential("fake_api_secret_for_testing_purposes_only")


# ── Fixture: normalized types ─────────────────────────────────────────────────

@pytest.fixture
def sample_ticker():
    return NormalizedTicker(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        price=Decimal("67000.00"),
        change_24h_pct=Decimal("2.5"),
        volume_24h=Decimal("1234.56"),
        high_24h=Decimal("68000.00"),
        low_24h=Decimal("65000.00"),
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_candles():
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        NormalizedCandle(
            open_time=ts,
            open=Decimal("65000"),
            high=Decimal("68000"),
            low=Decimal("64000"),
            close=Decimal("67000"),
            volume=Decimal("100.5"),
        )
    ]


@pytest.fixture
def sample_balances():
    return [
        NormalizedBalance(asset="BTC", free=Decimal("0.5"), locked=Decimal("0.0")),
        NormalizedBalance(asset="USDT", free=Decimal("1000.0"), locked=Decimal("0.0")),
    ]


# ── Fixture: mock Binance HTTP responses ──────────────────────────────────────

BINANCE_TICKER_RESPONSE = {
    "symbol": "BTCUSDT",
    "lastPrice": "67000.00",
    "priceChangePercent": "2.5",
    "volume": "1234.56",
    "highPrice": "68000.00",
    "lowPrice": "65000.00",
}

BINANCE_KLINES_RESPONSE = [
    [
        1704067200000,  # open_time ms
        "65000.00",     # open
        "68000.00",     # high
        "64000.00",     # low
        "67000.00",     # close
        "100.5",        # volume
        1704153599999,  # close_time
        "6750000.00",   # quote volume
        1000,           # trades
        "50.0",         # taker buy base
        "3350000.00",   # taker buy quote
        "0",            # ignore
    ]
]

BINANCE_ACCOUNT_RESPONSE = {
    "balances": [
        {"asset": "BTC", "free": "0.50000000", "locked": "0.00000000"},
        {"asset": "USDT", "free": "1000.00000000", "locked": "0.00000000"},
        {"asset": "ETH", "free": "0.00000000", "locked": "0.00000000"},  # zero — should be filtered
    ]
}

BINANCE_EMPTY_ACCOUNT_RESPONSE = {
    "balances": [
        {"asset": "BTC", "free": "0.00000000", "locked": "0.00000000"},
    ]
}
