"""
Watchlists API routes.

Provides full CRUD for user watchlists and individual watched assets.
All endpoints require authentication and enforce strict user data isolation.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistDetailResponse,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistSummaryResponse,
    WatchlistUpdate,
)
from app.services import watchlist_service as svc

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


@router.get(
    "",
    response_model=list[WatchlistSummaryResponse],
    summary="List user's watchlists",
)
async def list_watchlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WatchlistSummaryResponse]:
    """Retrieve all watchlists created by the authenticated user."""
    return await svc.list_watchlists(db, current_user)


@router.post(
    "",
    response_model=WatchlistDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new watchlist",
)
async def create_watchlist(
    body: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchlistDetailResponse:
    """Create a new watchlist with optional initial symbols."""
    return await svc.create_watchlist(
        db=db,
        user=current_user,
        name=body.name,
        description=body.description,
        symbols=body.symbols,
    )


@router.get(
    "/{watchlist_id}",
    response_model=WatchlistDetailResponse,
    summary="Get watchlist details",
)
async def get_watchlist(
    watchlist_id: uuid.UUID,
    enrich: bool = Query(default=True, description="Enrich items with live market quotes if available"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchlistDetailResponse:
    """Retrieve full details of a specific watchlist and its tracked assets."""
    try:
        return await svc.get_watchlist(
            db=db,
            user=current_user,
            watchlist_id=watchlist_id,
            enrich_market_data=enrich,
        )
    except svc.WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch(
    "/{watchlist_id}",
    response_model=WatchlistDetailResponse,
    summary="Update watchlist metadata",
)
async def update_watchlist(
    watchlist_id: uuid.UUID,
    body: WatchlistUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchlistDetailResponse:
    """Update name or description of an existing watchlist."""
    try:
        return await svc.update_watchlist(
            db=db,
            user=current_user,
            watchlist_id=watchlist_id,
            name=body.name,
            description=body.description,
        )
    except svc.WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{watchlist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a watchlist",
)
async def delete_watchlist(
    watchlist_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a watchlist and all its associated items."""
    try:
        await svc.delete_watchlist(db=db, user=current_user, watchlist_id=watchlist_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except svc.WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/{watchlist_id}/items",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a crypto symbol to a watchlist",
)
async def add_watchlist_item(
    watchlist_id: uuid.UUID,
    body: WatchlistItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchlistItemResponse:
    """Add a new crypto symbol to the specified watchlist."""
    try:
        return await svc.add_item(
            db=db,
            user=current_user,
            watchlist_id=watchlist_id,
            symbol=body.symbol,
            notes=body.notes,
        )
    except svc.WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except svc.DuplicateSymbolError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.delete(
    "/{watchlist_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a symbol from a watchlist",
)
async def remove_watchlist_item(
    watchlist_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a tracked asset item from a watchlist."""
    try:
        await svc.remove_item(
            db=db,
            user=current_user,
            watchlist_id=watchlist_id,
            item_id=item_id,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except svc.WatchlistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except svc.WatchlistItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
