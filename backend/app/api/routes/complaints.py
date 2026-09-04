"""
Complaints and Support API routes.

Provides endpoints for submitting complaints/tickets, retrieving tickets,
adding thread replies, updating resolution status, and viewing support summaries.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintDetailResponse,
    ComplaintMessageCreate,
    ComplaintResponse,
    ComplaintStatusUpdate,
    ComplaintSummaryResponse,
)
from app.services import complaint_service as svc

router = APIRouter(prefix="/complaints", tags=["Complaints & Support"])


@router.get(
    "",
    response_model=list[ComplaintResponse],
    summary="List user's complaints or support tickets",
)
async def list_complaints(
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status: open, in_progress, resolved, closed"),
    category: str | None = Query(default=None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ComplaintResponse]:
    """Retrieve complaints submitted by the authenticated user (or all if admin)."""
    return await svc.list_complaints(
        db=db,
        user=current_user,
        status_filter=status_filter,
        category_filter=category,
    )


@router.get(
    "/summary",
    response_model=ComplaintSummaryResponse,
    summary="Get complaints status summary counts",
)
async def get_complaint_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComplaintSummaryResponse:
    """Retrieve counts of complaints by status (total, open, in_progress, resolved, closed)."""
    counts = await svc.get_complaint_summary(db=db, user=current_user)
    return ComplaintSummaryResponse(**counts)


@router.post(
    "",
    response_model=ComplaintDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new complaint or support ticket",
)
async def create_complaint(
    body: ComplaintCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComplaintDetailResponse:
    """Create a new support ticket / complaint."""
    try:
        return await svc.create_complaint(
            db=db,
            user=current_user,
            subject=body.subject,
            category=body.category.value,
            priority=body.priority.value,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get(
    "/{complaint_id}",
    response_model=ComplaintDetailResponse,
    summary="Get complaint details and conversation thread",
)
async def get_complaint(
    complaint_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComplaintDetailResponse:
    """Retrieve full complaint detail with all threaded messages."""
    try:
        return await svc.get_complaint(
            db=db,
            user=current_user,
            complaint_id=complaint_id,
        )
    except svc.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/{complaint_id}/messages",
    response_model=ComplaintDetailResponse,
    summary="Add a message reply to complaint thread",
)
async def add_complaint_message(
    complaint_id: uuid.UUID,
    body: ComplaintMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComplaintDetailResponse:
    """Post a reply message to an existing support ticket thread."""
    try:
        return await svc.add_complaint_message(
            db=db,
            user=current_user,
            complaint_id=complaint_id,
            message=body.message,
        )
    except svc.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.patch(
    "/{complaint_id}/status",
    response_model=ComplaintDetailResponse,
    summary="Update complaint status or resolution notes",
)
async def update_complaint_status(
    complaint_id: uuid.UUID,
    body: ComplaintStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComplaintDetailResponse:
    """Update status (e.g. resolve, close) or resolution notes for a complaint."""
    try:
        return await svc.update_complaint_status(
            db=db,
            user=current_user,
            complaint_id=complaint_id,
            status=body.status.value,
            resolution_notes=body.resolution_notes,
        )
    except svc.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
