"""
Exchange provider registry / factory.

Returns the correct ``BaseExchangeProvider`` for a given exchange name.
Adding a new exchange means registering it here — no other file changes needed.
"""

from app.exchanges.base import BaseExchangeProvider
from app.exchanges.binance.provider import BinanceProvider

_SUPPORTED_EXCHANGES: dict[str, type[BaseExchangeProvider]] = {
    "binance": BinanceProvider,
}


def get_supported_exchanges() -> list[str]:
    """Return list of supported exchange names."""
    return list(_SUPPORTED_EXCHANGES.keys())


def get_provider(
    exchange_name: str,
    encrypted_api_key: str,
    encrypted_api_secret: str,
) -> BaseExchangeProvider:
    """
    Instantiate the provider for *exchange_name* with encrypted credentials.

    :raises ValueError: if the exchange is not supported.
    """
    name = exchange_name.lower()
    provider_cls = _SUPPORTED_EXCHANGES.get(name)
    if provider_cls is None:
        raise ValueError(
            f"Exchange '{name}' is not supported. "
            f"Supported: {list(_SUPPORTED_EXCHANGES)}"
        )
    return provider_cls(
        encrypted_api_key=encrypted_api_key,
        encrypted_api_secret=encrypted_api_secret,
    )


def get_public_market_provider() -> BaseExchangeProvider:
    """Return the primary provider for public market-data endpoints.

    Binance ticker and candle endpoints do not require account credentials.
    Keeping this separate from account providers prevents public browsing from
    decrypting or depending on a user's exchange connection.
    """
    return BinanceProvider(encrypted_api_key="", encrypted_api_secret="")
