"""
Tests: Alert service — on-demand price evaluation, triggering logic, status lifecycle, and user isolation.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.alert import Alert, AlertCondition, AlertStatus
from app.models.user import User
from app.services import alert_service as svc
from app.services.market_service import NoExchangeConnectedError


def make_user(email="testuser@example.com"):
    return User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hashed_test_password",
        role="user",
        is_active=True,
    )


class TestAlertTriggerLogic:
    @pytest.mark.asyncio
    async def test_above_condition_triggers_when_price_exceeds_target(self, sample_ticker):
        user = make_user()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        # Alert: BTC above $65,000. Sample ticker price is $67,000.00
        alert = Alert(
            id=uuid.uuid4(),
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("65000.00"),
            condition=AlertCondition.ABOVE.value,
            status=AlertStatus.ACTIVE.value,
            triggered_at=None,
            triggered_price=None,
            notes="Breakout watch",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.market_service.get_tickers", return_value={"BTCUSDT": sample_ticker}) as mock_tickers:
            enriched = await svc._evaluate_and_enrich_alerts(mock_db, user, [alert])

            mock_tickers.assert_awaited_once_with(mock_db, user, ["BTCUSDT"])
            assert len(enriched) == 1
            assert enriched[0]["status"] == AlertStatus.TRIGGERED.value
            assert enriched[0]["triggered_price"] == Decimal("67000.00")
            assert enriched[0]["triggered_at"] is not None
            assert alert.status == AlertStatus.TRIGGERED.value
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_above_condition_triggers_on_exact_equality(self, sample_ticker):
        user = make_user()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        # Alert: BTC above $67,000.00. Sample ticker price is exact $67,000.00
        alert = Alert(
            id=uuid.uuid4(),
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("67000.00"),
            condition=AlertCondition.ABOVE.value,
            status=AlertStatus.ACTIVE.value,
            triggered_at=None,
            triggered_price=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.market_service.get_tickers", return_value={"BTCUSDT": sample_ticker}):
            enriched = await svc._evaluate_and_enrich_alerts(mock_db, user, [alert])
            assert enriched[0]["status"] == AlertStatus.TRIGGERED.value
            assert alert.status == AlertStatus.TRIGGERED.value

    @pytest.mark.asyncio
    async def test_above_condition_does_not_trigger_when_below_target(self, sample_ticker):
        user = make_user()
        mock_db = AsyncMock()

        # Alert: BTC above $70,000. Sample ticker is $67,000.00
        alert = Alert(
            id=uuid.uuid4(),
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("70000.00"),
            condition=AlertCondition.ABOVE.value,
            status=AlertStatus.ACTIVE.value,
            triggered_at=None,
            triggered_price=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.market_service.get_tickers", return_value={"BTCUSDT": sample_ticker}):
            enriched = await svc._evaluate_and_enrich_alerts(mock_db, user, [alert])
            assert enriched[0]["status"] == AlertStatus.ACTIVE.value
            assert alert.status == AlertStatus.ACTIVE.value
            assert enriched[0]["triggered_at"] is None
            assert enriched[0]["current_price"] == Decimal("67000.00")
            assert enriched[0]["distance_usd"] == Decimal("3000.00")

    @pytest.mark.asyncio
    async def test_below_condition_triggers_when_price_drops_below_target(self, sample_ticker):
        user = make_user()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        # Alert: BTC below $68,000. Sample ticker price is $67,000.00
        alert = Alert(
            id=uuid.uuid4(),
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("68000.00"),
            condition=AlertCondition.BELOW.value,
            status=AlertStatus.ACTIVE.value,
            triggered_at=None,
            triggered_price=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.market_service.get_tickers", return_value={"BTCUSDT": sample_ticker}):
            enriched = await svc._evaluate_and_enrich_alerts(mock_db, user, [alert])
            assert enriched[0]["status"] == AlertStatus.TRIGGERED.value
            assert alert.status == AlertStatus.TRIGGERED.value
            assert enriched[0]["triggered_price"] == Decimal("67000.00")

    @pytest.mark.asyncio
    async def test_disabled_alert_never_triggers(self, sample_ticker):
        user = make_user()
        mock_db = AsyncMock()

        # Alert is disabled, price exceeds target
        alert = Alert(
            id=uuid.uuid4(),
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("60000.00"),
            condition=AlertCondition.ABOVE.value,
            status=AlertStatus.DISABLED.value,
            triggered_at=None,
            triggered_price=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.market_service.get_tickers", return_value={"BTCUSDT": sample_ticker}):
            enriched = await svc._evaluate_and_enrich_alerts(mock_db, user, [alert])
            assert enriched[0]["status"] == AlertStatus.DISABLED.value
            assert alert.status == AlertStatus.DISABLED.value
            assert enriched[0]["triggered_at"] is None

    @pytest.mark.asyncio
    async def test_already_triggered_alert_remains_stable(self, sample_ticker):
        user = make_user()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        prev_time = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
        prev_price = Decimal("66000.00")

        alert = Alert(
            id=uuid.uuid4(),
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("65000.00"),
            condition=AlertCondition.ABOVE.value,
            status=AlertStatus.TRIGGERED.value,
            triggered_at=prev_time,
            triggered_price=prev_price,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.market_service.get_tickers", return_value={"BTCUSDT": sample_ticker}):
            enriched = await svc._evaluate_and_enrich_alerts(mock_db, user, [alert])
            assert enriched[0]["status"] == AlertStatus.TRIGGERED.value
            # Preserves original triggered timestamp and price
            assert enriched[0]["triggered_at"] == prev_time
            assert enriched[0]["triggered_price"] == prev_price
            # DB commit not called since status didn't change
            assert not mock_db.commit.called

    @pytest.mark.asyncio
    async def test_missing_market_data_fallback(self):
        user = make_user()
        mock_db = AsyncMock()

        alert = Alert(
            id=uuid.uuid4(),
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("70000.00"),
            condition=AlertCondition.ABOVE.value,
            status=AlertStatus.ACTIVE.value,
            triggered_at=None,
            triggered_price=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch(
            "app.services.market_service.get_tickers",
            side_effect=NoExchangeConnectedError("No exchange"),
        ):
            enriched = await svc._evaluate_and_enrich_alerts(mock_db, user, [alert])
            assert len(enriched) == 1
            assert enriched[0]["status"] == AlertStatus.ACTIVE.value
            assert enriched[0]["current_price"] is None
            assert enriched[0]["distance_usd"] is None


class TestAlertServiceCRUD:
    @pytest.mark.asyncio
    async def test_create_alert_validation(self):
        user = make_user()
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="greater than 0"):
            await svc.create_alert(mock_db, user, "BTCUSDT", Decimal("-10"))

        with pytest.raises(ValueError, match="greater than 0"):
            await svc.create_alert(mock_db, user, "BTCUSDT", Decimal("0"))

        with pytest.raises(ValueError, match="above.*below"):
            await svc.create_alert(mock_db, user, "BTCUSDT", Decimal("50000"), condition="invalid_cond")

    @pytest.mark.asyncio
    async def test_update_alert_resets_triggered_state(self):
        user = make_user()
        alert_id = uuid.uuid4()
        mock_db = AsyncMock()

        alert = Alert(
            id=alert_id,
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("65000.00"),
            condition="above",
            status=AlertStatus.TRIGGERED.value,
            triggered_at=datetime.now(timezone.utc),
            triggered_price=Decimal("66000.00"),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        mock_db.execute.return_value = mock_result

        with patch.object(svc, "get_alert", return_value={"id": alert_id, "status": "active"}):
            await svc.update_alert(mock_db, user, alert_id, target_price=Decimal("75000.00"))
            assert alert.target_price == Decimal("75000.00")
            assert alert.status == AlertStatus.ACTIVE.value
            assert alert.triggered_at is None
            assert alert.triggered_price is None

    @pytest.mark.asyncio
    async def test_toggle_alert_status(self):
        user = make_user()
        alert_id = uuid.uuid4()
        mock_db = AsyncMock()

        alert = Alert(
            id=alert_id,
            user_id=user.id,
            symbol="BTCUSDT",
            target_price=Decimal("65000.00"),
            condition="above",
            status=AlertStatus.ACTIVE.value,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        mock_db.execute.return_value = mock_result

        with patch.object(svc, "get_alert", return_value={"id": alert_id, "status": "disabled"}):
            await svc.toggle_alert_status(mock_db, user, alert_id)
            assert alert.status == AlertStatus.DISABLED.value

    @pytest.mark.asyncio
    async def test_delete_alert_user_isolation(self):
        user = make_user()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(svc.AlertNotFoundError):
            await svc.delete_alert(mock_db, user, uuid.uuid4())
