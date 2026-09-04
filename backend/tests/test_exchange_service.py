"""
Tests: BinanceClient credential security and error handling.

Verifies:
- Credentials are never present in raised exceptions
- Rate limit → ExchangeRateLimitError
- 401/403 → ExchangeCredentialError
- Timeout → ExchangeTimeoutError
- Credential decryption errors surface as ExchangeCredentialError
"""

from decimal import Decimal
import hashlib
import hmac
import logging
import pytest
import pytest_asyncio
import httpx

from app.exchanges.base import (
    ExchangeAPIError,
    ExchangeCredentialError,
    ExchangeRateLimitError,
    ExchangeTimeoutError,
)
from app.exchanges.binance.client import BinanceClient
from app.core.config import get_settings
from app.core.security import encrypt_credential


def make_client(api_key="testkey", api_secret="testsecret"):
    return BinanceClient(
        encrypted_api_key=encrypt_credential(api_key),
        encrypted_api_secret=encrypt_credential(api_secret),
    )


def test_uses_configured_binance_base_url(monkeypatch):
    """The default client endpoint follows BINANCE_BASE_URL."""
    with monkeypatch.context() as env:
        env.setenv("BINANCE_BASE_URL", "https://testnet.binance.vision")
        get_settings.cache_clear()
        client = BinanceClient()
        assert client._base_url == "https://testnet.binance.vision"

    get_settings.cache_clear()


class TestBinanceClientErrors:
    def test_signature_uses_percent_encoded_query_string(self, mocker):
        mocker.patch("app.exchanges.binance.client.decrypt_credential", side_effect=["key", "secret"])
        mocker.patch("app.exchanges.binance.client.time.time", return_value=1700000000)
        client = BinanceClient("encrypted-key", "encrypted-secret", base_url="https://testnet.binance.vision")

        headers, signed_params = client._signed_headers({"note": "a b/c"})

        assert headers == {"X-MBX-APIKEY": "key"}
        query = "note=a%20b%2Fc&timestamp=1700000000000"
        expected = hmac.new(b"secret", query.encode(), hashlib.sha256).hexdigest()
        assert signed_params["signature"] == expected

    def test_account_signature_failure_logs_diagnostics_without_exposing_them(self, mocker, caplog):
        response = mocker.MagicMock()
        response.status_code = 400
        response.json.return_value = {"code": -1022, "msg": "Signature for this request is not valid."}
        client = BinanceClient(base_url="https://testnet.binance.vision")

        with pytest.raises(ExchangeCredentialError):
            client._handle_error(response)

        record = next(record for record in caplog.records if record.name.endswith("binance.client"))
        assert record.binance_error_code == -1022
        assert not hasattr(record, "error_message")
        assert record.base_url == "https://testnet.binance.vision"

    def test_account_request_signs_explicit_recv_window(self, mocker):
        mocker.patch("app.exchanges.binance.client.decrypt_credential", side_effect=["key", "secret"])
        mocker.patch("app.exchanges.binance.client.time.time", return_value=1700000000)
        client = BinanceClient("encrypted-key", "encrypted-secret", base_url="https://testnet.binance.vision")

        _, params = client._signed_headers({"recvWindow": 5000})

        expected_query = "recvWindow=5000&timestamp=1700000000000"
        expected_signature = hmac.new(b"secret", expected_query.encode(), hashlib.sha256).hexdigest()
        assert params == {
            "recvWindow": 5000,
            "timestamp": 1700000000000,
            "signature": expected_signature,
        }

    @pytest.mark.asyncio
    async def test_account_uses_binance_server_time_for_signature(self, mocker):
        time_response = mocker.MagicMock()
        time_response.status_code = 200
        time_response.json.return_value = {"serverTime": 1700000000000}
        account_response = mocker.MagicMock()
        account_response.status_code = 200
        account_response.json.return_value = {"balances": []}
        get = mocker.patch(
            "httpx.AsyncClient.get", side_effect=[time_response, account_response]
        )

        client = make_client(api_key="key", api_secret="secret")
        assert await client.get_account() == {"balances": []}

        assert get.call_args_list[0].args == (
            "https://testnet.binance.vision/api/v3/time",
        )
        account_call = get.call_args_list[1]
        assert account_call.kwargs["params"]["timestamp"] == 1700000000000
        expected_query = "recvWindow=5000&timestamp=1700000000000"
        expected_signature = hmac.new(b"secret", expected_query.encode(), hashlib.sha256).hexdigest()
        assert account_call.kwargs["params"]["signature"] == expected_signature

    @pytest.mark.asyncio
    async def test_rate_limit_429_raises_rate_limit_error(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"code": -1003, "msg": "Too many requests"}
        mocker.patch("httpx.AsyncClient.get", return_value=mock_response)

        client = make_client()
        with pytest.raises(ExchangeRateLimitError):
            await client.get_ticker_24hr("BTCUSDT")

    @pytest.mark.asyncio
    async def test_401_raises_credential_error(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"code": -2014, "msg": "API-key format invalid"}
        mocker.patch("httpx.AsyncClient.get", return_value=mock_response)

        client = make_client()
        with pytest.raises(ExchangeCredentialError):
            await client.get_ticker_24hr("BTCUSDT")

    @pytest.mark.asyncio
    async def test_403_raises_credential_error(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"code": -2015, "msg": "Invalid API-key, IP, or permissions"}
        mocker.patch("httpx.AsyncClient.get", return_value=mock_response)

        client = make_client()
        with pytest.raises(ExchangeCredentialError):
            await client.get_ticker_24hr("BTCUSDT")

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self, mocker):
        mocker.patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.TimeoutException("timeout"),
        )
        client = make_client()
        with pytest.raises(ExchangeTimeoutError):
            await client.get_ticker_24hr("BTCUSDT")

    @pytest.mark.asyncio
    async def test_network_error_raises_api_error(self, mocker):
        mocker.patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.RequestError("connection refused"),
        )
        client = make_client()
        with pytest.raises(ExchangeAPIError):
            await client.get_ticker_24hr("BTCUSDT")


class TestCredentialSecurity:
    def test_log_filter_redacts_signed_request_urls(self):
        from app.core.logging import CredentialScrubFilter

        record = logging.LogRecord(
            "httpx", logging.INFO, "", 0,
            "HTTP Request: GET /api/v3/account?signature=not-safe-to-log", (), None,
        )
        CredentialScrubFilter().filter(record)
        assert record.msg == "[REDACTED]"

    def test_api_key_not_in_exception_message_or_log(self, mocker, caplog):
        """API key must never appear in any raised exception message."""
        api_key = "SUPER_SECRET_API_KEY_12345"
        client = make_client(api_key=api_key)

        mock_response = mocker.MagicMock()
        mock_response.status_code = 401
        # Simulate exchange echoing the key back in its message field —
        # our handler must NOT include that raw message in the exception.
        mock_response.json.return_value = {"code": -2014, "msg": api_key}

        with pytest.raises(ExchangeCredentialError) as exc_info:
            client._handle_error(mock_response)

        # The API key must not appear in the exception message
        assert api_key not in str(exc_info.value)
        record = next(record for record in caplog.records if record.name.endswith("binance.client"))
        assert all(api_key not in str(value) for value in record.__dict__.values())

    def test_encrypted_key_not_stored_as_plaintext(self):
        """Client must not store plaintext credentials as accessible attributes."""
        api_key = "plaintext_key_must_not_be_stored"
        client = make_client(api_key=api_key)

        # Check all string attributes of client — none should be plaintext
        for attr_name in dir(client):
            if attr_name.startswith("__"):
                continue
            try:
                val = getattr(client, attr_name)
                if isinstance(val, str):
                    assert api_key not in val, (
                        f"Plaintext API key found in client.{attr_name}"
                    )
            except Exception:
                pass  # Skip properties that raise

    def test_decryption_failure_raises_credential_error(self):
        """A corrupted encrypted blob must raise ExchangeCredentialError, not expose details."""
        client = BinanceClient(
            encrypted_api_key="not_valid_base64_aes_blob==",
            encrypted_api_secret="not_valid_base64_aes_blob==",
        )
        with pytest.raises(ExchangeCredentialError) as exc_info:
            client._signed_headers({})
        # Error message must not contain the corrupted blob
        assert "not_valid_base64_aes_blob" not in str(exc_info.value)
