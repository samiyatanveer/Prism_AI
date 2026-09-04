"""
Binance implementation of BaseExchangeProvider.

This is the only place where BinanceClient is instantiated.
All Binance-specific client calls happen here and the results
are returned as normalized PrismAI types.
"""

from app.exchanges.base import (
    BaseExchangeProvider,
    NormalizedBalance,
    NormalizedCandle,
    NormalizedTicker,
)
from app.exchanges.binance.client import BinanceClient
from app.exchanges.binance.normalizers import (
    normalize_balances,
    normalize_candles,
    normalize_ticker,
)


class BinanceProvider(BaseExchangeProvider):
    """
    Binance exchange provider (read-only).

    Accepts encrypted credential blobs directly from ``ConnectedExchange``.
    Credential plaintext is handled entirely within ``BinanceClient`` and
    never exposed to this class or its callers.
    """

    def __init__(
        self,
        encrypted_api_key: str,
        encrypted_api_secret: str,
    ) -> None:
        self._client = BinanceClient(
            encrypted_api_key=encrypted_api_key,
            encrypted_api_secret=encrypted_api_secret,
        )

    @property
    def exchange_name(self) -> str:
        return "binance"

    async def validate_credentials(self) -> bool:
        """
        Validate credentials by calling the Binance account endpoint.

        :raises ExchangeCredentialError: if credentials are rejected.
        :raises ExchangeAPIError: on other API failures.
        """
        return await self._client.ping()

    async def get_ticker(self, symbol: str) -> NormalizedTicker:
        raw = await self._client.get_ticker_24hr(symbol)
        return normalize_ticker(raw)

    async def get_tickers(self, symbols: list[str]) -> list[NormalizedTicker]:
        if not symbols:
            return []
        raw_list = await self._client.get_tickers_24hr(symbols)
        results = []
        for raw in raw_list:
            try:
                results.append(normalize_ticker(raw))
            except Exception:
                continue
        return results

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 90,
    ) -> list[NormalizedCandle]:
        raw = await self._client.get_klines(symbol, interval, limit)
        return normalize_candles(raw)

    async def get_balances(self) -> list[NormalizedBalance]:
        raw = await self._client.get_account()
        return normalize_balances(raw)
