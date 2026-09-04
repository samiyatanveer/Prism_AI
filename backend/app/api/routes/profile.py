"""Profile preferences and security-session management."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_refresh_token
from app.database import get_db
from app.dependencies import get_current_user
from app.models.audit_log import AuditLog
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate, SessionResponse

router = APIRouter(prefix="/profile", tags=["Profile & Security"])
_REFRESH_COOKIE = "refresh_token"


def _profile(user: User) -> ProfileResponse:
    return ProfileResponse.model_validate(user)


@router.get("", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)) -> ProfileResponse:
    return _profile(current_user)


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    values = body.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(current_user, field, value)
    if values:
        db.add(AuditLog(
            created_at=datetime.now(timezone.utc), user_id=current_user.id,
            action="profile.updated", resource_type="user", resource_id=str(current_user.id),
            details="fields=" + ",".join(sorted(values)),
        ))
        await db.commit()
        await db.refresh(current_user)
    return _profile(current_user)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_security_sessions(
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False,  # noqa: E712
        RefreshToken.expires_at > datetime.now(timezone.utc),
    ).order_by(RefreshToken.created_at.desc()))
    current_hash = hash_refresh_token(refresh_token) if refresh_token else None
    return [SessionResponse(id=item.id, created_at=item.created_at, expires_at=item.expires_at,
                            user_agent=item.user_agent, ip_address=item.ip_address,
                            is_current=item.token_hash == current_hash) for item in result.scalars().all()]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_security_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.id == session_id, RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False,  # noqa: E712
    ))
    token = result.scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    token.revoked = True
    db.add(AuditLog(created_at=datetime.now(timezone.utc), user_id=current_user.id,
                    action="security.session.revoked", resource_type="refresh_token",
                    resource_id=str(session_id)))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
