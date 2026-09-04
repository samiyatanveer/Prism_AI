"""
Tests: Alert API schemas, validation, security, and route handling.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.alert import (
    AlertConditionEnum,
    AlertCreate,
    AlertResponse,
    AlertStatusEnum,
    AlertSummaryResponse,
    AlertUpdate,
)


class TestAlertSchemas:
    def test_valid_alert_create(self):
        req = AlertCreate(
            symbol="BTCUSDT",
            target_price=Decimal("70000.00"),
            condition=AlertConditionEnum.ABOVE,
            notes="Watch for all-time high breakout",
        )
        assert req.symbol == "BTCUSDT"
        assert req.target_price == Decimal("70000.00")
        assert req.condition == AlertConditionEnum.ABOVE

    def test_alert_create_negative_price_raises(self):
        with pytest.raises(ValidationError):
            AlertCreate(
                symbol="BTCUSDT",
                target_price=Decimal("-10.00"),
                condition=AlertConditionEnum.ABOVE,
            )

    def test_alert_create_zero_price_raises(self):
        with pytest.raises(ValidationError):
            AlertCreate(
                symbol="BTCUSDT",
                target_price=Decimal("0.00"),
                condition=AlertConditionEnum.ABOVE,
            )

    def test_alert_create_empty_symbol_raises(self):
        with pytest.raises(ValidationError):
            AlertCreate(
                symbol="",
                target_price=Decimal("100.00"),
                condition=AlertConditionEnum.ABOVE,
            )

    def test_alert_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = AlertResponse(
            id=uuid.uuid4(),
            symbol="ETHUSDT",
            target_price=Decimal("3500.00"),
            condition="above",
            status="active",
            notes="Key resistance",
            created_at=now,
            updated_at=now,
            current_price=Decimal("3450.00"),
            distance_usd=Decimal("50.00"),
            distance_pct=Decimal("1.45"),
            quote_asset="USDT",
        )
        assert resp.symbol == "ETHUSDT"
        assert resp.current_price == Decimal("3450.00")
        assert resp.distance_usd == Decimal("50.00")

    def test_alert_summary_response_schema(self):
        summary = AlertSummaryResponse(total=5, active=3, triggered=1, disabled=1)
        assert summary.total == 5
        assert summary.active == 3
        assert summary.triggered == 1
        assert summary.disabled == 1


class TestAlertSchemaSecurity:
    def test_no_sensitive_credentials_in_alert_schemas(self):
        schemas = [
            AlertCreate,
            AlertUpdate,
            AlertResponse,
            AlertSummaryResponse,
        ]
        forbidden_fields = {"api_key", "api_secret", "encrypted_api_key", "encrypted_api_secret", "password", "hashed_password"}

        for schema in schemas:
            fields = set(schema.model_fields.keys())
            overlap = fields & forbidden_fields
            assert not overlap, f"Forbidden fields {overlap} found in {schema.__name__}"
