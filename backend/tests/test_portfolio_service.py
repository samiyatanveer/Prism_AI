"""
Tests: Portfolio service — balance normalization and USD valuation rules.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.exchanges.binance.normalizers import normalize_balances
from app.exchanges.base import ExchangeTimeoutError, NormalizedBalance
from tests.conftest import BINANCE_ACCOUNT_RESPONSE


class TestPortfolioNormalization:
    def test_non_zero_assets_included(self):
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        assets = {b.asset for b in balances}
        assert "BTC" in assets
        assert "USDT" in assets

    def test_zero_balances_excluded(self):
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        assets = {b.asset for b in balances}
        assert "ETH" not in assets  # ETH row has 0 free and 0 locked

    def test_usd_value_is_none_from_normalizer(self):
        """
        The normalizer must never set estimated_usd_value.
        USD valuation is portfolio_service's responsibility.
        """
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        for b in balances:
            assert b.estimated_usd_value is None

    def test_free_and_locked_values_correct(self):
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        btc = next(b for b in balances if b.asset == "BTC")
        assert btc.free == Decimal("0.5")
        assert btc.locked == Decimal("0.0")

    def test_total_computed_correctly(self):
        """Routes compute total = free + locked; verify the values are correct."""
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        btc = next(b for b in balances if b.asset == "BTC")
        assert btc.free + btc.locked == Decimal("0.5")

    def test_stablecoin_identified(self):
        """USDT is returned as a regular balance — classification is portfolio service concern."""
        balances = normalize_balances(BINANCE_ACCOUNT_RESPONSE)
        usdt = next(b for b in balances if b.asset == "USDT")
        assert usdt.free == Decimal("1000.0")


class TestUSDValuationPolicy:
    """
    Verify USD valuation is never fabricated.
    These are policy tests — they check the data contract, not live API calls.
    """

    def test_null_usd_value_is_valid_response(self):
        """A balance with None estimated_usd_value must be a valid NormalizedBalance."""
        b = NormalizedBalance(
            asset="SOMETOKEN",
            free=Decimal("10"),
            locked=Decimal("0"),
            estimated_usd_value=None,
        )
        assert b.estimated_usd_value is None

    def test_total_usd_none_when_any_asset_missing_price(self):
        """
        If any asset has no USD price, the aggregate total must also be None.
        This is enforced in portfolio_service.get_portfolio().
        """
        assets = [
            NormalizedBalance("BTC", Decimal("1"), Decimal("0"), Decimal("67000")),
            NormalizedBalance("SOMETOKEN", Decimal("100"), Decimal("0"), None),  # No price
        ]
        # Simulate the aggregation logic from portfolio_service
        has_all_prices = all(b.estimated_usd_value is not None for b in assets)
        total = sum(b.estimated_usd_value for b in assets if b.estimated_usd_value) if has_all_prices else None
        assert total is None

    def test_total_usd_computed_when_all_assets_have_price(self):
        assets = [
            NormalizedBalance("BTC", Decimal("1"), Decimal("0"), Decimal("67000")),
            NormalizedBalance("USDT", Decimal("1000"), Decimal("0"), Decimal("1000")),
        ]
        has_all_prices = all(b.estimated_usd_value is not None for b in assets)
        total = sum(b.estimated_usd_value for b in assets) if has_all_prices else None
        assert total == Decimal("68000")


@pytest.mark.asyncio
async def test_portfolio_keeps_balances_when_optional_ticker_times_out(mocker):
    """A valuation failure must not hide successfully fetched account balances."""
    from app.services.portfolio_service import get_portfolio

    exchange = MagicMock(exchange_name="binance", id="exchange-id")
    provider = MagicMock()
    provider.get_balances = AsyncMock(return_value=[
        NormalizedBalance("BTC", Decimal("0.5"), Decimal("0")),
    ])
    provider.get_ticker = AsyncMock(side_effect=ExchangeTimeoutError("timeout"))
    mocker.patch(
        "app.services.portfolio_service._get_active_exchange_and_provider",
        new=AsyncMock(return_value=(exchange, provider)),
    )

    result = await get_portfolio(MagicMock(), MagicMock())

    assert result["assets"][0].asset == "BTC"
    assert result["assets"][0].estimated_usd_value is None
    assert result["total_estimated_usd_value"] is None
