"""
Exchange connection management service.

Handles connect, disconnect, list, and credential validation.
All credential encryption/decryption is delegated to security.py and
the exchange provider. This service never handles plaintext credentials.
Audit logs are written for all connection state changes.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import encrypt_credential
from app.exchanges.base import ExchangeCredentialError, ExchangeAPIError
from app.exchanges.registry import get_provider, get_supported_exchanges
from app.models.audit_log import AuditLog
from app.models.exchange import ConnectedExchange
from app.models.user import User

logger = get_logger(__name__)


class ExchangeNotFoundError(Exception):
    """Exchange record not found or does not belong to this user."""


class ExchangeAlreadyConnectedError(Exception):
    """User already has an active connection to this exchange."""


class ExchangeValidationError(Exception):
    """Credentials were rejected by the exchange during connect."""


# ── Connection management ─────────────────────────────────────────────────────

async def connect_exchange(
    db: AsyncSession,
    user: User,
    exchange_name: str,
    api_key: str,
    api_secret: str,
    display_label: str | None = None,
    ip_address: str | None = None,
) -> ConnectedExchange:
    """
    Validate credentials against the live exchange, then encrypt and store.

    Steps:
    1. Check for existing active connection (one per exchange per user).
    2. Validate credentials via a live exchange ping.
    3. Encrypt api_key and api_secret with AES-256-GCM.
    4. Persist ConnectedExchange record.
    5. Write audit log.

    :raises ExchangeAlreadyConnectedError: if already connected to this exchange.
    :raises ExchangeValidationError: if credentials are rejected by the exchange.
    :raises ValueError: if exchange_name is not supported.
    """
    # Normalize name
    exchange_name = exchange_name.lower()
    if exchange_name not in get_supported_exchanges():
        raise ValueError(f"Exchange '{exchange_name}' is not supported.")

    # One active connection per exchange per user
    existing = await db.execute(
        select(ConnectedExchange).where(
            ConnectedExchange.user_id == user.id,
            ConnectedExchange.exchange_name == exchange_name,
            ConnectedExchange.is_active == True,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ExchangeAlreadyConnectedError(
            f"You already have an active {exchange_name} connection. "
            "Disconnect it first to reconnect."
        )

    # Validate credentials against the live exchange BEFORE encrypting/storing.
    # We encrypt temporarily to pass to the provider (which decrypts internally).
    # This avoids ever holding plaintext beyond this call stack.
    encrypted_key_temp = encrypt_credential(api_key)
    encrypted_secret_temp = encrypt_credential(api_secret)

    provider = None
    try:
        provider = get_provider(exchange_name, encrypted_key_temp, encrypted_secret_temp)
        await provider.validate_credentials()
    except ExchangeCredentialError:
        raise ExchangeValidationError(
            "The API key or secret was rejected by the exchange. "
            "Check that your credentials are correct and have read permissions."
        )
    except ExchangeAPIError:
        raise ExchangeValidationError(
            "Could not verify credentials. The exchange may be temporarily unavailable."
        )
    finally:
        # Discard temp encrypted blobs and provider
        del encrypted_key_temp, encrypted_secret_temp
        if provider is not None:
            del provider

    # Encrypt final credentials for storage
    exchange = ConnectedExchange(
        user_id=user.id,
        exchange_name=exchange_name,
        encrypted_api_key=encrypt_credential(api_key),
        encrypted_api_secret=encrypt_credential(api_secret),
        display_label=display_label,
        permissions="read-only spot",
        is_active=True,
        last_synced_at=datetime.now(timezone.utc),
    )
    db.add(exchange)
    await db.flush()

    # Audit log — action only, no credentials
    db.add(AuditLog(
        created_at=datetime.now(timezone.utc),
        user_id=user.id,
        action="exchange.connected",
        resource_type="connected_exchange",
        resource_id=str(exchange.id),
        ip_address=ip_address,
        details=f"exchange={exchange_name}",
    ))

    await db.commit()
    await db.refresh(exchange)

    logger.info(
        "Exchange connected",
        extra={"user_id": str(user.id), "exchange": exchange_name},
    )
    return exchange


async def disconnect_exchange(
    db: AsyncSession,
    user: User,
    exchange_id: str,
    ip_address: str | None = None,
) -> None:
    """
    Soft-delete an exchange connection (sets is_active=False).

    :raises ExchangeNotFoundError: if not found or not owned by user.
    """
    result = await db.execute(
        select(ConnectedExchange).where(
            ConnectedExchange.id == exchange_id,
            ConnectedExchange.user_id == user.id,
            ConnectedExchange.is_active == True,  # noqa: E712
        )
    )
    exchange = result.scalar_one_or_none()
    if exchange is None:
        raise ExchangeNotFoundError("Exchange connection not found.")

    exchange.is_active = False
    db.add(AuditLog(
        created_at=datetime.now(timezone.utc),
        user_id=user.id,
        action="exchange.disconnected",
        resource_type="connected_exchange",
        resource_id=str(exchange.id),
        ip_address=ip_address,
        details=f"exchange={exchange.exchange_name}",
    ))
    await db.commit()

    logger.info(
        "Exchange disconnected",
        extra={"user_id": str(user.id), "exchange_id": exchange_id},
    )


async def list_exchanges(
    db: AsyncSession,
    user: User,
) -> list[ConnectedExchange]:
    """Return all active exchange connections for the user."""
    result = await db.execute(
        select(ConnectedExchange).where(
            ConnectedExchange.user_id == user.id,
            ConnectedExchange.is_active == True,  # noqa: E712
        ).order_by(ConnectedExchange.created_at)
    )
    return list(result.scalars().all())


async def get_exchange(
    db: AsyncSession,
    user: User,
    exchange_id: str,
) -> ConnectedExchange:
    """
    Fetch a single active exchange owned by the user.

    :raises ExchangeNotFoundError: if not found.
    """
    result = await db.execute(
        select(ConnectedExchange).where(
            ConnectedExchange.id == exchange_id,
            ConnectedExchange.user_id == user.id,
            ConnectedExchange.is_active == True,  # noqa: E712
        )
    )
    exchange = result.scalar_one_or_none()
    if exchange is None:
        raise ExchangeNotFoundError("Exchange connection not found.")
    return exchange


async def validate_exchange_credentials(
    db: AsyncSession,
    user: User,
    exchange_id: str,
) -> dict:
    """
    Make a live credential check for an existing connection.

    :returns: {"valid": bool, "message": str}
    Never exposes credential material in the return value or exceptions.
    """
    exchange = await get_exchange(db, user, exchange_id)

    try:
        provider = get_provider(
            exchange.exchange_name,
            exchange.encrypted_api_key,
            exchange.encrypted_api_secret,
        )
        await provider.validate_credentials()
        return {"valid": True, "message": "Credentials are valid."}
    except ExchangeCredentialError:
        return {
            "valid": False,
            "message": "Credentials were rejected by the exchange.",
        }
    except ExchangeAPIError:
        return {
            "valid": False,
            "message": "Could not reach the exchange. Please try again later.",
        }


async def sync_exchange(
    db: AsyncSession,
    user: User,
    exchange_id: str,
    ip_address: str | None = None,
) -> ConnectedExchange:
    """Refresh a connection's permitted account data and timestamp.

    This intentionally performs a read-only balance request; no orders or
    account settings are changed.  Portfolio data is always fetched live, so
    only sync metadata is persisted.
    """
    exchange = await get_exchange(db, user, exchange_id)
    provider = get_provider(
        exchange.exchange_name, exchange.encrypted_api_key, exchange.encrypted_api_secret
    )
    await provider.get_balances()
    exchange.last_synced_at = datetime.now(timezone.utc)
    db.add(AuditLog(
        created_at=exchange.last_synced_at, user_id=user.id, action="exchange.synced",
        resource_type="connected_exchange", resource_id=str(exchange.id),
        ip_address=ip_address, details=f"exchange={exchange.exchange_name}",
    ))
    await db.commit()
    await db.refresh(exchange)
    return exchange
