"""
Auth service — user registration, login, token lifecycle management,
and audit logging.

Passwords and tokens are NEVER passed to the logger. The audit log
records what happened without recording any secrets.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.audit_log import AuditLog
from app.models.token import RefreshToken
from app.models.user import User
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


# ── Registration ──────────────────────────────────────────────────────────────

async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str | None = None,
    ip_address: str | None = None,
) -> User:
    """
    Create a new user account.

    :raises ValueError: if the email is already registered.
    """
    # Check for duplicate email (case-insensitive)
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    if result.scalar_one_or_none() is not None:
        raise ValueError("An account with this email already exists.")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.flush()  # get the generated id without committing

    await _write_audit_log(
        db,
        action="user.registered",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )

    await db.commit()
    await db.refresh(user)

    logger.info("User registered", extra={"user_id": str(user.id)})
    return user


# ── Authentication ────────────────────────────────────────────────────────────

async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    ip_address: str | None = None,
) -> User:
    """
    Verify credentials and return the user.

    :raises ValueError: on invalid credentials or inactive account.
    """
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        # Log the failure without recording the password
        await _write_audit_log(
            db,
            action="user.login.failed",
            user_id=None,
            resource_type="user",
            resource_id=None,
            ip_address=ip_address,
            details=f"email={email.lower()[:50]}",  # truncated for safety
        )
        await db.commit()
        raise ValueError("Invalid credentials.")

    if not user.is_active:
        raise ValueError("Account is disabled. Contact support.")

    await _write_audit_log(
        db,
        action="user.login.success",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
    )
    await db.commit()

    logger.info("User authenticated", extra={"user_id": str(user.id)})
    return user


# ── Token management ──────────────────────────────────────────────────────────

async def create_tokens(
    db: AsyncSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """
    Issue a new access + refresh token pair for *user*.

    :returns: (access_token_plaintext, refresh_token_plaintext)
    Only the hash of the refresh token is stored in the database.
    """
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role},
    )

    refresh_token_plain = generate_refresh_token()
    token_hash = hash_refresh_token(refresh_token_plain)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )

    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(refresh_token_record)
    await db.commit()

    return access_token, refresh_token_plain


async def refresh_access_token(
    db: AsyncSession,
    refresh_token_plain: str,
) -> tuple[str, str]:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Implements token rotation: the old refresh token is revoked.

    :raises ValueError: if the token is invalid, expired, or revoked.
    :returns: (new_access_token, new_refresh_token_plain)
    """
    token_hash = hash_refresh_token(refresh_token_plain)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise ValueError("Invalid refresh token.")
    if record.revoked:
        raise ValueError("Refresh token has been revoked.")
    if record.expires_at < datetime.now(timezone.utc):
        raise ValueError("Refresh token has expired.")

    # Revoke the old token (rotation)
    record.revoked = True
    await db.flush()

    # Load the user
    user_result = await db.execute(select(User).where(User.id == record.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise ValueError("User not found or inactive.")

    new_access, new_refresh_plain = await create_tokens(
        db, user, ip_address=record.ip_address, user_agent=record.user_agent
    )

    logger.info(
        "Refresh token rotated", extra={"user_id": str(user.id)}
    )
    return new_access, new_refresh_plain


async def revoke_refresh_token(db: AsyncSession, refresh_token_plain: str) -> None:
    """Revoke a specific refresh token (logout)."""
    token_hash = hash_refresh_token(refresh_token_plain)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record:
        record.revoked = True
        await db.commit()


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _write_audit_log(
    db: AsyncSession,
    action: str,
    user_id: uuid.UUID | None,
    resource_type: str | None,
    resource_id: str | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: str | None = None,
) -> None:
    """Insert an audit log row. Never include secrets in any field."""
    log = AuditLog(
        created_at=datetime.now(timezone.utc),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )
    db.add(log)
