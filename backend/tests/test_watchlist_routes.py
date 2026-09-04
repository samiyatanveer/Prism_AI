"""
Tests: Watchlist API schemas, validation, security, and route handling.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistDetailResponse,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistSummaryResponse,
    WatchlistUpdate,
)


class TestWatchlistSchemas:
    def test_watchlist_create_valid(self):
        req = WatchlistCreate(name="Main Portfolio", description="Primary tracked coins", symbols=["BTCUSDT", "ETHUSDT"])
        assert req.name == "Main Portfolio"
        assert req.symbols == ["BTCUSDT", "ETHUSDT"]

    def test_watchlist_create_empty_name_raises(self):
        with pytest.raises(ValidationError):
            WatchlistCreate(name="")

    def test_watchlist_item_create_valid(self):
        req = WatchlistItemCreate(symbol="BTCUSDT", notes="Wait for 65k")
        assert req.symbol == "BTCUSDT"
        assert req.notes == "Wait for 65k"

    def test_watchlist_item_create_empty_symbol_raises(self):
        with pytest.raises(ValidationError):
            WatchlistItemCreate(symbol="")

    def test_watchlist_item_response_schema(self):
        now = datetime.now(timezone.utc)
        item = WatchlistItemResponse(
            id=uuid.uuid4(),
            watchlist_id=uuid.uuid4(),
            symbol="BTCUSDT",
            added_price=Decimal("62000.50"),
            notes="Added in dip",
            created_at=now,
            price=Decimal("68000.00"),
            change_24h_pct=Decimal("3.5"),
            high_24h=Decimal("69000.00"),
            low_24h=Decimal("61000.00"),
            volume_24h=Decimal("5000.00"),
            quote_asset="USDT",
        )
        assert item.symbol == "BTCUSDT"
        assert item.price == Decimal("68000.00")
        assert item.change_24h_pct == Decimal("3.5")

    def test_watchlist_detail_response_schema(self):
        now = datetime.now(timezone.utc)
        wl = WatchlistDetailResponse(
            id=uuid.uuid4(),
            name="Layer 1s",
            description="L1 blockchains",
            items=[],
            created_at=now,
            updated_at=now,
        )
        assert wl.name == "Layer 1s"
        assert wl.items == []


class TestWatchlistSchemaSecurity:
    def test_no_sensitive_credentials_in_watchlist_schemas(self):
        schemas = [
            WatchlistCreate,
            WatchlistUpdate,
            WatchlistItemCreate,
            WatchlistItemResponse,
            WatchlistSummaryResponse,
            WatchlistDetailResponse,
        ]
        forbidden_fields = {"api_key", "api_secret", "encrypted_api_key", "encrypted_api_secret", "password", "hashed_password"}

        for schema in schemas:
            fields = set(schema.model_fields.keys())
            overlap = fields & forbidden_fields
            assert not overlap, f"Forbidden fields {overlap} found in {schema.__name__}"
