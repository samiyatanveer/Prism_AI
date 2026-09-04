"""Minimal role-protected administration APIs for users and support records."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.admin import AdminUserResponse, AdminUserUpdate
from app.schemas.complaint import ComplaintResponse
from app.services import complaint_service

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserResponse]:
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(limit))
    return [AdminUserResponse.model_validate(user) for user in result.scalars().all()]


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if body.is_active is not None:
        # Avoid a single administrator accidentally locking themselves out.
        if target.id == admin.id and body.is_active is False:
            raise HTTPException(status_code=422, detail="You cannot deactivate your own account.")
        target.is_active = body.is_active
        db.add(AuditLog(created_at=datetime.now(timezone.utc), user_id=admin.id,
                        action="admin.user.updated", resource_type="user",
                        resource_id=str(target.id), details=f"is_active={target.is_active}"))
        await db.commit()
        await db.refresh(target)
    return AdminUserResponse.model_validate(target)


@router.get("/complaints", response_model=list[ComplaintResponse])
async def list_all_complaints(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ComplaintResponse]:
    return await complaint_service.list_complaints(db=db, user=admin)
