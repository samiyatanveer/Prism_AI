"""Exchange request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class ConnectExchangeRequest(BaseModel):
    """Connect a new exchange account."""

    exchange_name: Literal["binance"] = Field(
        description="Exchange identifier. Only 'binance' is supported."
    )
    api_key: str = Field(min_length=8, max_length=256, description="Exchange API key")
    api_secret: str = Field(
        min_length=8, max_length=256, description="Exchange API secret"
    )
    display_label: str | None = Field(
        default=None,
        max_length=100,
        description="Optional user-friendly label for this connection.",
    )


# ── Responses ─────────────────────────────────────────────────────────────────

class ExchangeResponse(BaseModel):
    """
    Safe representation of a connected exchange.
    Never includes API key, secret, or encrypted blobs.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    exchange_name: str
    display_label: str | None
    permissions: str | None
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime


class ExchangeStatusResponse(BaseModel):
    """Connection status for a single exchange."""

    id: str
    exchange_name: str
    is_active: bool
    last_synced_at: datetime | None
    credential_valid: bool | None = Field(
        default=None,
        description="None if not yet validated; True/False after a live check.",
    )
    message: str | None = None


class ConnectExchangeResponse(BaseModel):
    """Returned after a successful exchange connection."""

    exchange: ExchangeResponse
    message: str = "Exchange connected successfully."
