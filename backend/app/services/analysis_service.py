"""
Analysis service layer — structured AI trading intelligence reports and technical analysis.

Rules:
- Strictly user-isolated on all queries and mutations.
- Technical indicators computed deterministically from authoritative market data.
- AI assessments strictly categorized as:
  'Buy Gradually' | 'Hold' | 'Consider Selling' | 'Insufficient Context'
- Risk levels: 'Low' | 'Moderate' | 'High'.
- Factual data strictly separated from LLM reasoning.
- No credentials or sensitive tokens ever passed to the LLM.
"""

import json
import re
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.models.analysis import Analysis, AssessmentCategory, RiskLevel
from app.models.user import User
from app.services import market_service
from app.services.watchlist_service import normalize_market_symbol

logger = get_logger(__name__)


# ── Exceptions ───────────────────────────────────────────────────────────────

class AnalysisError(Exception):
    """Base exception for analysis operations."""


class AnalysisNotFoundError(AnalysisError):
    """Analysis report not found or does not belong to user."""


# ── Deterministic Technical Indicator Calculation ───────────────────────────

def _compute_technical_indicators(
    ticker: Any,
    candles: list[Any],
) -> dict[str, Any]:
    """
    Deterministically compute technical indicators and price statistics
    from authoritative market ticker and OHLCV candlestick data.
    """
    indicators: dict[str, Any] = {
        "current_price": float(ticker.price) if ticker else None,
        "change_24h_pct": float(ticker.change_24h_pct) if ticker else 0.0,
        "high_24h": float(ticker.high_24h) if ticker else None,
        "low_24h": float(ticker.low_24h) if ticker else None,
        "volume_24h": float(ticker.volume_24h) if ticker else None,
        "trend": "Neutral",
    }

    if not candles:
        return indicators

    closes = [float(c.close) for c in candles]
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]

    # Moving averages
    if len(closes) >= 7:
        indicators["sma_7"] = round(sum(closes[-7:]) / 7, 4)
    if len(closes) >= 25:
        indicators["sma_25"] = round(sum(closes[-25:]) / 25, 4)

    # Simple RSI (14-period)
    if len(closes) >= 15:
        gains = []
        losses = []
        for i in range(1, 15):
            diff = closes[-15 + i] - closes[-15 + i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(diff))

        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        indicators["rsi_14"] = round(rsi, 2)

    # Trend calculation from Moving Averages & Price Action
    curr_p = float(ticker.price) if ticker else closes[-1]
    if "sma_7" in indicators and "sma_25" in indicators:
        if curr_p > indicators["sma_7"] > indicators["sma_25"]:
            indicators["trend"] = "Strong Bullish"
        elif curr_p > indicators["sma_7"]:
            indicators["trend"] = "Bullish"
        elif curr_p < indicators["sma_7"] < indicators["sma_25"]:
            indicators["trend"] = "Strong Bearish"
        elif curr_p < indicators["sma_7"]:
            indicators["trend"] = "Bearish"
        else:
            indicators["trend"] = "Consolidating / Neutral"
    elif "sma_7" in indicators:
        indicators["trend"] = "Bullish" if curr_p >= indicators["sma_7"] else "Bearish"

    # Candle range
    indicators["recent_range_high"] = round(max(highs[-14:]), 4) if highs else None
    indicators["recent_range_low"] = round(min(lows[-14:]), 4) if lows else None

    return indicators


# ── AI Reasoning Engine ───────────────────────────────────────────────────────

async def _invoke_reasoning_engine(
    symbol: str,
    timeframe: str,
    market_data: dict[str, Any],
    user_notes: str | None = None,
) -> dict[str, Any]:
    """
    Invoke Groq LLM with structured prompt to generate standardized assessment,
    risk level, key price levels, summary, and analytical reasoning.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        # Fallback if no LLM key configured
        return _build_fallback_assessment(symbol, market_data, "AI key not configured.")

    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.1,
            timeout=settings.groq_timeout,
        )

        prompt = f"""You are the PrismAI Technical Analysis & Decision Support Engine.
Analyze the following crypto market data and produce a structured intelligence report.

Asset: {symbol}
Timeframe: {timeframe}
Market Data:
{json.dumps(market_data, indent=2)}
User Context / Notes: {user_notes or "None provided"}

Requirements:
1. "assessment" MUST BE EXACTLY ONE OF:
   - "Buy Gradually"
   - "Hold"
   - "Consider Selling"
   - "Insufficient Context"
2. "risk_level" MUST BE EXACTLY ONE OF:
   - "Low"
   - "Moderate"
   - "High"
3. "key_price_levels" must contain estimated numeric levels:
   - "support"
   - "resistance"
   - "target"
   - "stop_loss"
4. "summary": A concise 2-sentence executive summary.
5. "reasoning": Detailed technical breakdown explaining trend, momentum, support/resistance, and risk factors.

Respond ONLY with a valid JSON object matching this schema:
{{
  "assessment": "Buy Gradually | Hold | Consider Selling | Insufficient Context",
  "risk_level": "Low | Moderate | High",
  "summary": "string",
  "reasoning": "string",
  "key_price_levels": {{
    "support": float,
    "resistance": float,
    "target": float,
    "stop_loss": float
  }}
}}"""

        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        # Extract JSON from response
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
        else:
            parsed = json.loads(content)

        # Validate standard assessment
        valid_assessments = [e.value for e in AssessmentCategory]
        assessment = parsed.get("assessment", "Hold")
        if assessment not in valid_assessments:
            # Fuzzy match or fallback
            if "buy" in assessment.lower():
                assessment = AssessmentCategory.BUY_GRADUALLY.value
            elif "sell" in assessment.lower():
                assessment = AssessmentCategory.CONSIDER_SELLING.value
            elif "context" in assessment.lower() or "insufficient" in assessment.lower():
                assessment = AssessmentCategory.INSUFFICIENT_CONTEXT.value
            else:
                assessment = AssessmentCategory.HOLD.value

        valid_risks = [e.value for e in RiskLevel]
        risk_level = parsed.get("risk_level", "Moderate")
        if risk_level not in valid_risks:
            risk_level = RiskLevel.MODERATE.value

        return {
            "assessment": assessment,
            "risk_level": risk_level,
            "summary": parsed.get("summary", f"Analysis completed for {symbol} on {timeframe} timeframe."),
            "reasoning": parsed.get("reasoning", "Technical evaluation based on current market indicators."),
            "key_price_levels": parsed.get("key_price_levels", {}),
        }

    except Exception as exc:
        logger.warning("AI analysis generation error, building deterministic fallback", extra={"error": str(exc)})
        return _build_fallback_assessment(symbol, market_data, str(exc))


def _build_fallback_assessment(
    symbol: str,
    market_data: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    """Rule-based fallback if LLM call fails."""
    curr_p = market_data.get("current_price") or 0.0
    chg = market_data.get("change_24h_pct") or 0.0
    rsi = market_data.get("rsi_14")

    if curr_p == 0.0:
        assessment = AssessmentCategory.INSUFFICIENT_CONTEXT.value
        risk = RiskLevel.HIGH.value
        summary = f"Insufficient market data available for {symbol}."
        reasoning = f"Could not retrieve authoritative market quotes: {reason}"
    elif rsi and rsi > 75:
        assessment = AssessmentCategory.CONSIDER_SELLING.value
        risk = RiskLevel.HIGH.value
        summary = f"{symbol} is in overbought territory with RSI at {rsi}."
        reasoning = f"24-hour change is {chg:+.2f}%. Overbought momentum suggests potential consolidation or pullback."
    elif rsi and rsi < 30:
        assessment = AssessmentCategory.BUY_GRADUALLY.value
        risk = RiskLevel.MODERATE.value
        summary = f"{symbol} is showing oversold conditions with RSI at {rsi}."
        reasoning = f"Price is testing lower bounds with potential for mean reversion."
    elif chg > 5.0:
        assessment = AssessmentCategory.BUY_GRADUALLY.value
        risk = RiskLevel.MODERATE.value
        summary = f"{symbol} displays positive short-term momentum (+{chg:.2f}% 24h)."
        reasoning = "Upward price action supported by 24-hour volume metrics."
    elif chg < -5.0:
        assessment = AssessmentCategory.CONSIDER_SELLING.value
        risk = RiskLevel.HIGH.value
        summary = f"{symbol} is experiencing downside pressure ({chg:.2f}% 24h)."
        reasoning = "Short-term momentum has weakened."
    else:
        assessment = AssessmentCategory.HOLD.value
        risk = RiskLevel.MODERATE.value
        summary = f"{symbol} is consolidating with moderate volatility ({chg:+.2f}% 24h)."
        reasoning = "Neutral market structure. Recommend holding current allocation while waiting for clear breakout signals."

    support = round(curr_p * 0.95, 4) if curr_p else None
    resistance = round(curr_p * 1.05, 4) if curr_p else None
    target = round(curr_p * 1.10, 4) if curr_p else None
    stop_loss = round(curr_p * 0.92, 4) if curr_p else None

    return {
        "assessment": assessment,
        "risk_level": risk,
        "summary": summary,
        "reasoning": reasoning,
        "key_price_levels": {
            "support": support,
            "resistance": resistance,
            "target": target,
            "stop_loss": stop_loss,
        },
    }


# ── Core Service Operations ───────────────────────────────────────────────────

async def list_analyses(
    db: AsyncSession,
    user: User,
    symbol_filter: str | None = None,
    assessment_filter: str | None = None,
    limit: int = 50,
) -> list[Analysis]:
    """
    List saved analysis reports for *user*, ordered by created_at DESC.
    Strictly user-isolated.
    """
    query = select(Analysis).where(Analysis.user_id == user.id)

    if symbol_filter:
        query = query.where(Analysis.symbol == symbol_filter.strip().upper())
    if assessment_filter:
        query = query.where(Analysis.assessment == assessment_filter.strip())

    query = query.order_by(Analysis.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_analysis(
    db: AsyncSession,
    user: User,
    analysis_id: uuid.UUID,
) -> Analysis:
    """
    Retrieve single analysis report with user isolation.

    :raises AnalysisNotFoundError: if report not found or not owned by user.
    """
    stmt = select(Analysis).where(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id,
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise AnalysisNotFoundError("Analysis report not found.")
    return analysis


async def create_analysis(
    db: AsyncSession,
    user: User,
    symbol: str,
    assessment: str,
    risk_level: str,
    market_price: Decimal,
    summary: str,
    reasoning: str,
    timeframe: str = "1D",
    key_price_levels: dict[str, Any] | None = None,
    technical_indicators: dict[str, Any] | None = None,
    user_notes: str | None = None,
) -> Analysis:
    """
    Persist an analysis report directly.
    """
    cleaned_symbol = symbol.strip().upper()
    if not cleaned_symbol:
        raise ValueError("Symbol cannot be empty.")
    if market_price <= Decimal("0"):
        raise ValueError("Market price must be greater than 0.")

    valid_assessments = [e.value for e in AssessmentCategory]
    if assessment not in valid_assessments:
        raise ValueError(f"Invalid assessment category. Must be one of: {valid_assessments}")

    valid_risks = [e.value for e in RiskLevel]
    if risk_level not in valid_risks:
        raise ValueError(f"Invalid risk level. Must be one of: {valid_risks}")

    analysis = Analysis(
        user_id=user.id,
        symbol=cleaned_symbol,
        assessment=assessment,
        risk_level=risk_level,
        market_price=market_price,
        timeframe=timeframe.strip().upper(),
        summary=summary.strip(),
        reasoning=reasoning.strip(),
        key_price_levels=key_price_levels,
        technical_indicators=technical_indicators,
        user_notes=user_notes.strip() if user_notes else None,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def generate_and_save_analysis(
    db: AsyncSession,
    user: User,
    symbol: str,
    timeframe: str = "1D",
    user_notes: str | None = None,
) -> Analysis:
    """
    End-to-end AI intelligence analysis pipeline:
    1. Retrieves authoritative market ticker and candles via market_service.
    2. Calculates deterministic technical indicators.
    3. Invokes Groq reasoning engine for structured assessment and key price levels.
    4. Persists and returns the report.
    """
    cleaned_sym = symbol.strip().upper()
    m_sym = normalize_market_symbol(cleaned_sym)

    # 1. Fetch live market data
    ticker = None
    candles = []
    try:
        ticker = await market_service.get_ticker(db, user, m_sym)
    except Exception as exc:
        logger.debug("Ticker retrieval failed for analysis", extra={"symbol": m_sym, "error": str(exc)})

    # Map timeframe interval for Binance (e.g. 1D -> 1d, 4H -> 4h, 1H -> 1h)
    interval_map = {"1D": "1d", "4H": "4h", "1H": "1h", "15M": "15m", "1W": "1w"}
    interval = interval_map.get(timeframe.upper(), "1d")

    try:
        candles = await market_service.get_candles(db, user, m_sym, interval=interval, limit=30)
    except Exception as exc:
        logger.debug("Candles retrieval failed for analysis", extra={"symbol": m_sym, "error": str(exc)})

    # 2. Deterministic calculations
    indicators = _compute_technical_indicators(ticker, candles)
    market_price = ticker.price if ticker else Decimal("0.00")

    # If no ticker and no candles, market price is 0 -> fallback to insufficient context
    if market_price == Decimal("0.00") and candles:
        market_price = Decimal(str(candles[-1].close))

    # 3. AI Reasoning
    ai_result = await _invoke_reasoning_engine(
        symbol=cleaned_sym,
        timeframe=timeframe,
        market_data=indicators,
        user_notes=user_notes,
    )

    # 4. Save and return
    # Ensure market_price is at least a valid positive Decimal for persistence
    if market_price <= Decimal("0"):
        market_price = Decimal("1.00")  # nominal placeholder for zero-price context failure

    return await create_analysis(
        db=db,
        user=user,
        symbol=cleaned_sym,
        assessment=ai_result["assessment"],
        risk_level=ai_result["risk_level"],
        market_price=market_price,
        timeframe=timeframe,
        summary=ai_result["summary"],
        reasoning=ai_result["reasoning"],
        key_price_levels=ai_result.get("key_price_levels"),
        technical_indicators=indicators,
        user_notes=user_notes,
    )


async def delete_analysis(
    db: AsyncSession,
    user: User,
    analysis_id: uuid.UUID,
) -> bool:
    """
    Delete an analysis report.

    :raises AnalysisNotFoundError: if report does not exist or belong to user.
    """
    stmt = select(Analysis).where(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id,
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise AnalysisNotFoundError("Analysis report not found.")

    await db.delete(analysis)
    await db.commit()
    return True


async def get_analysis_summary(
    db: AsyncSession,
    user: User,
) -> dict[str, int]:
    """
    Return counts of user analysis reports by assessment category.
    """
    stmt = (
        select(Analysis.assessment, func.count(Analysis.id))
        .where(Analysis.user_id == user.id)
        .group_by(Analysis.assessment)
    )
    result = await db.execute(stmt)
    rows = result.all()

    counts = {
        "total": 0,
        "buy_gradually": 0,
        "hold": 0,
        "consider_selling": 0,
        "insufficient_context": 0,
    }

    mapping = {
        AssessmentCategory.BUY_GRADUALLY.value: "buy_gradually",
        AssessmentCategory.HOLD.value: "hold",
        AssessmentCategory.CONSIDER_SELLING.value: "consider_selling",
        AssessmentCategory.INSUFFICIENT_CONTEXT.value: "insufficient_context",
    }

    for assess_val, count in rows:
        key = mapping.get(assess_val)
        if key:
            counts[key] = count
        counts["total"] += count

    return counts
