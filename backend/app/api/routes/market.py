"""Market data API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exchanges.base import ExchangeAPIError, ExchangeRateLimitError, ExchangeTimeoutError
from app.models.user import User
from app.schemas.market import CandleResponse, CandlesResponse, TickerResponse
from app.services import market_service as svc

router = APIRouter(prefix="/market", tags=["Market"])


def _map_exchange_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ExchangeRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Exchange rate limit reached. Please wait before retrying.",
        )
    if isinstance(exc, ExchangeTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Exchange did not respond in time. Please try again.",
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Exchange returned an error. Please try again later.",
    )


@router.get(
    "/{symbol}/ticker",
    response_model=TickerResponse,
    summary="Get 24-hour ticker for a symbol",
)
async def get_ticker(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TickerResponse:
    """Fetch 24-hour price statistics for the given trading pair symbol."""
    try:
        ticker = await svc.get_ticker(db, current_user, symbol)
    except svc.NoExchangeConnectedError as exc:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc))
    except ExchangeAPIError as exc:
        raise _map_exchange_error(exc)

    return TickerResponse(
        symbol=ticker.symbol,
        base_asset=ticker.base_asset,
        quote_asset=ticker.quote_asset,
        price=ticker.price,
        change_24h_pct=ticker.change_24h_pct,
        volume_24h=ticker.volume_24h,
        high_24h=ticker.high_24h,
        low_24h=ticker.low_24h,
        timestamp=ticker.timestamp,
    )


@router.get(
    "/{symbol}",
    response_model=TickerResponse,
    summary="Get market summary for a symbol",
)
async def get_market_summary(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TickerResponse:
    """Compatibility endpoint documented as ``GET /market/{symbol}``."""
    return await get_ticker(symbol=symbol, current_user=current_user, db=db)


@router.get(
    "/{symbol}/candles",
    response_model=CandlesResponse,
    summary="Get OHLCV candlestick data",
)
async def get_candles(
    symbol: str,
    interval: str = Query(default="1d", description="Candle interval, e.g. 1m, 1h, 1d"),
    limit: int = Query(default=90, ge=1, le=1000, description="Number of candles (1-1000)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandlesResponse:
    """Fetch OHLCV candlestick data for a trading pair."""
    try:
        candles = await svc.get_candles(db, current_user, symbol, interval, limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except svc.NoExchangeConnectedError as exc:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc))
    except ExchangeAPIError as exc:
        raise _map_exchange_error(exc)

    return CandlesResponse(
        symbol=symbol.upper(),
        interval=interval,
        candles=[
            CandleResponse(
                open_time=c.open_time,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in candles
        ],
    )


@router.get(
    "/{symbol}/chart",
    response_model=CandlesResponse,
    summary="Get historical chart data for a symbol",
)
async def get_chart(
    symbol: str,
    interval: str = Query(default="1d", description="Candle interval, e.g. 1m, 1h, 1d"),
    limit: int = Query(default=90, ge=1, le=1000, description="Number of candles (1-1000)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandlesResponse:
    """Compatibility endpoint documented as ``GET /market/{symbol}/chart``."""
    return await get_candles(
        symbol=symbol,
        interval=interval,
        limit=limit,
        current_user=current_user,
        db=db,
    )
