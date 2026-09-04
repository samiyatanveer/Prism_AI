"""Auth request and response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserResponse


# ── Requests ─────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Responses ─────────────────────────────────────────────────────────────────

class TokenPair(BaseModel):
    """Returned on login and register. Refresh token is opaque and one-time-use."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class AccessTokenResponse(BaseModel):
    """Returned when exchanging a refresh token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    """Combined token pair + user details, returned on login/register."""

    model_config = ConfigDict(from_attributes=True)

    tokens: TokenPair
    user: UserResponse
