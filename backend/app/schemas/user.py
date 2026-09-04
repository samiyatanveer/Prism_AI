"""
User-facing Pydantic schemas.

Passwords and credential fields are NEVER included in response schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserResponse(UserBase):
    """Safe user representation returned to the client. No sensitive fields."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
