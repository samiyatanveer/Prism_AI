"""
Alert Pydantic schemas for request validation and API responses.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AlertConditionEnum(str, Enum):
    ABOVE = "above"
    BELOW = "below"


class AlertStatusEnum(str, Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISABLED = "disabled"


class AlertCreate(BaseModel):
    """Payload to create a new price threshold alert."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Trading pair symbol (e.g. BTCUSDT, ETH, SOL)",
        examples=["BTCUSDT"],
    )
    target_price: Decimal = Field(
        ...,
        gt=0,
        description="Price threshold to trigger the alert (> 0)",
        examples=[Decimal("70000.00")],
    )
    condition: AlertConditionEnum = Field(
        default=AlertConditionEnum.ABOVE,
        description="Trigger when price moves above or below target",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional notes about why this alert was set",
    )


class AlertUpdate(BaseModel):
    """Payload to update an existing alert."""

    target_price: Decimal | None = Field(
        default=None,
        gt=0,
        description="New price threshold",
    )
    condition: AlertConditionEnum | None = Field(
        default=None,
        description="New trigger condition ('above' | 'below')",
    )
    status: AlertStatusEnum | None = Field(
        default=None,
        description="Set alert state ('active' | 'disabled')",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Updated notes",
    )


class AlertResponse(BaseModel):
    """Full detail of a price alert with on-demand evaluation metrics."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    target_price: Decimal
    condition: str
    status: str
    triggered_at: datetime | None = None
    triggered_price: Decimal | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    # Live evaluation metrics (None if market data unavailable)
    current_price: Decimal | None = None
    distance_usd: Decimal | None = None
    distance_pct: Decimal | None = None
    quote_asset: str | None = None


class AlertSummaryResponse(BaseModel):
    """Summary counts of alerts by status for dashboards and widgets."""

    total: int = 0
    active: int = 0
    triggered: int = 0
    disabled: int = 0
