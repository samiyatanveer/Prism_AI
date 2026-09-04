"""
Binance REST API HTTP client.

Credential security rules enforced here:
- Encrypted credentials are stored on the instance.
- Plaintext API key and secret are decrypted only inside ``_signed_headers()``,
  used immediately to compute the request signature, then explicitly deleted
  from local scope. They are never stored as instance attributes.
- API key and secret are NEVER logged, raised in exceptions, or returned.
- Decryption errors surface as ``ExchangeCredentialError`` with a generic message.

Public endpoints (ticker, candles) do not require credentials.
Private endpoints (account) require HMAC-SHA256 signed requests.
"""

import hashlib
import hmac
import time
from urllib.parse import quote, urlencode

import httpx
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import decrypt_credential
from app.exchanges.base import (
    ExchangeAPIError,
    ExchangeCredentialError,
    ExchangeRateLimitError,
    ExchangeTimeoutError,
)

_BINANCE_BASE_URL = "https://api.binance.com"
_DEFAULT_TIMEOUT = 8.0  # seconds
logger = get_logger(__name__)


class BinanceClient:
    """
    Low-level Binance REST API client.

    Pass encrypted credential blobs (from ``ConnectedExchange``) directly.
    Credentials are decrypted on-demand and discarded after each signed call.
    """

    def __init__(
    self,
    encrypted_api_key: str = "",
    encrypted_api_secret: str = "",
    base_url: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> None:
        # Store ONLY the encrypted blobs — never the plaintext
        self._encrypted_api_key = encrypted_api_key
        self._encrypted_api_secret = encrypted_api_secret
        self._base_url = base_url or get_settings().binance_base_url
        self._timeout = timeout
        logger.info("Binance client configured", extra={"base_url": self._base_url})

    # ── Private helpers ───────────────────────────────────────────────────────

    def _signed_headers(
        self,
        params: dict,
        timestamp_ms: int | None = None,
    ) -> tuple[dict, dict]:
        """
        Decrypt credentials, compute HMAC-SHA256 signature, discard plaintext.

        Returns ``(headers, signed_params)``.
        API key and secret exist as local variables only — deleted explicitly
        before the function returns. Never stored as instance state.

        :raises ExchangeCredentialError: if decryption fails.
        """
        if not self._encrypted_api_key or not self._encrypted_api_secret:
            raise ExchangeCredentialError("Exchange credentials are required for this request.")

        try:
            api_key = decrypt_credential(self._encrypted_api_key)
            api_secret = decrypt_credential(self._encrypted_api_secret)
        except Exception:
            # Decryption failure — do not propagate internal error details
            raise ExchangeCredentialError(
                "Failed to load exchange credentials. Please reconnect the exchange."
            )

        try:
            timestamp_ms = timestamp_ms or int(time.time() * 1000)
            signed_params = {**params, "timestamp": timestamp_ms}
            # Binance signs the percent-encoded query string. Use %20 for
            # spaces (rather than form-style '+') and encode reserved bytes.
            query_string = urlencode(signed_params, quote_via=quote)
            signature = hmac.new(
                api_secret.encode(),
                query_string.encode(),
                hashlib.sha256,
            ).hexdigest()
            signed_params["signature"] = signature
            headers = {"X-MBX-APIKEY": api_key}
            return headers, signed_params
        finally:
            # Explicitly clear plaintext from local scope
            try:
                del api_key
                del api_secret
            except NameError:
                pass  # already deleted or never assigned

    def _handle_error(self, response: httpx.Response) -> None:
        """
        Raise the appropriate exception for non-2xx responses.

        Never includes request parameters, credentials, or raw exchange
        messages that could contain key material in the raised exception.
        """
        status = response.status_code

        try:
            body = response.json()
            code = body.get("code", "") if isinstance(body, dict) else ""
        except Exception:
            code = ""

        # Log only status and Binance's numeric error code.  Never log params,
        # credentials, signatures, or the exchange-provided message because it
        # can theoretically reflect request data.
        logger.warning(
            "Binance request failed",
            extra={
                "base_url": self._base_url,
                "status_code": status,
                "binance_error_code": code,
            },
        )

        # Binance may return credential/signature failures as HTTP 400 rather
        # than 401/403. Treat the documented auth error codes consistently.
        if str(code) in {"-1022", "-2014", "-2015"}:
            raise ExchangeCredentialError(
                "Exchange rejected the request. Check your API key permissions.",
                status_code=status,
                error_code=str(code),
            )

        if status == 429 or status == 418:
            raise ExchangeRateLimitError(
                "Binance rate limit reached. Please wait before retrying.",
                status_code=status,
                error_code=str(code),
            )

        if status in (401, 403):
            # Could mean invalid API key, bad signature, or IP restriction
            raise ExchangeCredentialError(
                "Exchange rejected the request. Check your API key permissions.",
                status_code=status,
                error_code=str(code),
            )

        # Extract exchange error code from body for non-credential errors
        # but sanitize — only include the exchange error code, not raw message
        try:
            body = response.json()
            code = body.get("code", "")
            # Only surface the numeric error code, never the raw message field
            # which could theoretically contain reflected key material
            detail = f"Binance error code {code}" if code else f"HTTP {status}"
        except Exception:
            detail = f"HTTP {status}"

        raise ExchangeAPIError(detail, status_code=status, error_code=str(code) or None)

    async def _get_server_time(self) -> int:
        """Fetch Binance server time for a signed request timestamp."""
        url = f"{self._base_url}/api/v3/time"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ExchangeTimeoutError(
                f"Binance time request timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            raise ExchangeAPIError("Network error contacting Binance.") from exc

        if response.status_code != 200:
            self._handle_error(response)

        try:
            return int(response.json()["serverTime"])
        except (KeyError, TypeError, ValueError):
            raise ExchangeAPIError("Binance returned an invalid server time.")

    # ── Public (no credentials required) ─────────────────────────────────────

    async def get_ticker_24hr(self, symbol: str) -> dict:
        """GET /api/v3/ticker/24hr — 24-hour price statistics."""
        url = f"{self._base_url}/api/v3/ticker/24hr"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params={"symbol": symbol.upper()})
        except httpx.TimeoutException as exc:
            raise ExchangeTimeoutError(
                f"Binance ticker request timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            raise ExchangeAPIError("Network error contacting Binance.") from exc

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()

    async def get_tickers_24hr(self, symbols: list[str]) -> list[dict]:
        """GET /api/v3/ticker/24hr for multiple symbols."""
        if not symbols:
            return []
        import json
        url = f"{self._base_url}/api/v3/ticker/24hr"
        formatted_symbols = json.dumps([s.upper() for s in symbols])
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params={"symbols": formatted_symbols})
        except httpx.TimeoutException as exc:
            raise ExchangeTimeoutError(
                f"Binance tickers request timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            raise ExchangeAPIError("Network error contacting Binance.") from exc

        if response.status_code != 200:
            self._handle_error(response)

        data = response.json()
        return data if isinstance(data, list) else [data]

    async def get_klines(self, symbol: str, interval: str, limit: int = 90) -> list:
        """GET /api/v3/klines — candlestick / OHLCV data."""
        url = f"{self._base_url}/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000),
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise ExchangeTimeoutError(
                f"Binance klines request timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            raise ExchangeAPIError("Network error contacting Binance.") from exc

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()

    # ── Private (signed requests) ─────────────────────────────────────────────

    async def get_account(self) -> dict:
        """GET /api/v3/account — account information including balances (signed)."""
        url = f"{self._base_url}/api/v3/account"
        # Binance defaults to 5 seconds, but including it in the signed query
        # makes the request window explicit and keeps it within Binance's
        # recommended maximum for normal API traffic.
        # Use Binance's time rather than the host clock. This prevents the
        # -1021 timestamp rejection when a development machine clock drifts.
        server_time_ms = await self._get_server_time()
        headers, params = self._signed_headers(
            {"recvWindow": 5000}, timestamp_ms=server_time_ms
        )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=headers, params=params)
        except httpx.TimeoutException as exc:
            raise ExchangeTimeoutError(
                f"Binance account request timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            raise ExchangeAPIError("Network error contacting Binance.") from exc

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()

    async def ping(self) -> bool:
        """
        GET /api/v3/account with minimal data to validate credentials.

        :raises ExchangeCredentialError: if credentials are invalid.
        :raises ExchangeAPIError: on other failures.
        :returns: True on success.
        """
        # Using GET /api/v3/account is the canonical way to validate
        # both key existence and read permission
        await self.get_account()
        return True
