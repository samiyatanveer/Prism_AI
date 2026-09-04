"""
Analyses API routes.

Provides endpoints for generating, listing, viewing, and deleting structured AI analysis reports.
All endpoints require JWT authentication and strictly enforce user data isolation.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisGenerateRequest,
    AnalysisResponse,
    AnalysisSummaryResponse,
)
from app.services import analysis_service as svc

router = APIRouter(prefix="/analyses", tags=["Analyses"])


@router.get(
    "",
    response_model=list[AnalysisResponse],
    summary="List saved AI analysis reports",
)
async def list_analyses(
    symbol: str | None = Query(default=None, description="Filter by asset symbol (e.g. BTCUSDT)"),
    assessment: str | None = Query(default=None, description="Filter by assessment category: Buy Gradually, Hold, Consider Selling, Insufficient Context"),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnalysisResponse]:
    """Retrieve saved AI analysis reports for the authenticated user."""
    return await svc.list_analyses(
        db=db,
        user=current_user,
        symbol_filter=symbol,
        assessment_filter=assessment,
        limit=limit,
    )


@router.get(
    "/summary",
    response_model=AnalysisSummaryResponse,
    summary="Get saved analysis reports summary count",
)
async def get_analysis_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisSummaryResponse:
    """Retrieve counts of saved analysis reports by assessment category."""
    counts = await svc.get_analysis_summary(db=db, user=current_user)
    return AnalysisSummaryResponse(**counts)


@router.post(
    "/generate",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and save a new AI technical analysis report",
)
async def generate_analysis(
    body: AnalysisGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """
    Run full AI trading intelligence pipeline on an asset:
    fetches live market quotes + candles, computes deterministic technical indicators,
    and uses Groq to generate a standardized decision-support report.
    """
    try:
        return await svc.generate_and_save_analysis(
            db=db,
            user=current_user,
            symbol=body.symbol,
            timeframe=body.timeframe,
            user_notes=body.user_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a structured analysis report",
)
async def create_analysis(
    body: AnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Persist an analysis report directly."""
    try:
        return await svc.create_analysis(
            db=db,
            user=current_user,
            symbol=body.symbol,
            assessment=body.assessment.value,
            risk_level=body.risk_level.value,
            market_price=body.market_price,
            timeframe=body.timeframe,
            summary=body.summary,
            reasoning=body.reasoning,
            key_price_levels=body.key_price_levels,
            technical_indicators=body.technical_indicators,
            user_notes=body.user_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get single analysis report detail",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Retrieve full details for a saved analysis report."""
    try:
        return await svc.get_analysis(
            db=db,
            user=current_user,
            analysis_id=analysis_id,
        )
    except svc.AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an analysis report",
)
async def delete_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a saved analysis report."""
    try:
        await svc.delete_analysis(db=db, user=current_user, analysis_id=analysis_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except svc.AnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
