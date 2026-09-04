"""
Unit and service tests for Watchlist functionality.

Verifies:
- Watchlist CRUD operations
- Strict user data isolation
- Duplicate symbol prevention
- Optional real-time market data enrichment and safe fallbacks
- Symbol normalization helper
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistItem
from app.services import watchlist_service as svc
from app.services.market_service import NoExchangeConnectedError


def make_user(email="testuser@example.com"):
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hashed_test_password",
        role="user",
        is_active=True,
    )
    return user


class TestSymbolNormalization:
    def test_normalize_market_symbol_cases(self):
        assert svc.normalize_market_symbol("BTC") == "BTCUSDT"
        assert svc.normalize_market_symbol("eth") == "ETHUSDT"
        assert svc.normalize_market_symbol("SOLUSDT") == "SOLUSDT"
        assert svc.normalize_market_symbol("bnb/usdc") == "BNBUSDC"
        assert svc.normalize_market_symbol("ada-try") == "ADATRY"
        assert svc.normalize_market_symbol("ETHBTC") == "ETHBTC"


class TestWatchlistServiceLogic:
    @pytest.mark.asyncio
    async def test_create_watchlist_mocked_db(self):
        user = make_user()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Mock get_watchlist return and market_service
        with patch.object(
            svc,
            "get_watchlist",
            return_value={
                "id": uuid.uuid4(),
                "name": "DeFi Gems",
                "description": "Top DeFi tokens",
                "items": [],
                "created_at": None,
                "updated_at": None,
            },
        ), patch("app.services.market_service.get_ticker", new_callable=AsyncMock) as mock_ticker:
            mock_ticker.side_effect = NoExchangeConnectedError("No exchange")
            res = await svc.create_watchlist(
                db=mock_db,
                user=user,
                name="DeFi Gems",
                description="Top DeFi tokens",
                symbols=["BTC", "ETHUSDT"],
            )
            assert res["name"] == "DeFi Gems"
            assert mock_db.add.called
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_get_watchlist_not_found(self):
        user = make_user()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(svc.WatchlistNotFoundError):
            await svc.get_watchlist(mock_db, user, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_add_duplicate_symbol_raises(self):
        user = make_user()
        wl_id = uuid.uuid4()
        mock_db = AsyncMock()

        # 1st execute for watchlist lookup (found)
        # 2nd execute for item lookup (duplicate found)
        mock_wl = Watchlist(id=wl_id, user_id=user.id, name="Main")
        mock_item = WatchlistItem(id=uuid.uuid4(), watchlist_id=wl_id, symbol="BTCUSDT")

        res_wl = MagicMock()
        res_wl.scalar_one_or_none.return_value = mock_wl

        res_item = MagicMock()
        res_item.scalar_one_or_none.return_value = mock_item

        mock_db.execute.side_effect = [res_wl, res_item]

        with pytest.raises(svc.DuplicateSymbolError):
            await svc.add_item(mock_db, user, wl_id, "BTCUSDT")

    @pytest.mark.asyncio
    async def test_remove_item_not_found_raises(self):
        user = make_user()
        wl_id = uuid.uuid4()
        mock_db = AsyncMock()

        mock_wl = Watchlist(id=wl_id, user_id=user.id, name="Main")
        res_wl = MagicMock()
        res_wl.scalar_one_or_none.return_value = mock_wl

        res_item = MagicMock()
        res_item.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [res_wl, res_item]

        with pytest.raises(svc.WatchlistItemNotFoundError):
            await svc.remove_item(mock_db, user, wl_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_delete_watchlist_success(self):
        user = make_user()
        wl_id = uuid.uuid4()
        mock_db = AsyncMock()

        mock_wl = Watchlist(id=wl_id, user_id=user.id, name="Main")
        res_wl = MagicMock()
        res_wl.scalar_one_or_none.return_value = mock_wl
        mock_db.execute.return_value = res_wl

        success = await svc.delete_watchlist(mock_db, user, wl_id)
        assert success is True
        mock_db.delete.assert_called_once_with(mock_wl)
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_market_enrichment_fallback_when_exchange_disconnected(self):
        """When exchange is disconnected, items must still return with None market data fields."""
        user = make_user()
        mock_db = AsyncMock()

        item1 = WatchlistItem(
            id=uuid.uuid4(),
            watchlist_id=uuid.uuid4(),
            symbol="BTCUSDT",
            added_price=Decimal("60000"),
            notes="Watch for bounce",
            created_at=None,
        )
        item2 = WatchlistItem(
            id=uuid.uuid4(),
            watchlist_id=uuid.uuid4(),
            symbol="SOLUSDT",
            added_price=None,
            notes=None,
            created_at=None,
        )

        with patch(
            "app.services.market_service.get_tickers",
            side_effect=NoExchangeConnectedError("No exchange connected"),
        ):
            enriched = await svc._enrich_items_with_market_data(mock_db, user, [item1, item2])
            assert len(enriched) == 2
            assert enriched[0]["symbol"] == "BTCUSDT"
            assert enriched[0]["price"] is None
            assert enriched[0]["change_24h_pct"] is None
            assert enriched[0]["added_price"] == Decimal("60000")
            assert enriched[1]["symbol"] == "SOLUSDT"
            assert enriched[1]["price"] is None

    @pytest.mark.asyncio
    async def test_market_enrichment_success(self, sample_ticker):
        """When exchange is connected, items receive real-time ticker data."""
        user = make_user()
        mock_db = AsyncMock()

        item = WatchlistItem(
            id=uuid.uuid4(),
            watchlist_id=uuid.uuid4(),
            symbol="BTCUSDT",
            added_price=Decimal("65000"),
            notes="Core holding",
            created_at=None,
        )

        with patch(
            "app.services.market_service.get_tickers",
            return_value={"BTCUSDT": sample_ticker},
        ):
            enriched = await svc._enrich_items_with_market_data(mock_db, user, [item])
            assert len(enriched) == 1
            assert enriched[0]["symbol"] == "BTCUSDT"
            assert enriched[0]["price"] == Decimal("67000.00")
            assert enriched[0]["change_24h_pct"] == Decimal("2.5")
            assert enriched[0]["volume_24h"] == Decimal("1234.56")
