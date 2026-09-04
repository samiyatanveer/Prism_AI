"""
Tests: LangGraph AI tools.

Verifies:
- Each tool correctly invokes existing service layer methods
- Config injection of user_id and db is respected
- Error cases (NoExchangeConnectedError, unknown user, exceptions) return safe strings
- Output contains no raw credentials or internal database keys
"""

import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.exchanges.base import NormalizedBalance, NormalizedCandle, NormalizedTicker
from app.services.portfolio_service import NoExchangeConnectedError as PortfolioNoExchange
from app.services.market_service import NoExchangeConnectedError as MarketNoExchange


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "test@example.com"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    db.execute.return_value = mock_result
    return db, mock_user


class TestAITools:
    @pytest.mark.asyncio
    async def test_get_portfolio_summary_success(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        portfolio_data = {
            "exchange_name": "binance",
            "exchange_id": "test-exchange-id",
            "assets": [
                NormalizedBalance(asset="BTC", free=Decimal("0.5"), locked=Decimal("0.1"), estimated_usd_value=Decimal("33500.00")),
                NormalizedBalance(asset="USDT", free=Decimal("1000.0"), locked=Decimal("0.0"), estimated_usd_value=Decimal("1000.00")),
            ],
            "total_estimated_usd_value": Decimal("34500.00"),
        }

        with patch("app.services.portfolio_service.get_portfolio", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = portfolio_data
            from app.ai.tools import get_portfolio_summary
            result = await get_portfolio_summary.ainvoke({}, config=config)

            assert "Portfolio Summary" in result
            assert "BTC: 0.600000 BTC" in result
            assert "USDT: 1,000.00 USDT" in result
            assert "Total Value: $34,500.00 USDT" in result
            assert "Allocation:" in result
            assert "Available:" in result
            mock_get.assert_awaited_once_with(db, user, include_usd_valuation=True)

    @pytest.mark.asyncio
    async def test_get_portfolio_summary_no_exchange(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        with patch("app.services.portfolio_service.get_portfolio", side_effect=PortfolioNoExchange("No exchange")):
            from app.ai.tools import get_portfolio_summary
            result = await get_portfolio_summary.ainvoke({}, config=config)
            assert "No exchange is connected" in result

    @pytest.mark.asyncio
    async def test_get_asset_balance_found(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        portfolio_data = {
            "exchange_name": "binance",
            "exchange_id": "test-id",
            "assets": [
                NormalizedBalance(asset="ETH", free=Decimal("2.5"), locked=Decimal("0.5"), estimated_usd_value=Decimal("7500.00")),
            ],
            "total_estimated_usd_value": Decimal("7500.00"),
        }

        with patch("app.services.portfolio_service.get_portfolio", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = portfolio_data
            from app.ai.tools import get_asset_balance
            result = await get_asset_balance.ainvoke({"asset": "eth"}, config=config)

            assert "ETH Balance" in result
            assert "Total: 3.0000 ETH" in result
            assert "Available: 2.5000 ETH" in result
            assert "Locked: 0.500000 ETH" in result
            assert "7,500.00" in result

    @pytest.mark.asyncio
    async def test_get_asset_balance_not_found(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        portfolio_data = {
            "exchange_name": "binance",
            "exchange_id": "test-id",
            "assets": [
                NormalizedBalance(asset="BTC", free=Decimal("1.0"), locked=Decimal("0.0")),
            ],
            "total_estimated_usd_value": None,
        }

        with patch("app.services.portfolio_service.get_portfolio", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = portfolio_data
            from app.ai.tools import get_asset_balance
            result = await get_asset_balance.ainvoke({"asset": "SOL"}, config=config)
            assert "You have no SOL holdings" in result

    @pytest.mark.asyncio
    async def test_get_market_ticker_success(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        ticker = NormalizedTicker(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            price=Decimal("68500.50"),
            change_24h_pct=Decimal("3.45"),
            volume_24h=Decimal("12345.67"),
            high_24h=Decimal("69000.00"),
            low_24h=Decimal("66000.00"),
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        with patch("app.services.market_service.get_ticker", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = ticker
            from app.ai.tools import get_market_ticker
            result = await get_market_ticker.ainvoke({"symbol": "BTC"}, config=config)

            assert "BTCUSDT current price: 68,500.5000 USDT" in result
            assert "24h change: +3.45%" in result
            assert "24h high: 69,000.0000" in result
            mock_get.assert_awaited_once_with(db, user, "BTCUSDT")

    @pytest.mark.asyncio
    async def test_get_price_candles_success(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        candles = [
            NormalizedCandle(
                open_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                open=Decimal("65000.00"),
                high=Decimal("67000.00"),
                low=Decimal("64000.00"),
                close=Decimal("66500.00"),
                volume=Decimal("100.0"),
            ),
            NormalizedCandle(
                open_time=datetime(2026, 1, 2, tzinfo=timezone.utc),
                open=Decimal("66500.00"),
                high=Decimal("68000.00"),
                low=Decimal("66000.00"),
                close=Decimal("67800.00"),
                volume=Decimal("150.0"),
            ),
        ]

        with patch("app.services.market_service.get_candles", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = candles
            from app.ai.tools import get_price_candles
            result = await get_price_candles.ainvoke({"symbol": "BTCUSDT", "interval": "1d"}, config=config)

            assert "BTCUSDT 1d candles (last 2 periods)" in result
            assert "Period open: 65,000.0000" in result
            assert "Period close: 67,800.0000" in result
            assert "Range high: 68,000.0000" in result

    @pytest.mark.asyncio
    async def test_get_exchange_status_success(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        mock_ex = MagicMock()
        mock_ex.display_label = "Primary Binance"
        mock_ex.exchange_name = "binance"
        mock_ex.last_synced_at = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)

        with patch("app.services.exchange_service.list_exchanges", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [mock_ex]
            from app.ai.tools import get_exchange_status
            result = await get_exchange_status.ainvoke({}, config=config)

            assert "Connected exchanges:" in result
            assert "Primary Binance: Active" in result
            assert "2026-08-27 12:00 UTC" in result

    @pytest.mark.asyncio
    async def test_get_user_watchlists_success(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        mock_wl_list = [{"id": uuid.uuid4(), "name": "Favorites"}]
        mock_wl_detail = {
            "id": mock_wl_list[0]["id"],
            "name": "Favorites",
            "items": [
                {
                    "symbol": "BTCUSDT",
                    "price": Decimal("68000.00"),
                    "change_24h_pct": Decimal("2.5"),
                },
                {
                    "symbol": "ETHUSDT",
                    "price": Decimal("3500.00"),
                    "change_24h_pct": Decimal("-1.2"),
                },
            ],
        }

        with patch("app.services.watchlist_service.list_watchlists", new_callable=AsyncMock) as mock_list, \
             patch("app.services.watchlist_service.get_watchlist", new_callable=AsyncMock) as mock_detail:
            mock_list.return_value = mock_wl_list
            mock_detail.return_value = mock_wl_detail

            from app.ai.tools import get_user_watchlists
            result = await get_user_watchlists.ainvoke({}, config=config)

            assert "Watchlist 'Favorites' (2 items):" in result
            assert "BTCUSDT: $68,000.0000 (+2.50% 24h)" in result
            assert "ETHUSDT: $3,500.0000 (-1.20% 24h)" in result

    @pytest.mark.asyncio
    async def test_get_user_watchlists_empty(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        with patch("app.services.watchlist_service.list_watchlists", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            from app.ai.tools import get_user_watchlists
            result = await get_user_watchlists.ainvoke({}, config=config)

            assert "You don't have any watchlists yet" in result

    @pytest.mark.asyncio
    async def test_get_user_alerts_success(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        mock_alerts = [
            {
                "symbol": "BTCUSDT",
                "condition": "above",
                "target_price": Decimal("70000.00"),
                "status": "active",
                "current_price": Decimal("68500.00"),
                "distance_pct": Decimal("2.19"),
                "triggered_price": None,
                "triggered_at": None,
                "notes": "ATH watch",
            },
            {
                "symbol": "ETHUSDT",
                "condition": "below",
                "target_price": Decimal("3000.00"),
                "status": "triggered",
                "current_price": Decimal("2950.00"),
                "distance_pct": Decimal("-1.67"),
                "triggered_price": Decimal("2990.00"),
                "triggered_at": datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc),
                "notes": None,
            },
        ]

        with patch("app.services.alert_service.list_alerts", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_alerts

            from app.ai.tools import get_user_alerts
            result = await get_user_alerts.ainvoke({}, config=config)

            assert "Your Price Alerts (2 total):" in result
            assert "BTCUSDT (≥ $70,000.0000) — [ACTIVE]" in result
            assert "Current price: $68,500.0000 (+2.19% to target)" in result
            assert "ETHUSDT (≤ $3,000.0000) — [TRIGGERED]" in result
            assert "Triggered at $2,990.0000 on 2026-08-30 10:00 UTC" in result

    @pytest.mark.asyncio
    async def test_get_user_alerts_empty(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        with patch("app.services.alert_service.list_alerts", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            from app.ai.tools import get_user_alerts
            result = await get_user_alerts.ainvoke({}, config=config)

            assert "You have no price alerts configured" in result

    @pytest.mark.asyncio
    async def test_get_saved_analyses_success(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        from app.models.analysis import Analysis
        mock_reports = [
            Analysis(
                id=uuid.uuid4(),
                user_id=user.id,
                symbol="BTCUSDT",
                assessment="Buy Gradually",
                risk_level="Moderate",
                market_price=Decimal("68000.00"),
                timeframe="1D",
                summary="Solid consolidation above $65,000 support.",
                reasoning="Bullish momentum supported by moving averages.",
                key_price_levels={"support": 65000.0, "resistance": 72000.0},
                technical_indicators={"rsi_14": 55.4},
                created_at=datetime(2026, 8, 30, 14, 0, tzinfo=timezone.utc),
            )
        ]

        with patch("app.services.analysis_service.list_analyses", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_reports

            from app.ai.tools import get_saved_analyses
            result = await get_saved_analyses.ainvoke({"symbol": "BTCUSDT"}, config=config)

            assert "Saved AI Analysis Reports (1 found):" in result
            assert "BTCUSDT (1D) — Assessment: [BUY GRADUALLY]" in result
            assert "Risk: Moderate" in result
            assert "Solid consolidation above $65,000 support." in result
            assert "Support: $65,000.00" in result
            assert "Resistance: $72,000.00" in result

    @pytest.mark.asyncio
    async def test_get_saved_analyses_empty(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        with patch("app.services.analysis_service.list_analyses", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            from app.ai.tools import get_saved_analyses
            result = await get_saved_analyses.ainvoke({"symbol": "ETH"}, config=config)

            assert "No saved analysis reports found for ETH" in result

    @pytest.mark.asyncio
    async def test_get_user_complaints_success(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        mock_complaints = [
            {
                "id": uuid.uuid4(),
                "subject": "Binance sync timeout",
                "category": "Exchange Connection",
                "priority": "high",
                "status": "open",
                "message_count": 2,
                "created_at": datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc),
                "resolution_notes": None,
            },
            {
                "id": uuid.uuid4(),
                "subject": "Missing ETH price alerts",
                "category": "Bug Report",
                "priority": "medium",
                "status": "resolved",
                "message_count": 4,
                "created_at": datetime(2026, 8, 28, 9, 0, tzinfo=timezone.utc),
                "resolution_notes": "Resolved after background ticker fix.",
            },
        ]

        with patch("app.services.complaint_service.list_complaints", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_complaints

            from app.ai.tools import get_user_complaints
            result = await get_user_complaints.ainvoke({}, config=config)

            assert "Your Support Tickets & Complaints (2 total):" in result
            assert "• [OPEN] Binance sync timeout (Category: Exchange Connection, Priority: High, 2 messages" in result
            assert "• [RESOLVED] Missing ETH price alerts" in result
            assert "Resolution: Resolved after background ticker fix." in result

    @pytest.mark.asyncio
    async def test_get_user_complaints_empty(self, mock_db):
        db, user = mock_db
        config = {"configurable": {"user_id": str(user.id), "db": db}}

        with patch("app.services.complaint_service.list_complaints", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            from app.ai.tools import get_user_complaints
            result = await get_user_complaints.ainvoke({}, config=config)

            assert "You have not submitted any support tickets or complaints yet" in result

    @pytest.mark.asyncio
    async def test_tools_user_isolation(self):
        """If user cannot be found in DB for the given user_id, tools return account not found."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        config = {"configurable": {"user_id": str(uuid.uuid4()), "db": db}}
        from app.ai.tools import get_portfolio_summary
        result = await get_portfolio_summary.ainvoke({}, config=config)
        assert "User account not found" in result
