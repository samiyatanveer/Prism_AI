"""Regression tests for the remaining required PrismAI contracts."""

import pytest
from pydantic import ValidationError
from decimal import Decimal
from datetime import datetime, timezone


def test_public_market_provider_has_no_credentials():
    from app.exchanges.registry import get_public_market_provider

    provider = get_public_market_provider()
    assert provider.exchange_name == "binance"
    # Public ticker/candle use must not require a decrypted account secret.
    assert provider._client._encrypted_api_key == ""
    assert provider._client._encrypted_api_secret == ""


def test_documented_ai_alias_routes_are_registered():
    from app.api.routes.assistant import ai_router

    paths = {route.path for route in ai_router.routes}
    assert "/ai/chat" in paths
    assert "/ai/sessions" in paths
    assert "/ai/sessions/{session_id}" in paths


def test_profile_schema_only_allows_supported_risk_profiles():
    from app.schemas.profile import ProfileUpdate

    assert ProfileUpdate(risk_profile="moderate").risk_profile == "moderate"
    with pytest.raises(ValidationError):
        ProfileUpdate(risk_profile="guaranteed-profit")


def test_risk_profile_migration_follows_the_actual_revision_chain():
    """Keep the deployable Alembic chain intact through the profile release."""
    from pathlib import Path

    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0008_user_risk_profile.py"
    source = migration.read_text(encoding="utf-8")
    assert 'down_revision = "0007"' in source
    assert 'op.add_column("users", sa.Column("risk_profile"' in source


def test_admin_user_response_cannot_expose_password_or_tokens():
    from app.schemas.admin import AdminUserResponse

    forbidden = {"hashed_password", "password", "refresh_token", "token_hash"}
    assert not forbidden.intersection(AdminUserResponse.model_fields)


def test_sensitive_rate_limit_groups_cover_required_operations():
    from app.core.rate_limit import sensitive_endpoint_group

    assert sensitive_endpoint_group("/auth/login") == "auth"
    assert sensitive_endpoint_group("/ai/chat") == "assistant"
    assert sensitive_endpoint_group("/exchanges/connect") == "exchange"
    assert sensitive_endpoint_group("/market/BTCUSDT") is None


def test_market_cache_round_trip_preserves_decimal_market_truth():
    from app.exchanges.base import NormalizedTicker
    from app.services.market_service import _ticker_from_cache, _ticker_to_cache

    ticker = NormalizedTicker(
        symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", price=Decimal("67000.12"),
        change_24h_pct=Decimal("1.23"), volume_24h=Decimal("5.4"), high_24h=Decimal("68000"),
        low_24h=Decimal("65000"), timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    restored = _ticker_from_cache(_ticker_to_cache(ticker))
    assert restored.price == ticker.price
    assert restored.timestamp == ticker.timestamp
