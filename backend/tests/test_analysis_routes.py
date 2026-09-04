"""
Tests: Analysis API schemas, route handling, input validation, and security invariants.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisGenerateRequest,
    AnalysisResponse,
    AnalysisSummaryResponse,
    AssessmentEnum,
    RiskLevelEnum,
)


class TestAnalysisSchemas:
    def test_valid_analysis_generate_request(self):
        req = AnalysisGenerateRequest(
            symbol="BTCUSDT",
            timeframe="1D",
            user_notes="Checking entry zone",
        )
        assert req.symbol == "BTCUSDT"
        assert req.timeframe == "1D"
        assert req.user_notes == "Checking entry zone"

    def test_analysis_generate_empty_symbol_raises(self):
        with pytest.raises(ValidationError):
            AnalysisGenerateRequest(symbol="")

    def test_valid_analysis_create(self):
        req = AnalysisCreate(
            symbol="ETHUSDT",
            assessment=AssessmentEnum.BUY_GRADUALLY,
            risk_level=RiskLevelEnum.LOW,
            market_price=Decimal("3400.50"),
            timeframe="4H",
            summary="Bullish divergence on 4H",
            reasoning="RSI bounced from oversold territory.",
            key_price_levels={"support": 3200.0, "resistance": 3600.0},
        )
        assert req.symbol == "ETHUSDT"
        assert req.assessment == AssessmentEnum.BUY_GRADUALLY
        assert req.market_price == Decimal("3400.50")

    def test_analysis_response_serialization(self):
        now = datetime.now(timezone.utc)
        resp = AnalysisResponse(
            id=uuid.uuid4(),
            symbol="SOLUSDT",
            assessment="Hold",
            risk_level="Moderate",
            market_price=Decimal("180.25"),
            timeframe="1D",
            summary="Range-bound trading",
            reasoning="Testing midpoint of Bollinger Bands.",
            key_price_levels={"support": 165.0, "resistance": 195.0},
            technical_indicators={"rsi_14": 52.3, "trend": "Neutral"},
            user_notes="Wait for breakout",
            created_at=now,
            updated_at=now,
        )
        assert resp.symbol == "SOLUSDT"
        assert resp.assessment == "Hold"
        assert resp.key_price_levels["support"] == 165.0

    def test_analysis_summary_response(self):
        summary = AnalysisSummaryResponse(
            total=10,
            buy_gradually=4,
            hold=3,
            consider_selling=2,
            insufficient_context=1,
        )
        assert summary.total == 10
        assert summary.buy_gradually == 4
        assert summary.hold == 3
        assert summary.consider_selling == 2
        assert summary.insufficient_context == 1


class TestAnalysisSchemaSecurity:
    def test_no_sensitive_credentials_in_analysis_schemas(self):
        schemas = [
            AnalysisGenerateRequest,
            AnalysisCreate,
            AnalysisResponse,
            AnalysisSummaryResponse,
        ]
        forbidden_fields = {"api_key", "api_secret", "encrypted_api_key", "encrypted_api_secret", "password", "hashed_password"}

        for schema in schemas:
            fields = set(schema.model_fields.keys())
            overlap = fields & forbidden_fields
            assert not overlap, f"Forbidden fields {overlap} found in {schema.__name__}"
