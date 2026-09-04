"""Portfolio response schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class AssetHoldingResponse(BaseModel):
    """Single asset balance from an exchange account."""

    asset: str
    free: Decimal
    locked: Decimal
    total: Decimal
    estimated_usd_value: Decimal | None = Field(
        default=None,
        description=(
            "Estimated USD value derived from live USDT ticker price. "
            "Null when no USDT market exists for this asset or valuation "
            "was not available. Never fabricated."
        ),
    )


class PortfolioResponse(BaseModel):
    """Summary of portfolio holdings from the active exchange."""

    exchange_name: str
    exchange_id: str
    assets: list[AssetHoldingResponse]
    total_estimated_usd_value: Decimal | None = Field(
        default=None,
        description="Sum of all asset USD estimates. Null if any asset had no price.",
    )
