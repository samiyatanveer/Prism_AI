"""
Analysis Pydantic schemas for request validation and API responses.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssessmentEnum(str, Enum):
    BUY_GRADUALLY = "Buy Gradually"
    HOLD = "Hold"
    CONSIDER_SELLING = "Consider Selling"
    INSUFFICIENT_CONTEXT = "Insufficient Context"


class RiskLevelEnum(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"


class AnalysisGenerateRequest(BaseModel):
    """Payload to trigger a new AI-generated technical analysis report for an asset."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Trading pair symbol (e.g. BTCUSDT, ETH, SOL)",
        examples=["BTCUSDT"],
    )
    timeframe: str = Field(
        default="1D",
        max_length=10,
        description="Analysis chart timeframe (e.g. 1D, 4H, 1H)",
        examples=["1D"],
    )
    user_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional user notes or trade context",
    )


class AnalysisCreate(BaseModel):
    """Manual analysis creation payload."""

    symbol: str = Field(..., min_length=1, max_length=20)
    assessment: AssessmentEnum
    risk_level: RiskLevelEnum = RiskLevelEnum.MODERATE
    market_price: Decimal = Field(..., gt=0)
    timeframe: str = Field(default="1D", max_length=10)
    summary: str = Field(..., min_length=1)
    reasoning: str = Field(..., min_length=1)
    key_price_levels: dict[str, Any] | None = None
    technical_indicators: dict[str, Any] | None = None
    user_notes: str | None = None


class AnalysisResponse(BaseModel):
    """Full detail of a structured AI intelligence and technical analysis report."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    assessment: str
    risk_level: str
    market_price: Decimal
    timeframe: str
    summary: str
    reasoning: str
    key_price_levels: dict[str, Any] | None = None
    technical_indicators: dict[str, Any] | None = None
    user_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisSummaryResponse(BaseModel):
    """Summary counts of saved analysis reports by assessment category."""

    total: int = 0
    buy_gradually: int = 0
    hold: int = 0
    consider_selling: int = 0
    insufficient_context: int = 0
