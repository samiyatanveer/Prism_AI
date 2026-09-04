"""
Security utilities — password hashing, JWT operations, and
exchange-credential encryption.

Credentials (passwords, tokens, API keys) are NEVER logged or returned
in API responses. Encryption key is loaded from settings only.
"""

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# ── Password hashing ─────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*. Never store or log the input."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ── JWT tokens ───────────────────────────────────────────────────────────────

def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    """
    Create a short-lived JWT access token.

    :param subject: Usually the user's UUID (str).
    :param extra_claims: Optional additional claims (e.g. role).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    :raises JWTError: if the token is invalid or expired.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


# ── Refresh tokens ───────────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """
    Generate a cryptographically random opaque refresh token.
    The plaintext is returned once to be sent to the client;
    only the hash is stored in the database.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Return a SHA-256 hex digest of the refresh token for DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Exchange credential encryption (AES-256-GCM) ────────────────────────────

def _get_aes_key() -> bytes:
    """Decode the base64-encoded 32-byte AES key from settings."""
    try:
        key = base64.b64decode(settings.encryption_key, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("ENCRYPTION_KEY must be valid base64-encoded data.") from exc
    if len(key) != 32:
        raise ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes.")
    return key


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt *plaintext* with AES-256-GCM authenticated encryption.

    Storage format (base64-encoded):
      [ 12-byte nonce ][ ciphertext ][ 16-byte GCM authentication tag ]

    The GCM authentication tag is appended to the ciphertext automatically
    by ``AESGCM.encrypt()``. Any tampering with the stored blob will cause
    ``AESGCM.decrypt()`` to raise an ``InvalidTag`` exception before any
    plaintext is returned.

    - Nonce: 12 bytes, generated with ``os.urandom`` per encryption call
    - Key:   32 bytes (AES-256), loaded from ``settings.encryption_key``
    - Tag:   16 bytes, implicit in AESGCM output

    Decrypt only when required by the backend integration layer.
    Never return the encrypted blob or plaintext to the frontend.
    Never log the plaintext, the key, or the raw bytes.
    """
    key = _get_aes_key()
    nonce = os.urandom(12)  # Unique per encryption — never reuse with the same key
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)  # ct includes GCM tag
    return base64.b64encode(nonce + ct).decode()


def decrypt_credential(ciphertext_b64: str) -> str:
    """
    Decrypt a value previously encrypted with :func:`encrypt_credential`.

    :raises Exception: if decryption fails (tampered data or wrong key).
    """
    key = _get_aes_key()
    raw = base64.b64decode(ciphertext_b64)
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()
