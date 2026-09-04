"""
Exchange provider abstraction — normalized types and base interface.

All exchange-specific logic lives in provider subpackages (e.g. binance/).
The normalized types defined here are the only exchange-related types
that cross package boundaries into services, routes, or schemas.
No exchange-specific field names or structures should appear outside their
own subpackage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


# ── Custom exceptions ─────────────────────────────────────────────────────────

class ExchangeError(Exception):
    """Base class for all exchange-related errors."""


class ExchangeAPIError(ExchangeError):
    """
    Non-2xx or unexpected response from the exchange.

    IMPORTANT: The ``message`` parameter must NEVER contain API key or
    secret material. Sanitize before raising.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        # Numeric/provider error codes are safe diagnostics.  Never attach an
        # exchange-provided message here: it could reflect request data.
        self.error_code = error_code


class ExchangeCredentialError(ExchangeAPIError):
    """
    Invalid API key or signature rejected by the exchange (HTTP 401/403).
    Message must not contain key material.
    """


class ExchangeRateLimitError(ExchangeAPIError):
    """Rate limit hit (HTTP 429 / 418 from Binance)."""


class ExchangeTimeoutError(ExchangeError):
    """Exchange did not respond within the configured timeout."""


# ── Normalized data types ─────────────────────────────────────────────────────
# These are PrismAI-owned types; exchange-specific field names never appear here.


@dataclass(frozen=True)
class NormalizedTicker:
    """24-hour ticker statistics for a trading pair."""

    symbol: str          # e.g. "BTCUSDT"
    base_asset: str      # e.g. "BTC"
    quote_asset: str     # e.g. "USDT"
    price: Decimal
    change_24h_pct: Decimal
    volume_24h: Decimal   # in base asset units
    high_24h: Decimal
    low_24h: Decimal
    timestamp: datetime


@dataclass(frozen=True)
class NormalizedCandle:
    """OHLCV candlestick for a single period."""

    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal       # base asset volume


@dataclass(frozen=True)
class NormalizedBalance:
    """
    Normalized asset balance from an exchange account.

    ``estimated_usd_value`` is None when no USDT market exists for
    the asset or valuation was not requested. Never fabricate a value.
    """

    asset: str            # e.g. "BTC"
    free: Decimal
    locked: Decimal
    estimated_usd_value: Decimal | None = None


# ── Abstract provider interface ───────────────────────────────────────────────

class BaseExchangeProvider(ABC):
    """
    Abstract interface for exchange providers.

    Implementors must:
    - Return only normalized PrismAI types — no exchange-specific objects
    - Never log, raise, or propagate API keys or secrets
    - Raise ``ExchangeCredentialError`` for auth failures
    - Raise ``ExchangeRateLimitError`` for rate-limit responses
    - Raise ``ExchangeTimeoutError`` for network/timeout failures
    - Raise ``ExchangeAPIError`` for all other unexpected exchange errors
    """

    @property
    @abstractmethod
    def exchange_name(self) -> str:
        """Canonical lowercase name, e.g. 'binance'."""

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Make a lightweight authenticated call to verify the credentials work.

        :returns: True if valid.
        :raises ExchangeCredentialError: if credentials are rejected.
        :raises ExchangeAPIError: on other API failures.
        """

    @abstractmethod
    async def get_ticker(self, symbol: str) -> NormalizedTicker:
        """
        Fetch 24-hour ticker statistics for *symbol*.

        :param symbol: Exchange trading pair, e.g. "BTCUSDT".
        :raises ExchangeAPIError: on failure.
        """

    @abstractmethod
    async def get_tickers(self, symbols: list[str]) -> list[NormalizedTicker]:
        """
        Fetch 24-hour ticker statistics for multiple *symbols*.

        :param symbols: List of exchange trading pairs, e.g. ["BTCUSDT", "ETHUSDT"].
        :raises ExchangeAPIError: on failure.
        """

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 90,
    ) -> list[NormalizedCandle]:
        """
        Fetch OHLCV candles for *symbol*.

        :param symbol: Trading pair, e.g. "BTCUSDT".
        :param interval: Time interval string, e.g. "1d", "1h", "15m".
        :param limit: Number of candles to return (max 1000).
        :raises ExchangeAPIError: on failure.
        """

    @abstractmethod
    async def get_balances(self) -> list[NormalizedBalance]:
        """
        Fetch account balances (read-only account data).

        Only non-zero balances are returned.

        :raises ExchangeCredentialError: if credentials are rejected.
        :raises ExchangeAPIError: on other failures.
        """
