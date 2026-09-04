"""
Watchlist service layer — business logic for user-scoped watchlists and market enrichment.

Enforces strict user isolation on all operations.
Market data enrichment uses bulk fetching when an exchange is connected,
falling back gracefully to null values if disconnected or unsupported.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistItem
from app.services import market_service

logger = get_logger(__name__)


# ── Exceptions ───────────────────────────────────────────────────────────────

class WatchlistError(Exception):
    """Base exception for watchlist operations."""


class WatchlistNotFoundError(WatchlistError):
    """Watchlist does not exist or does not belong to the user."""


class WatchlistItemNotFoundError(WatchlistError):
    """Watchlist item does not exist or does not belong to the user's watchlist."""


class DuplicateSymbolError(WatchlistError):
    """Symbol is already present in this watchlist."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_market_symbol(symbol: str) -> str:
    """
    Format a symbol for exchange market-data lookup.
    E.g. 'BTC' -> 'BTCUSDT', 'SOL-USD' -> 'SOLUSDT', 'ETHUSDT' -> 'ETHUSDT'.
    """
    cleaned = symbol.upper().strip().replace("/", "").replace("-", "")
    known_quotes = ("USDT", "USDC", "FDUSD", "BUSD", "EUR", "TRY", "BTC", "ETH", "BNB")
    if any(cleaned.endswith(q) for q in ("USDT", "USDC", "FDUSD", "BUSD", "EUR", "TRY")):
        return cleaned
    if len(cleaned) > 4 and any(cleaned.endswith(q) for q in ("BTC", "ETH", "BNB")):
        return cleaned
    return cleaned + "USDT"


async def _enrich_items_with_market_data(
    db: AsyncSession,
    user: User,
    items: list[WatchlistItem],
) -> list[dict[str, Any]]:
    """
    Bulk-fetch 24h ticker data for all watchlist items.
    Returns list of item dicts with market fields populated (or None if unavailable).
    Never raises an exception — fails safely on exchange/symbol errors.
    """
    if not items:
        return []

    # Map market symbols to items
    symbol_map: dict[str, list[WatchlistItem]] = {}
    for item in items:
        m_sym = normalize_market_symbol(item.symbol)
        symbol_map.setdefault(m_sym, []).append(item)

    tickers: dict[str, Any] = {}
    try:
        tickers = await market_service.get_tickers(db, user, list(symbol_map.keys()))
    except market_service.NoExchangeConnectedError:
        logger.debug("No exchange connected — returning watchlist items without live market quotes.")
    except Exception as exc:
        logger.warning(
            "Failed to fetch market tickers for watchlist",
            extra={"error": str(exc)},
        )

    enriched_items = []
    for item in items:
        m_sym = normalize_market_symbol(item.symbol)
        ticker = tickers.get(m_sym) or tickers.get(item.symbol.upper())

        enriched_items.append({
            "id": item.id,
            "watchlist_id": item.watchlist_id,
            "symbol": item.symbol,
            "added_price": item.added_price,
            "notes": item.notes,
            "created_at": item.created_at,
            "price": ticker.price if ticker else None,
            "change_24h_pct": ticker.change_24h_pct if ticker else None,
            "high_24h": ticker.high_24h if ticker else None,
            "low_24h": ticker.low_24h if ticker else None,
            "volume_24h": ticker.volume_24h if ticker else None,
            "quote_asset": ticker.quote_asset if ticker else None,
        })

    return enriched_items


# ── Core Operations ───────────────────────────────────────────────────────────

async def list_watchlists(
    db: AsyncSession,
    user: User,
) -> list[dict[str, Any]]:
    """
    List all watchlists belonging to *user* with item counts.
    Strictly isolated to the authenticated user.
    """
    stmt = (
        select(
            Watchlist,
            func.count(WatchlistItem.id).label("item_count"),
        )
        .outerjoin(WatchlistItem, Watchlist.id == WatchlistItem.watchlist_id)
        .where(Watchlist.user_id == user.id)
        .group_by(Watchlist.id)
        .order_by(Watchlist.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": wl.id,
            "name": wl.name,
            "description": wl.description,
            "item_count": item_count,
            "created_at": wl.created_at,
            "updated_at": wl.updated_at,
        }
        for wl, item_count in rows
    ]


async def get_watchlist(
    db: AsyncSession,
    user: User,
    watchlist_id: uuid.UUID,
    enrich_market_data: bool = True,
) -> dict[str, Any]:
    """
    Retrieve full details of a watchlist and its items.
    Enforces user isolation at query level.

    :raises WatchlistNotFoundError: if watchlist does not exist or belong to user.
    """
    stmt = (
        select(Watchlist)
        .options(selectinload(Watchlist.items))
        .where(
            Watchlist.id == watchlist_id,
            Watchlist.user_id == user.id,
        )
    )
    result = await db.execute(stmt)
    wl = result.scalar_one_or_none()
    if wl is None:
        raise WatchlistNotFoundError("Watchlist not found.")

    if enrich_market_data:
        items = await _enrich_items_with_market_data(db, user, wl.items)
    else:
        items = [
            {
                "id": it.id,
                "watchlist_id": it.watchlist_id,
                "symbol": it.symbol,
                "added_price": it.added_price,
                "notes": it.notes,
                "created_at": it.created_at,
                "price": None,
                "change_24h_pct": None,
                "high_24h": None,
                "low_24h": None,
                "volume_24h": None,
                "quote_asset": None,
            }
            for it in wl.items
        ]

    return {
        "id": wl.id,
        "name": wl.name,
        "description": wl.description,
        "items": items,
        "created_at": wl.created_at,
        "updated_at": wl.updated_at,
    }


async def create_watchlist(
    db: AsyncSession,
    user: User,
    name: str,
    description: str | None = None,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create a new watchlist for *user*, optionally adding initial symbols.
    """
    wl = Watchlist(
        user_id=user.id,
        name=name.strip(),
        description=description.strip() if description else None,
    )
    db.add(wl)
    await db.flush()

    if symbols:
        seen = set()
        for sym in symbols:
            cleaned_sym = sym.strip().upper()
            if not cleaned_sym or cleaned_sym in seen:
                continue
            seen.add(cleaned_sym)

            # Optional: attempt to get current price as added_price
            added_price = None
            try:
                m_sym = normalize_market_symbol(cleaned_sym)
                ticker = await market_service.get_ticker(db, user, m_sym)
                added_price = ticker.price
            except Exception:
                pass

            item = WatchlistItem(
                watchlist_id=wl.id,
                symbol=cleaned_sym,
                added_price=added_price,
            )
            db.add(item)

    await db.commit()
    await db.refresh(wl)
    return await get_watchlist(db, user, wl.id, enrich_market_data=True)


async def update_watchlist(
    db: AsyncSession,
    user: User,
    watchlist_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """
    Update watchlist metadata (name / description).

    :raises WatchlistNotFoundError: if not found or unauthorized.
    """
    stmt = select(Watchlist).where(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == user.id,
    )
    result = await db.execute(stmt)
    wl = result.scalar_one_or_none()
    if wl is None:
        raise WatchlistNotFoundError("Watchlist not found.")

    if name is not None:
        wl.name = name.strip()
    if description is not None:
        wl.description = description.strip() if description else None

    await db.commit()
    await db.refresh(wl)
    return await get_watchlist(db, user, wl.id, enrich_market_data=True)


async def delete_watchlist(
    db: AsyncSession,
    user: User,
    watchlist_id: uuid.UUID,
) -> bool:
    """
    Delete a watchlist and all its items (cascading).

    :raises WatchlistNotFoundError: if not found or unauthorized.
    """
    stmt = select(Watchlist).where(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == user.id,
    )
    result = await db.execute(stmt)
    wl = result.scalar_one_or_none()
    if wl is None:
        raise WatchlistNotFoundError("Watchlist not found.")

    await db.delete(wl)
    await db.commit()
    return True


async def add_item(
    db: AsyncSession,
    user: User,
    watchlist_id: uuid.UUID,
    symbol: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Add a crypto symbol to an existing watchlist.

    :raises WatchlistNotFoundError: if watchlist does not exist or belong to user.
    :raises DuplicateSymbolError: if symbol is already in this watchlist.
    """
    stmt = select(Watchlist).where(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == user.id,
    )
    result = await db.execute(stmt)
    wl = result.scalar_one_or_none()
    if wl is None:
        raise WatchlistNotFoundError("Watchlist not found.")

    cleaned_sym = symbol.strip().upper()
    if not cleaned_sym:
        raise ValueError("Symbol cannot be empty.")

    # Check for existing item with same symbol in this watchlist
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.symbol == cleaned_sym,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise DuplicateSymbolError(f"{cleaned_sym} is already in this watchlist.")

    # Fetch current market price as added_price if available
    added_price = None
    ticker_data = None
    try:
        m_sym = normalize_market_symbol(cleaned_sym)
        ticker_data = await market_service.get_ticker(db, user, m_sym)
        added_price = ticker_data.price
    except Exception:
        pass

    item = WatchlistItem(
        watchlist_id=watchlist_id,
        symbol=cleaned_sym,
        added_price=added_price,
        notes=notes.strip() if notes else None,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "id": item.id,
        "watchlist_id": item.watchlist_id,
        "symbol": item.symbol,
        "added_price": item.added_price,
        "notes": item.notes,
        "created_at": item.created_at,
        "price": ticker_data.price if ticker_data else None,
        "change_24h_pct": ticker_data.change_24h_pct if ticker_data else None,
        "high_24h": ticker_data.high_24h if ticker_data else None,
        "low_24h": ticker_data.low_24h if ticker_data else None,
        "volume_24h": ticker_data.volume_24h if ticker_data else None,
        "quote_asset": ticker_data.quote_asset if ticker_data else None,
    }


async def remove_item(
    db: AsyncSession,
    user: User,
    watchlist_id: uuid.UUID,
    item_id: uuid.UUID,
) -> bool:
    """
    Remove an item from a watchlist.

    :raises WatchlistNotFoundError: if watchlist does not exist or belong to user.
    :raises WatchlistItemNotFoundError: if item does not exist in this watchlist.
    """
    # Verify watchlist ownership
    stmt = select(Watchlist).where(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == user.id,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise WatchlistNotFoundError("Watchlist not found.")

    item_stmt = select(WatchlistItem).where(
        WatchlistItem.id == item_id,
        WatchlistItem.watchlist_id == watchlist_id,
    )
    item_result = await db.execute(item_stmt)
    item = item_result.scalar_one_or_none()
    if item is None:
        raise WatchlistItemNotFoundError("Item not found in this watchlist.")

    await db.delete(item)
    await db.commit()
    return True
