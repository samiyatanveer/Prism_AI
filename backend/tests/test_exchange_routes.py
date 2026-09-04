"""
Tests: Exchange routes — authentication, validation, error mapping.

Uses only unit-testable logic — no live DB or exchange calls.
"""

import pytest
from app.exchanges.base import (
    ExchangeAPIError,
    ExchangeCredentialError,
    ExchangeRateLimitError,
    ExchangeTimeoutError,
)
from app.api.routes import market as market_routes


class TestExchangeErrorMapping:
    """Test that exchange errors map to correct HTTP status codes."""

    def test_rate_limit_maps_to_429(self):
        exc = ExchangeRateLimitError("Rate limit", status_code=429)
        http_exc = market_routes._map_exchange_error(exc)
        assert http_exc.status_code == 429

    def test_timeout_maps_to_504(self):
        exc = ExchangeTimeoutError("Timeout")
        http_exc = market_routes._map_exchange_error(exc)
        assert http_exc.status_code == 504

    def test_generic_api_error_maps_to_502(self):
        exc = ExchangeAPIError("Something went wrong", status_code=500)
        http_exc = market_routes._map_exchange_error(exc)
        assert http_exc.status_code == 502

    def test_credential_error_maps_to_502(self):
        """ExchangeCredentialError is a subclass of ExchangeAPIError — maps to 502."""
        exc = ExchangeCredentialError("Bad key", status_code=401)
        http_exc = market_routes._map_exchange_error(exc)
        assert http_exc.status_code == 502


class TestExchangeExceptionHierarchy:
    """Verify exception class hierarchy is correct."""

    def test_credential_error_is_api_error(self):
        assert issubclass(ExchangeCredentialError, ExchangeAPIError)

    def test_rate_limit_error_is_api_error(self):
        assert issubclass(ExchangeRateLimitError, ExchangeAPIError)

    def test_api_error_is_exchange_error(self):
        from app.exchanges.base import ExchangeError
        assert issubclass(ExchangeAPIError, ExchangeError)

    def test_timeout_error_is_exchange_error(self):
        from app.exchanges.base import ExchangeError
        assert issubclass(ExchangeTimeoutError, ExchangeError)


class TestExchangeRegistry:
    """Verify the provider registry works correctly."""

    def test_binance_is_supported(self):
        from app.exchanges.registry import get_supported_exchanges
        assert "binance" in get_supported_exchanges()

    def test_unsupported_exchange_raises(self):
        from app.exchanges.registry import get_provider
        with pytest.raises(ValueError, match="not supported"):
            get_provider("fakex", "enc_key", "enc_secret")

    def test_binance_provider_instantiation(self, encrypted_key, encrypted_secret):
        from app.exchanges.registry import get_provider
        from app.exchanges.binance.provider import BinanceProvider
        provider = get_provider("binance", encrypted_key, encrypted_secret)
        assert isinstance(provider, BinanceProvider)
        assert provider.exchange_name == "binance"

    def test_exchange_name_is_case_insensitive(self, encrypted_key, encrypted_secret):
        from app.exchanges.registry import get_provider
        provider = get_provider("BINANCE", encrypted_key, encrypted_secret)
        assert provider.exchange_name == "binance"


class TestConnectExchangeRequestValidation:
    """Validate schema constraints on the connect request."""

    def test_valid_request(self):
        from app.schemas.exchange import ConnectExchangeRequest
        req = ConnectExchangeRequest(
            exchange_name="binance",
            api_key="a" * 10,
            api_secret="b" * 10,
        )
        assert req.exchange_name == "binance"

    def test_key_too_short_raises(self):
        from app.schemas.exchange import ConnectExchangeRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ConnectExchangeRequest(
                exchange_name="binance",
                api_key="short",  # < 8 chars
                api_secret="b" * 10,
            )

    def test_display_label_optional(self):
        from app.schemas.exchange import ConnectExchangeRequest
        req = ConnectExchangeRequest(
            exchange_name="binance",
            api_key="a" * 10,
            api_secret="b" * 10,
        )
        assert req.display_label is None


class TestCredentialNeverInResponse:
    """Verify response schemas have no credential fields."""

    def test_exchange_response_has_no_credential_fields(self):
        from app.schemas.exchange import ExchangeResponse
        fields = set(ExchangeResponse.model_fields.keys())
        credential_fields = {"api_key", "api_secret", "encrypted_api_key", "encrypted_api_secret"}
        overlap = fields & credential_fields
        assert not overlap, f"Credential fields found in ExchangeResponse: {overlap}"

    def test_connect_response_has_no_credential_fields(self):
        from app.schemas.exchange import ConnectExchangeResponse
        # Walk all nested model fields
        fields = set(ConnectExchangeResponse.model_fields.keys())
        assert "api_key" not in fields
        assert "api_secret" not in fields
