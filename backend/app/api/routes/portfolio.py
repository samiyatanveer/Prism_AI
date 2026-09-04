"""Portfolio API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exchanges.base import ExchangeAPIError, ExchangeRateLimitError, ExchangeTimeoutError
from app.models.user import User
from app.schemas.portfolio import AssetHoldingResponse, PortfolioResponse
from app.services import portfolio_service as svc

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get(
    "",
    response_model=PortfolioResponse,
    summary="Get portfolio holdings with optional USD valuation",
)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    """
    Fetch live portfolio holdings from the user's active exchange.

    USD valuation is derived from live USDT ticker prices where available.
    Assets without a USDT market have estimated_usd_value=null.
    total_estimated_usd_value is null if any asset has no USD price.
    """
    try:
        data = await svc.get_portfolio(db, current_user, include_usd_valuation=True)
    except svc.NoExchangeConnectedError as exc:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc))
    except ExchangeRateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Exchange rate limit reached. Please wait before retrying.",
        )
    except ExchangeTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Exchange did not respond in time.",
        )
    except ExchangeAPIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Exchange returned an error. Please try again later.",
        )

    return PortfolioResponse(
        exchange_name=data["exchange_name"],
        exchange_id=data["exchange_id"],
        assets=[
            AssetHoldingResponse(
                asset=b.asset,
                free=b.free,
                locked=b.locked,
                total=b.free + b.locked,
                estimated_usd_value=b.estimated_usd_value,
            )
            for b in data["assets"]
        ],
        total_estimated_usd_value=data["total_estimated_usd_value"],
    )
