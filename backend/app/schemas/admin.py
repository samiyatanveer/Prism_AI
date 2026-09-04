"""Admin-only user management schemas without credential-bearing fields."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
