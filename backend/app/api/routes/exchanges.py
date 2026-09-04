"""Exchange management API routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.exchange import (
    ConnectExchangeRequest,
    ConnectExchangeResponse,
    ExchangeResponse,
    ExchangeStatusResponse,
)
from app.services import exchange_service as svc
from app.exchanges.base import ExchangeAPIError, ExchangeRateLimitError, ExchangeTimeoutError

router = APIRouter(prefix="/exchanges", tags=["Exchanges"])


def _exchange_to_response(ex) -> ExchangeResponse:
    return ExchangeResponse(
        id=str(ex.id),
        exchange_name=ex.exchange_name,
        display_label=ex.display_label if hasattr(ex, "display_label") else None,
        permissions=ex.permissions,
        is_active=ex.is_active,
        last_synced_at=ex.last_synced_at,
        created_at=ex.created_at,
    )


@router.get("", response_model=list[ExchangeResponse], summary="List connected exchanges")
async def list_exchanges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ExchangeResponse]:
    """Return all active exchange connections for the authenticated user."""
    exchanges = await svc.list_exchanges(db, current_user)
    return [_exchange_to_response(e) for e in exchanges]


@router.post(
    "/connect",
    response_model=ConnectExchangeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a new exchange",
)
async def connect_exchange(
    body: ConnectExchangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConnectExchangeResponse:
    """
    Validate and connect an exchange account.

    Credentials are validated against the live exchange before storage.
    API key and secret are encrypted with AES-256-GCM before being stored.
    They are never returned in any response.
    """
    ip = request.client.host if request.client else None
    try:
        exchange = await svc.connect_exchange(
            db=db,
            user=current_user,
            exchange_name=body.exchange_name,
            api_key=body.api_key,
            api_secret=body.api_secret,
            display_label=body.display_label,
            ip_address=ip,
        )
    except svc.ExchangeAlreadyConnectedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except svc.ExchangeValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return ConnectExchangeResponse(exchange=_exchange_to_response(exchange))


@router.get(
    "/{exchange_id}/status",
    response_model=ExchangeStatusResponse,
    summary="Get exchange connection status",
)
async def exchange_status(
    exchange_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExchangeStatusResponse:
    """Return connection status without making a live credential check."""
    try:
        exchange = await svc.get_exchange(db, current_user, exchange_id)
    except svc.ExchangeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return ExchangeStatusResponse(
        id=str(exchange.id),
        exchange_name=exchange.exchange_name,
        is_active=exchange.is_active,
        last_synced_at=exchange.last_synced_at,
        credential_valid=None,  # Live check not performed here
        message="Connection active.",
    )


@router.post(
    "/{exchange_id}/validate",
    response_model=ExchangeStatusResponse,
    summary="Validate exchange credentials (live check)",
)
async def validate_credentials(
    exchange_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExchangeStatusResponse:
    """Make a live credential check against the exchange."""
    try:
        exchange = await svc.get_exchange(db, current_user, exchange_id)
        result = await svc.validate_exchange_credentials(db, current_user, exchange_id)
    except svc.ExchangeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return ExchangeStatusResponse(
        id=str(exchange.id),
        exchange_name=exchange.exchange_name,
        is_active=exchange.is_active,
        last_synced_at=exchange.last_synced_at,
        credential_valid=result["valid"],
        message=result["message"],
    )


@router.post(
    "/{exchange_id}/sync",
    response_model=ExchangeStatusResponse,
    summary="Refresh permitted exchange account data",
)
async def sync_exchange(
    exchange_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExchangeStatusResponse:
    """Perform a read-only account refresh and record its completion time."""
    try:
        exchange = await svc.sync_exchange(
            db, current_user, exchange_id,
            ip_address=request.client.host if request.client else None,
        )
    except svc.ExchangeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ExchangeRateLimitError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Exchange rate limit reached. Please wait before retrying.")
    except ExchangeTimeoutError:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Exchange did not respond in time.")
    except ExchangeAPIError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Exchange returned an error. Please try again later.")
    return ExchangeStatusResponse(
        id=str(exchange.id), exchange_name=exchange.exchange_name,
        is_active=exchange.is_active, last_synced_at=exchange.last_synced_at,
        credential_valid=True, message="Exchange data refreshed.",
    )


@router.delete(
    "/{exchange_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect an exchange",
)
async def disconnect_exchange(
    exchange_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete an exchange connection (sets is_active=False)."""
    ip = request.client.host if request.client else None
    try:
        await svc.disconnect_exchange(db, current_user, exchange_id, ip_address=ip)
    except svc.ExchangeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
