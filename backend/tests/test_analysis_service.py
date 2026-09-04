"""
Tests: Analysis service — deterministic indicator computation, assessment validation, report lifecycle, and user isolation.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.analysis import Analysis, AssessmentCategory, RiskLevel
from app.models.user import User
from app.schemas.market import CandleResponse, TickerResponse
from app.services import analysis_service as svc


def make_user(email="testuser@example.com"):
    return User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hashed_test_password",
        role="user",
        is_active=True,
    )


class TestDeterministicIndicatorComputation:
    def test_compute_indicators_with_full_candles(self, sample_ticker):
        candles = [
            CandleResponse(
                open_time=datetime(2026, 8, 1 + i, 0, 0, tzinfo=timezone.utc),
                open=Decimal(str(60000 + i * 100)),
                high=Decimal(str(60500 + i * 100)),
                low=Decimal(str(59500 + i * 100)),
                close=Decimal(str(60200 + i * 100)),
                volume=Decimal("1250.50"),
            )
            for i in range(30)
        ]

        indicators = svc._compute_technical_indicators(sample_ticker, candles)

        assert indicators["current_price"] == float(sample_ticker.price)
        assert indicators["change_24h_pct"] == float(sample_ticker.change_24h_pct)
        assert "sma_7" in indicators
        assert "sma_25" in indicators
        assert "rsi_14" in indicators
        assert indicators["trend"] in ("Strong Bullish", "Bullish", "Consolidating / Neutral", "Bearish", "Strong Bearish")
        assert indicators["recent_range_high"] is not None
        assert indicators["recent_range_low"] is not None

    def test_compute_indicators_empty_candles(self, sample_ticker):
        indicators = svc._compute_technical_indicators(sample_ticker, [])
        assert indicators["current_price"] == float(sample_ticker.price)
        assert indicators["trend"] == "Neutral"
        assert "sma_7" not in indicators
        assert "rsi_14" not in indicators


class TestAnalysisServiceCRUD:
    @pytest.mark.asyncio
    async def test_create_analysis_validates_assessment(self):
        user = make_user()
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Invalid assessment category"):
            await svc.create_analysis(
                db=mock_db,
                user=user,
                symbol="BTCUSDT",
                assessment="INVALID_ASSESSMENT",
                risk_level="Moderate",
                market_price=Decimal("65000.00"),
                summary="Test summary",
                reasoning="Test reasoning",
            )

    @pytest.mark.asyncio
    async def test_create_analysis_validates_risk_level(self):
        user = make_user()
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Invalid risk level"):
            await svc.create_analysis(
                db=mock_db,
                user=user,
                symbol="BTCUSDT",
                assessment=AssessmentCategory.BUY_GRADUALLY.value,
                risk_level="Extreme",
                market_price=Decimal("65000.00"),
                summary="Test summary",
                reasoning="Test reasoning",
            )

    @pytest.mark.asyncio
    async def test_create_analysis_validates_positive_market_price(self):
        user = make_user()
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Market price must be greater than 0"):
            await svc.create_analysis(
                db=mock_db,
                user=user,
                symbol="BTCUSDT",
                assessment=AssessmentCategory.HOLD.value,
                risk_level="Low",
                market_price=Decimal("-5.00"),
                summary="Test summary",
                reasoning="Test reasoning",
            )

    @pytest.mark.asyncio
    async def test_get_analysis_user_isolation(self):
        user = make_user()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(svc.AnalysisNotFoundError):
            await svc.get_analysis(mock_db, user, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_delete_analysis_user_isolation(self):
        user = make_user()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(svc.AnalysisNotFoundError):
            await svc.delete_analysis(mock_db, user, uuid.uuid4())


class TestGenerateAnalysisPipeline:
    @pytest.mark.asyncio
    async def test_generate_and_save_analysis_end_to_end(self, sample_ticker):
        user = make_user()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("app.services.market_service.get_ticker", new_callable=AsyncMock) as mock_tick, \
             patch("app.services.market_service.get_candles", new_callable=AsyncMock) as mock_cndl, \
             patch("app.services.analysis_service._invoke_reasoning_engine", new_callable=AsyncMock) as mock_ai:

            mock_tick.return_value = sample_ticker
            mock_cndl.return_value = []
            mock_ai.return_value = {
                "assessment": "Buy Gradually",
                "risk_level": "Moderate",
                "summary": "BTC shows healthy consolidation above key moving averages.",
                "reasoning": "RSI is in neutral range and 24h volume shows steady accumulation.",
                "key_price_levels": {
                    "support": 65000.0,
                    "resistance": 70000.0,
                    "target": 74000.0,
                    "stop_loss": 62500.0,
                },
            }

            result = await svc.generate_and_save_analysis(
                db=mock_db,
                user=user,
                symbol="BTCUSDT",
                timeframe="1D",
                user_notes="Planning to DCA",
            )

            assert result.symbol == "BTCUSDT"
            assert result.assessment == "Buy Gradually"
            assert result.risk_level == "Moderate"
            assert result.market_price == sample_ticker.price
            assert result.user_notes == "Planning to DCA"
            assert mock_db.add.called
            assert mock_db.commit.called
