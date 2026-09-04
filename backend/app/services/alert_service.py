"""
Alert service layer — on-demand price and condition threshold evaluation.

Rules:
- Strictly user-isolated on all queries and mutations.
- Uses bulk ticker lookup via market_service.get_tickers().
- Live evaluation: on-demand when alerts are queried or evaluated.
- 'above': triggers when current_price >= target_price.
- 'below': triggers when current_price <= target_price.
- Triggered alerts record triggered_at timestamp and triggered_price.
- Disabled alerts never trigger.
- Safe degradation: if market data unavailable, returns alerts with null live metrics.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.alert import Alert, AlertCondition, AlertStatus
from app.models.user import User
from app.services import market_service
from app.services.watchlist_service import normalize_market_symbol

logger = get_logger(__name__)


# ── Exceptions ───────────────────────────────────────────────────────────────

class AlertError(Exception):
    """Base exception for alert operations."""


class AlertNotFoundError(AlertError):
    """Alert not found or does not belong to the user."""


# ── Helper: Live Evaluation & Metric Calculation ──────────────────────────────

async def _evaluate_and_enrich_alerts(
    db: AsyncSession,
    user: User,
    alerts: list[Alert],
) -> list[dict[str, Any]]:
    """
    On-demand evaluation of a list of alerts against live market data.
    Fetches bulk tickers, evaluates active alerts against thresholds,
    and returns enriched alert response dictionaries.
    """
    if not alerts:
        return []

    # Map market symbols
    symbol_map: dict[str, list[Alert]] = {}
    for a in alerts:
        m_sym = normalize_market_symbol(a.symbol)
        symbol_map.setdefault(m_sym, []).append(a)

    tickers: dict[str, Any] = {}
    try:
        tickers = await market_service.get_tickers(db, user, list(symbol_map.keys()))
    except market_service.NoExchangeConnectedError:
        logger.debug("No exchange connected — returning alerts without live price evaluation.")
    except Exception as exc:
        logger.warning("Failed to fetch tickers for alert evaluation", extra={"error": str(exc)})

    has_updates = False
    enriched = []
    now_utc = datetime.now(timezone.utc)

    for alert in alerts:
        m_sym = normalize_market_symbol(alert.symbol)
        ticker = tickers.get(m_sym) or tickers.get(alert.symbol.upper())

        current_price = ticker.price if ticker else None
        quote_asset = ticker.quote_asset if ticker else None
        distance_usd = None
        distance_pct = None

        if current_price is not None:
            distance_usd = alert.target_price - current_price
            if current_price > 0:
                distance_pct = ((alert.target_price - current_price) / current_price) * Decimal("100")

            # Check if active alert meets trigger condition
            if alert.status == AlertStatus.ACTIVE.value:
                is_triggered = False
                if alert.condition == AlertCondition.ABOVE.value and current_price >= alert.target_price:
                    is_triggered = True
                elif alert.condition == AlertCondition.BELOW.value and current_price <= alert.target_price:
                    is_triggered = True

                if is_triggered:
                    alert.status = AlertStatus.TRIGGERED.value
                    alert.triggered_at = now_utc
                    alert.triggered_price = current_price
                    has_updates = True

        enriched.append({
            "id": alert.id,
            "symbol": alert.symbol,
            "target_price": alert.target_price,
            "condition": alert.condition,
            "status": alert.status,
            "triggered_at": alert.triggered_at,
            "triggered_price": alert.triggered_price,
            "notes": alert.notes,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at,
            "current_price": current_price,
            "distance_usd": distance_usd,
            "distance_pct": distance_pct,
            "quote_asset": quote_asset,
        })

    if has_updates:
        try:
            await db.commit()
        except Exception as exc:
            logger.warning("Failed to persist alert trigger state", extra={"error": str(exc)})

    return enriched


# ── Core Operations ───────────────────────────────────────────────────────────

async def list_alerts(
    db: AsyncSession,
    user: User,
    status_filter: str | None = None,
    enrich_market_data: bool = True,
) -> list[dict[str, Any]]:
    """
    List alerts for *user*, optionally filtered by status ('active', 'triggered', 'disabled').
    Strictly isolated to the authenticated user.
    """
    query = select(Alert).where(Alert.user_id == user.id)
    if status_filter:
        query = query.where(Alert.status == status_filter.lower().strip())
    query = query.order_by(Alert.created_at.desc())

    result = await db.execute(query)
    alerts = list(result.scalars().all())

    if enrich_market_data:
        return await _evaluate_and_enrich_alerts(db, user, alerts)

    return [
        {
            "id": a.id,
            "symbol": a.symbol,
            "target_price": a.target_price,
            "condition": a.condition,
            "status": a.status,
            "triggered_at": a.triggered_at,
            "triggered_price": a.triggered_price,
            "notes": a.notes,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
            "current_price": None,
            "distance_usd": None,
            "distance_pct": None,
            "quote_asset": None,
        }
        for a in alerts
    ]


async def get_alert(
    db: AsyncSession,
    user: User,
    alert_id: uuid.UUID,
    enrich_market_data: bool = True,
) -> dict[str, Any]:
    """
    Retrieve details for a single alert with user isolation.

    :raises AlertNotFoundError: if alert does not exist or belong to user.
    """
    stmt = select(Alert).where(
        Alert.id == alert_id,
        Alert.user_id == user.id,
    )
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if alert is None:
        raise AlertNotFoundError("Alert not found.")

    if enrich_market_data:
        enriched_list = await _evaluate_and_enrich_alerts(db, user, [alert])
        return enriched_list[0]

    return {
        "id": alert.id,
        "symbol": alert.symbol,
        "target_price": alert.target_price,
        "condition": alert.condition,
        "status": alert.status,
        "triggered_at": alert.triggered_at,
        "triggered_price": alert.triggered_price,
        "notes": alert.notes,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at,
        "current_price": None,
        "distance_usd": None,
        "distance_pct": None,
        "quote_asset": None,
    }


async def create_alert(
    db: AsyncSession,
    user: User,
    symbol: str,
    target_price: Decimal,
    condition: str = "above",
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Create a new price threshold alert for *user*.
    """
    cleaned_symbol = symbol.strip().upper()
    if not cleaned_symbol:
        raise ValueError("Symbol cannot be empty.")
    if target_price <= Decimal("0"):
        raise ValueError("Target price must be greater than 0.")

    cond = condition.strip().lower()
    if cond not in (AlertCondition.ABOVE.value, AlertCondition.BELOW.value):
        raise ValueError("Condition must be either 'above' or 'below'.")

    alert = Alert(
        user_id=user.id,
        symbol=cleaned_symbol,
        target_price=target_price,
        condition=cond,
        status=AlertStatus.ACTIVE.value,
        notes=notes.strip() if notes else None,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    # Perform initial on-demand evaluation
    return await get_alert(db, user, alert.id, enrich_market_data=True)


async def update_alert(
    db: AsyncSession,
    user: User,
    alert_id: uuid.UUID,
    target_price: Decimal | None = None,
    condition: str | None = None,
    status: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Update alert properties.
    If target_price or condition is changed, resets status to 'active'.

    :raises AlertNotFoundError: if alert does not exist or belong to user.
    """
    stmt = select(Alert).where(
        Alert.id == alert_id,
        Alert.user_id == user.id,
    )
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if alert is None:
        raise AlertNotFoundError("Alert not found.")

    is_threshold_changed = False

    if target_price is not None:
        if target_price <= Decimal("0"):
            raise ValueError("Target price must be greater than 0.")
        alert.target_price = target_price
        is_threshold_changed = True

    if condition is not None:
        cond = condition.strip().lower()
        if cond not in (AlertCondition.ABOVE.value, AlertCondition.BELOW.value):
            raise ValueError("Condition must be either 'above' or 'below'.")
        alert.condition = cond
        is_threshold_changed = True

    if status is not None:
        st = status.strip().lower()
        if st not in (AlertStatus.ACTIVE.value, AlertStatus.DISABLED.value, AlertStatus.TRIGGERED.value):
            raise ValueError("Invalid alert status.")
        alert.status = st

    if notes is not None:
        alert.notes = notes.strip() if notes else None

    # Reset trigger if threshold was updated
    if is_threshold_changed and status is None:
        alert.status = AlertStatus.ACTIVE.value
        alert.triggered_at = None
        alert.triggered_price = None

    await db.commit()
    await db.refresh(alert)
    return await get_alert(db, user, alert.id, enrich_market_data=True)


async def toggle_alert_status(
    db: AsyncSession,
    user: User,
    alert_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Toggle alert between 'active' and 'disabled'.
    If currently triggered or disabled, switches to 'active' and clears trigger.

    :raises AlertNotFoundError: if alert does not exist or belong to user.
    """
    stmt = select(Alert).where(
        Alert.id == alert_id,
        Alert.user_id == user.id,
    )
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if alert is None:
        raise AlertNotFoundError("Alert not found.")

    if alert.status == AlertStatus.ACTIVE.value:
        alert.status = AlertStatus.DISABLED.value
    else:
        alert.status = AlertStatus.ACTIVE.value
        alert.triggered_at = None
        alert.triggered_price = None

    await db.commit()
    await db.refresh(alert)
    return await get_alert(db, user, alert.id, enrich_market_data=True)


async def delete_alert(
    db: AsyncSession,
    user: User,
    alert_id: uuid.UUID,
) -> bool:
    """
    Delete an alert.

    :raises AlertNotFoundError: if alert does not exist or belong to user.
    """
    stmt = select(Alert).where(
        Alert.id == alert_id,
        Alert.user_id == user.id,
    )
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if alert is None:
        raise AlertNotFoundError("Alert not found.")

    await db.delete(alert)
    await db.commit()
    return True


async def get_alert_summary(
    db: AsyncSession,
    user: User,
) -> dict[str, int]:
    """
    Return counts of user alerts by status: total, active, triggered, disabled.
    """
    stmt = select(Alert.status, func.count(Alert.id)).where(Alert.user_id == user.id).group_by(Alert.status)
    result = await db.execute(stmt)
    rows = result.all()

    counts = {"total": 0, "active": 0, "triggered": 0, "disabled": 0}
    for status_val, count in rows:
        counts[status_val] = count
        counts["total"] += count

    return counts
