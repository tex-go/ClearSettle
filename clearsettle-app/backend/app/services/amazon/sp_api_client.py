"""
Amazon SP API HTTP client — retry-safe and throttle-aware.

Design goals
------------
1. Retry-safe:  transient 5xx and timeout errors are retried with exponential
   backoff.  The caller never has to write retry loops.

2. Throttle-safe: 429 responses respect the Retry-After header.  Rate-limit
   info from x-amzn-RateLimit-Limit is logged so future sessions can implement
   a proper token-bucket limiter.

3. Structured errors: every failure raises a typed exception (SpApiError
   hierarchy) so callers can handle specific cases cleanly.

4. DB-free: this module makes HTTP calls only.  It does NOT touch the database.
   Token refresh mutates the PlatformConnection object in place; the caller
   must `await db.commit()` to persist the new token.

5. Signature-ready: the request pipeline already has a hook for AWS SigV4
   signing (needed for grantless operations).  It is a no-op for seller-
   authorised calls (which use the LWA access token instead).
"""
import logging
import time
from typing import Any, Optional

import httpx

from app.core.crypto import decrypt
from app.services.amazon.auth import get_valid_access_token
from app.services.amazon.constants import (
    DEFAULT_ENDPOINT,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES,
    MAX_RETRY_DELAY,
    RATE_LIMITS,
    RETRY_BACKOFF_BASE,
    RETRYABLE_STATUS_CODES,
    SP_API_ENDPOINTS,
)

logger = logging.getLogger(__name__)


# ── Exception hierarchy ───────────────────────────────────────────────────────

class SpApiError(Exception):
    """Base for all SP API errors."""
    def __init__(self, message: str, status_code: int | None = None, headers: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.headers     = headers or {}


class RateLimitError(SpApiError):
    """HTTP 429 — rate limit exceeded."""
    @property
    def retry_after(self) -> float:
        return float(self.headers.get("Retry-After", 60))


class AuthError(SpApiError):
    """HTTP 401 or 403 — authentication / authorisation failure."""


class NotFoundError(SpApiError):
    """HTTP 404 — resource does not exist."""


class TransientError(SpApiError):
    """HTTP 5xx or network timeout — safe to retry."""


class InvalidResponseError(SpApiError):
    """Non-JSON or unexpected response shape."""


# ── Retry policy ──────────────────────────────────────────────────────────────

class RetryPolicy:
    """
    Executes a callable with exponential backoff retry.

    Retry behaviour:
      RateLimitError  → sleep Retry-After (capped at MAX_RETRY_DELAY), then retry
      TransientError  → sleep RETRY_BACKOFF_BASE * 2^attempt, then retry
      All others      → re-raise immediately (no retry)
    """

    def __init__(
        self,
        max_retries: int = MAX_RETRIES,
        base_delay:  float = RETRY_BACKOFF_BASE,
        max_delay:   float = MAX_RETRY_DELAY,
    ):
        self.max_retries = max_retries
        self.base_delay  = base_delay
        self.max_delay   = max_delay

    def execute(self, fn, *args, **kwargs) -> Any:
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return fn(*args, **kwargs)

            except RateLimitError as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    break
                delay = min(exc.retry_after, self.max_delay)
                logger.warning(
                    "SP API rate limit (429) — sleeping %.1fs (attempt %d/%d)",
                    delay, attempt + 1, self.max_retries,
                )
                time.sleep(delay)

            except TransientError as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    break
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.warning(
                    "SP API transient error %s — retrying in %.1fs (attempt %d/%d)",
                    exc.status_code, delay, attempt + 1, self.max_retries,
                )
                time.sleep(delay)

        raise last_exc  # type: ignore[misc]


_default_retry = RetryPolicy()


# ── Core HTTP client ──────────────────────────────────────────────────────────

class SPAPIClient:
    """
    Thin, retry-aware HTTP wrapper for the Amazon SP API.

    Usage
    -----
    Before constructing this client:
      1. Call get_valid_access_token(conn) to ensure the token is fresh.
      2. Persist the (possibly refreshed) token: `db.add(conn); await db.commit()`.

    Then use client.get() / client.post() — no further token management needed.
    """

    def __init__(
        self,
        connection,
        *,
        region: str | None = None,
        retry_policy: RetryPolicy | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.connection   = connection
        self.endpoint     = (
            SP_API_ENDPOINTS.get(region or connection.sp_region or "eu")
            or connection.sp_endpoint
            or DEFAULT_ENDPOINT
        )
        self.retry_policy = retry_policy or _default_retry
        self.timeout      = timeout

    # ── Public methods ────────────────────────────────────────────────────────

    def get(self, path: str, *, params: dict | None = None) -> Any:
        """HTTP GET with retry."""
        self._log_rate_limit_hint(path)
        return self.retry_policy.execute(self._get, path, params or {})

    def post(self, path: str, body: dict) -> Any:
        """HTTP POST with retry."""
        self._log_rate_limit_hint(path)
        return self.retry_policy.execute(self._post, path, body)

    def get_raw_bytes(self, url: str) -> bytes:
        """
        Download from a pre-signed URL (e.g. report document).
        No auth headers — the URL is already signed by Amazon.
        No retry policy — large downloads are non-idempotent.
        """
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.get(url)
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPStatusError as exc:
            raise SpApiError(
                f"Document download failed: {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.TimeoutException as exc:
            raise TransientError("Document download timed out") from exc

    # ── Private helpers ───────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        """
        Build request headers.

        Seller-authorised calls use only the LWA access token.
        AWS SigV4 signing (for grantless operations) is prepared below but
        left as a no-op until needed.
        """
        token = decrypt(self.connection.sp_access_token_enc)
        headers = {
            "x-amz-access-token": token,
            "Content-Type":       "application/json",
            "Accept":             "application/json",
        }
        # SigV4 hook — grantless operations require AWS credentials + signed headers.
        # For seller-authorised flows, this is a no-op.
        headers.update(self._sigv4_headers_if_needed())
        return headers

    @staticmethod
    def _sigv4_headers_if_needed() -> dict[str, str]:
        """
        Placeholder for AWS SigV4 signing.

        When implementing grantless operations (e.g. Selling Partner Insights),
        populate this with the signed headers:
          Authorization: AWS4-HMAC-SHA256 Credential=…
          x-amz-date: …
          x-amz-security-token: … (if using temporary credentials)
        """
        return {}

    def _get(self, path: str, params: dict) -> Any:
        url = f"{self.endpoint}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=self._headers(), params=params)
        except httpx.TimeoutException as exc:
            raise TransientError(f"GET {path} timed out") from exc
        except httpx.RequestError as exc:
            raise TransientError(f"GET {path} network error: {exc}") from exc

        self._raise_for_status(resp)
        return self._parse_json(resp, path)

    def _post(self, path: str, body: dict) -> Any:
        url = f"{self.endpoint}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=self._headers(), json=body)
        except httpx.TimeoutException as exc:
            raise TransientError(f"POST {path} timed out") from exc
        except httpx.RequestError as exc:
            raise TransientError(f"POST {path} network error: {exc}") from exc

        self._raise_for_status(resp)
        return self._parse_json(resp, path)

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        code = resp.status_code
        headers = dict(resp.headers)

        if code == 429:
            raise RateLimitError("SP API rate limit exceeded", status_code=code, headers=headers)
        if code in {401, 403}:
            raise AuthError(f"SP API auth failure ({code})", status_code=code, headers=headers)
        if code == 404:
            raise NotFoundError("SP API resource not found", status_code=code, headers=headers)
        if code in RETRYABLE_STATUS_CODES:
            raise TransientError(f"SP API server error ({code})", status_code=code, headers=headers)
        if code >= 400:
            raise SpApiError(f"SP API client error ({code}): {resp.text[:300]}", status_code=code)

    @staticmethod
    def _parse_json(resp: httpx.Response, path: str) -> Any:
        try:
            return resp.json()
        except Exception as exc:
            raise InvalidResponseError(
                f"Non-JSON response from SP API {path}: {resp.text[:200]}"
            ) from exc

    def _log_rate_limit_hint(self, path: str) -> None:
        """Log the documented rate limit for the path so ops can plan throttling."""
        for pattern, limits in RATE_LIMITS.items():
            # Simple prefix match — good enough for logging purposes
            if path.startswith(pattern.split("{")[0]):
                logger.debug(
                    "SP API %s — documented rate: %.4f req/s, burst: %d",
                    path, limits["rate"], limits["burst"],
                )
                break
