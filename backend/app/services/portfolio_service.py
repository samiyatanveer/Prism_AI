"""
Portfolio service.

Fetches and normalizes account balances from the user's active exchange.
USD valuation is derived from live USDT ticker prices using the same
exchange provider — never fabricated or from an external source.
Assets without a USDT market have estimated_usd_value=None.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.exchanges.base import ExchangeError, NormalizedBalance
from app.exchanges.registry import get_provider
from app.models.exchange import ConnectedExchange
from app.models.user import User

logger = get_logger(__name__)

# Stablecoins are treated as 1 USD — no ticker lookup needed.
_STABLECOINS = frozenset({"USDT", "BUSD", "USDC", "TUSD", "FDUSD"})

# Skip USD-valuation for individual assets below this threshold to avoid
# pricing hundreds of near-zero testnet dust positions.
_MIN_BALANCE_FOR_VALUATION = Decimal("0.00001")

# Batch size for the Binance bulk-ticker endpoint.
_TICKER_CHUNK_SIZE = 100


class NoExchangeConnectedError(Exception):
    """User has no active exchange connection."""


async def _get_active_exchange_and_provider(db: AsyncSession, user: User):
    """
    Return (ConnectedExchange, provider) for the user's first active connection.

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
        raise NoExchangeConnectedError(
            "No active exchange connection found. Connect an exchange first."
        )
    provider = get_provider(
        exchange.exchange_name,
        exchange.encrypted_api_key,
        exchange.encrypted_api_secret,
    )
    return exchange, provider


async def get_portfolio(
    db: AsyncSession,
    user: User,
    include_usd_valuation: bool = True,
) -> dict:
    """
    Fetch portfolio holdings and optionally compute USD valuation.

    USD values are derived from a single bulk USDT ticker call against the
    exchange provider. This replaces per-asset concurrent calls that exceed
    Binance rate limits when an account has many small balances (e.g. testnet).

    If include_usd_valuation is False, all values are None.
    Assets with total balance below _MIN_BALANCE_FOR_VALUATION are not priced
    to avoid pricing hundreds of dust positions on test accounts.

    :returns: dict with keys: exchange_name, exchange_id, assets, total_estimated_usd_value
    :raises NoExchangeConnectedError: if no exchange is connected.
    :raises ExchangeAPIError: if the balance fetch fails.
    """
    exchange, provider = await _get_active_exchange_and_provider(db, user)

    # Fetch balances (non-zero only — filtered in normalizer)
    balances: list[NormalizedBalance] = await provider.get_balances()

    if not include_usd_valuation or not balances:
        return {
            "exchange_name": exchange.exchange_name,
            "exchange_id": str(exchange.id),
            "assets": balances,
            "total_estimated_usd_value": None,
        }

    # Build a de-duplicated list of USDT symbols to price.
    # Skip stablecoins (priced at 1:1) and dust below the threshold.
    symbols_to_price: list[str] = []
    seen: set[str] = set()
    for b in balances:
        if b.asset in _STABLECOINS:
            continue
        if (b.free + b.locked) < _MIN_BALANCE_FOR_VALUATION:
            continue
        sym = f"{b.asset}USDT"
        if sym not in seen:
            symbols_to_price.append(sym)
            seen.add(sym)

    # Bulk-fetch tickers in chunks to respect the exchange endpoint limit.
    ticker_map: dict[str, object] = {}
    for chunk_start in range(0, len(symbols_to_price), _TICKER_CHUNK_SIZE):
        chunk = symbols_to_price[chunk_start : chunk_start + _TICKER_CHUNK_SIZE]
        try:
            tickers = await provider.get_tickers(chunk)
            for t in tickers:
                ticker_map[t.symbol] = t
        except ExchangeError:
            # Partial failure — continue with whatever data we have
            logger.warning(
                "Bulk ticker fetch failed for a chunk; some USD values may be missing",
                extra={"chunk_size": len(chunk)},
            )
        except Exception:
            logger.warning("Unexpected error during bulk ticker fetch")
            break

    # Enrich each balance with its USD estimate
    enriched: list[NormalizedBalance] = []
    total_usd = Decimal("0")
    all_valued = True

    for b in balances:
        total = b.free + b.locked
        usd_value: Decimal | None = None

        if b.asset in _STABLECOINS:
            usd_value = total * Decimal("1")
        else:
            sym = f"{b.asset}USDT"
            ticker = ticker_map.get(sym)
            if ticker is not None:
                usd_value = total * ticker.price
            else:
                all_valued = False

        if usd_value is not None:
            total_usd += usd_value

        enriched.append(
            NormalizedBalance(
                asset=b.asset,
                free=b.free,
                locked=b.locked,
                estimated_usd_value=usd_value,
            )
        )

    return {
        "exchange_name": exchange.exchange_name,
        "exchange_id": str(exchange.id),
        "assets": enriched,
        "total_estimated_usd_value": total_usd if all_valued else None,
    }
