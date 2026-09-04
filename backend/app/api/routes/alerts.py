"""
Alerts API routes.

Provides endpoints for creating, listing, updating, toggling, and deleting price alerts.
All endpoints require JWT authentication and strictly enforce user data isolation.
Alert threshold evaluation is performed on-demand during requests.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.alert import (
    AlertCreate,
    AlertResponse,
    AlertSummaryResponse,
    AlertUpdate,
)
from app.services import alert_service as svc

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=list[AlertResponse],
    summary="List user's price alerts",
)
async def list_alerts(
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status: active, triggered, disabled"),
    enrich: bool = Query(default=True, description="Evaluate alerts on-demand against live market prices"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AlertResponse]:
    """Retrieve all price alerts created by the authenticated user with on-demand status evaluation."""
    return await svc.list_alerts(
        db=db,
        user=current_user,
        status_filter=status_filter,
        enrich_market_data=enrich,
    )


@router.get(
    "/summary",
    response_model=AlertSummaryResponse,
    summary="Get user alert counts summary",
)
async def get_alert_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertSummaryResponse:
    """Retrieve summary counts of alerts (total, active, triggered, disabled)."""
    counts = await svc.get_alert_summary(db=db, user=current_user)
    return AlertSummaryResponse(**counts)


@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new price alert",
)
async def create_alert(
    body: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Create a new price threshold alert."""
    try:
        return await svc.create_alert(
            db=db,
            user=current_user,
            symbol=body.symbol,
            target_price=body.target_price,
            condition=body.condition.value,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert details",
)
async def get_alert(
    alert_id: uuid.UUID,
    enrich: bool = Query(default=True, description="Evaluate alert on-demand against live market price"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Retrieve details for a single price alert."""
    try:
        return await svc.get_alert(
            db=db,
            user=current_user,
            alert_id=alert_id,
            enrich_market_data=enrich,
        )
    except svc.AlertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Update alert settings",
)
async def update_alert(
    alert_id: uuid.UUID,
    body: AlertUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Update price threshold, condition, status, or notes for an alert."""
    try:
        return await svc.update_alert(
            db=db,
            user=current_user,
            alert_id=alert_id,
            target_price=body.target_price,
            condition=body.condition.value if body.condition else None,
            status=body.status.value if body.status else None,
            notes=body.notes,
        )
    except svc.AlertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post(
    "/{alert_id}/toggle",
    response_model=AlertResponse,
    summary="Toggle alert active/disabled state",
)
async def toggle_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Toggle an alert between active and disabled states."""
    try:
        return await svc.toggle_alert_status(
            db=db,
            user=current_user,
            alert_id=alert_id,
        )
    except svc.AlertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert",
)
async def delete_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a price alert permanently."""
    try:
        await svc.delete_alert(db=db, user=current_user, alert_id=alert_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except svc.AlertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
