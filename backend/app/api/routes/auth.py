"""Authentication routes."""

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

_REFRESH_COOKIE = "refresh_token"
_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 86_400  # seconds


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set the refresh token as an httpOnly, SameSite=Lax cookie."""
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.is_production,  # Secure flag only in prod (HTTPS)
        samesite="lax",
        path="/auth",  # Scoped to auth endpoints only
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    try:
        user = await auth_service.register_user(
            db=db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    access_token, refresh_token = await auth_service.create_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(
        tokens=TokenPair(
            access_token=access_token,
            expires_in=settings.access_token_expire_minutes * 60,
        ),
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate and obtain tokens",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    try:
        user = await auth_service.authenticate_user(
            db=db,
            email=payload.email,
            password=payload.password,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )

    access_token, refresh_token = await auth_service.create_tokens(
        db=db,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(
        tokens=TokenPair(
            access_token=access_token,
            expires_in=settings.access_token_expire_minutes * 60,
        ),
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Exchange refresh token for new access token",
)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
) -> AccessTokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided.",
        )

    try:
        new_access, new_refresh = await auth_service.refresh_access_token(
            db=db, refresh_token_plain=refresh_token
        )
    except ValueError as exc:
        # Clear the stale cookie on failure
        response.delete_cookie(_REFRESH_COOKIE, path="/auth")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )

    _set_refresh_cookie(response, new_refresh)

    return AccessTokenResponse(
        access_token=new_access,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke refresh token and clear session",
)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
) -> None:
    if refresh_token:
        await auth_service.revoke_refresh_token(db=db, refresh_token_plain=refresh_token)
    response.delete_cookie(_REFRESH_COOKIE, path="/auth")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the current authenticated user",
)
async def get_me(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    current_user = await get_current_user(db=db, authorization=authorization)
    return UserResponse.model_validate(current_user)
