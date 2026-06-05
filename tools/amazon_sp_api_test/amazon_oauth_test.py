"""
amazon_oauth_test.py — Test LWA OAuth token exchange end-to-end.

What this tests:
  1. POST to https://api.amazon.com/auth/o2/token (refresh_token grant)
  2. Parse and display the returned access token metadata
  3. Verify the token works by calling /sellers/v1/marketplaceParticipations
  4. Show expiration time and token lifecycle info

Run:
    python amazon_oauth_test.py
"""

from __future__ import annotations

import base64
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from _sp_client import (
    SPAPIConfig,
    LWAToken,
    SPAPIClient,
    exchange_refresh_token,
    mask,
    Printer,
    LWAError,
    LWA_TOKEN_URL,
)


# ─────────────────────────────────────────────────────────────────────────────
# Token introspection (JWT decode — no signature verification)
# ─────────────────────────────────────────────────────────────────────────────

def _decode_jwt_claims(token: str) -> dict[str, Any]:
    """
    Decode the payload of a JWT without verifying the signature.
    Amazon access tokens are JWTs — we read the claims for display only.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    # JWT payload is base64url-encoded
    payload_b64 = parts[1]
    # Add padding
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
    except Exception:
        return {}


def _format_ts(ts: int) -> str:
    """Format a Unix timestamp as a human-readable UTC datetime."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_token_exchange(config: SPAPIConfig) -> LWAToken:
    """Exchange the refresh token and return the LWA token object."""
    Printer.section("Token Exchange (POST /auth/o2/token)")
    print(f"    Endpoint : {LWA_TOKEN_URL}")
    print(f"    Client ID: {config.lwa_client_id}")
    print(f"    Secret   : {mask(config.lwa_client_secret)}")
    print(f"    Refresh  : {mask(config.lwa_refresh_token)}")
    print()

    start = time.time()
    token = exchange_refresh_token(config)
    elapsed = (time.time() - start) * 1000

    Printer.ok("Token exchange", f"({elapsed:.0f}ms)")
    return token


def test_token_metadata(token: LWAToken) -> None:
    """Display all available metadata from the access token."""
    Printer.section("Token Metadata")

    Printer.kv("token_type",      token.token_type)
    Printer.kv("expires_in",      f"{token.expires_in}s ({token.expires_in // 60}min)")
    Printer.kv("expires_at",      token.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
    Printer.kv("seconds_left",    f"{token.seconds_remaining}s")
    Printer.kv("access_token",    token.masked)

    # Attempt JWT decode — Amazon tokens are usually JWTs
    claims = _decode_jwt_claims(token.access_token)
    if claims:
        print()
        Printer.section("JWT Claims (decoded, not verified)")
        interesting = ["app_id", "iss", "aud", "client_id", "scope",
                       "jti", "iat", "exp", "token_use"]
        for key in interesting:
            if key in claims:
                val = claims[key]
                if key in ("iat", "exp") and isinstance(val, (int, float)):
                    val = f"{val}  ({_format_ts(int(val))})"
                Printer.kv(key, str(val))
        # Print any other claims not in the list above
        extra = {k: v for k, v in claims.items() if k not in interesting}
        for k, v in extra.items():
            Printer.kv(k, str(v))
    else:
        Printer.info("JWT decode", "token is opaque (not a standard JWT)")


def test_token_validity(config: SPAPIConfig, token: LWAToken) -> bool:
    """
    Validate the token works by calling a lightweight SP-API endpoint.
    Uses GET /sellers/v1/marketplaceParticipations which requires minimal permissions.
    """
    Printer.section("Token Validation (live SP-API call)")

    client = SPAPIClient(config)
    # Inject the fresh token directly instead of re-exchanging
    client._token = token

    resp = client.get("/sellers/v1/marketplaceParticipations")
    Printer.result(resp)

    if resp.ok:
        Printer.ok("Token accepted by SP-API", "")
        return True
    elif resp.status_code == 403:
        Printer.fail(
            "Token rejected (403 Forbidden)",
            "Token is valid LWA but lacks SP-API permissions. "
            "Check your app's IAM policy and marketplace authorisation."
        )
    elif resp.status_code == 401:
        Printer.fail("Token rejected (401 Unauthorized)", "Token was not accepted by SP-API.")
    else:
        Printer.fail(f"Unexpected response {resp.status_code}", resp.error_message())

    return resp.ok


def test_token_refresh_cycle(config: SPAPIConfig) -> None:
    """
    Demonstrate the refresh token is reusable across multiple exchanges.
    Requests two access tokens back-to-back — both should succeed.
    """
    Printer.section("Refresh Token Reuse")

    token1 = exchange_refresh_token(config)
    time.sleep(0.5)
    token2 = exchange_refresh_token(config)

    same = token1.access_token == token2.access_token
    Printer.ok("Token 1 obtained", token1.masked)
    Printer.ok("Token 2 obtained", token2.masked)

    if same:
        Printer.info("Tokens are identical",
                     "Amazon caches access tokens — this is expected behaviour.")
    else:
        Printer.ok("Tokens are distinct", "each exchange returned a different access token.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    Printer.header("ClearSettle  Amazon SP-API — OAuth Token Test")

    try:
        config = SPAPIConfig.from_env()
    except EnvironmentError as e:
        Printer.fail("Environment", str(e))
        Printer.footer("Fix .env and re-run.")
        return 1

    failures = 0

    # 1. Token exchange
    try:
        token = test_token_exchange(config)
    except LWAError as e:
        Printer.fail("Token exchange FAILED", str(e))
        Printer.footer("OAuth test failed — cannot continue without an access token.")
        return 1
    except Exception as e:
        Printer.fail("Token exchange FAILED (unexpected)", str(e))
        return 1

    # 2. Metadata
    test_token_metadata(token)

    # 3. Live validation
    if not test_token_validity(config, token):
        failures += 1

    # 4. Refresh cycle
    try:
        test_token_refresh_cycle(config)
    except LWAError as e:
        Printer.fail("Refresh cycle", str(e))
        failures += 1

    # Summary
    Printer.divider()
    if failures == 0:
        Printer.footer("OAuth test PASSED — token exchange and validation working.")
        return 0
    else:
        Printer.footer(f"OAuth test FAILED — {failures} issue(s) found. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
