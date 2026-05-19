#!/usr/bin/env python3
"""
Amazon SP-API Connection Test
==============================
Tests Amazon seller account connectivity using LWA (Login with Amazon) tokens.

This script mirrors ClearSettle's own SP API client approach — LWA access token
only, no AWS SigV4 signing required for seller-authorized calls.

Usage
-----
    # Install dependencies (already in backend/requirements.txt)
    pip install httpx python-dotenv

    # Set credentials in .env file, then run:
    python test_connection.py

    # Or pass credentials inline:
    SP_API_CLIENT_ID=xxx SP_API_CLIENT_SECRET=xxx SP_API_REFRESH_TOKEN=xxx python test_connection.py

Required Environment Variables
-------------------------------
    SP_API_CLIENT_ID        LWA Client ID      (amzn1.application-oa2-client.xxx)
    SP_API_CLIENT_SECRET    LWA Client Secret  (amzn1.oa2-cs.v1.xxx)
    SP_API_REFRESH_TOKEN    Refresh token from completed OAuth flow (Atzr|xxx)

Optional Environment Variables
--------------------------------
    SP_API_ENDPOINT         Default: https://sellingpartnerapi-eu.amazon.com
    SP_API_MARKETPLACE_ID   Default: A21TJRUUN4KGV (amazon.in)

.env File Format
-----------------
    SP_API_CLIENT_ID=amzn1.application-oa2-client.373285617442426d8cc4f8b329900b6f
    SP_API_CLIENT_SECRET=amzn1.oa2-cs.v1.3f84e2f12...
    SP_API_REFRESH_TOKEN=Atzr|IwEB...

    # Optional
    SP_API_ENDPOINT=https://sellingpartnerapi-eu.amazon.com
    SP_API_MARKETPLACE_ID=A21TJRUUN4KGV

Expected Output
---------------
    → Refreshing LWA access token...
    ✓ Access token obtained (expires in 3600s)
    → Calling /sellers/v1/marketplaceParticipations...
    ✓ SP API responded with 1 marketplace(s)

    {
      "status": "connected",
      "marketplace": "IN",
      "sp_api_access": true,
      "selling_partner_id": "XXXXXXXXXXXXX",
      "marketplaces": [...]
    }

Note on python-amazon-sp-api SDK
----------------------------------
    The python-amazon-sp-api package requires AWS IAM credentials (access key +
    secret key) for SigV4 request signing, even for seller-authorized calls.
    ClearSettle uses LWA tokens only (no AWS credentials needed for India SP API).
    This script uses the same direct httpx approach as ClearSettle's SPAPIClient.

Common Errors
--------------
    invalid_grant       — Refresh token expired or revoked. Re-run OAuth flow.
    invalid_client      — Wrong client_id or client_secret.
    HTTP 403            — App missing required SP API roles/permissions.
    HTTP 401            — Access token rejected; check credentials.
    Connection error    — Check network/VPN; ensure endpoint is reachable.
"""
import json
import os
import sys


def _load_env() -> None:
    """Load .env file if present (silent if not found)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv not installed; env vars must be set externally


def _require(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        print(f"ERROR: Missing required environment variable: {key}", file=sys.stderr)
        print("       See the .env format at the top of this script.", file=sys.stderr)
        sys.exit(1)
    return value


def _explain_error(status_code: int, body: str) -> str:
    body_lower = body.lower()
    if "invalid_grant" in body_lower:
        return "Refresh token is expired or revoked. Re-run the Amazon OAuth flow via GET /sp-api/authorize."
    if "invalid_client" in body_lower:
        return "Wrong client_id or client_secret. Check your LWA app credentials."
    if "unauthorized_client" in body_lower:
        return "Client not authorized. Ensure the SP API app has the correct roles."
    if status_code == 401:
        return "Access token rejected. The token may have expired mid-flight."
    if status_code == 403:
        return "Permission denied. Check SP API app roles for the India marketplace."
    if status_code == 429:
        return "Rate limit hit. Wait a moment and try again."
    if status_code >= 500:
        return "Amazon server error. This is usually transient — retry in a few seconds."
    return "Check your credentials and that the SP API endpoint is reachable."


def run_test() -> None:
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx is not installed. Run: pip install httpx", file=sys.stderr)
        sys.exit(1)

    _load_env()

    client_id     = _require("SP_API_CLIENT_ID")
    client_secret = _require("SP_API_CLIENT_SECRET")
    refresh_token = _require("SP_API_REFRESH_TOKEN")
    endpoint      = os.environ.get("SP_API_ENDPOINT", "https://sellingpartnerapi-eu.amazon.com").rstrip("/")
    marketplace_id = os.environ.get("SP_API_MARKETPLACE_ID", "A21TJRUUN4KGV")

    # ── Step 1: Refresh LWA access token ─────────────────────────────────────

    print("→ Refreshing LWA access token...")
    try:
        token_resp = httpx.post(
            "https://api.amazon.com/auth/o2/token",
            data={
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            timeout=15,
        )
    except httpx.TimeoutException:
        print("ERROR: Token refresh timed out after 15s", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as exc:
        print(f"ERROR: Network error during token refresh: {exc}", file=sys.stderr)
        sys.exit(1)

    if token_resp.status_code != 200:
        body = token_resp.text
        result = {
            "status":       "failed",
            "step":         "token_refresh",
            "http_status":  token_resp.status_code,
            "error":        body[:300],
            "hint":         _explain_error(token_resp.status_code, body),
        }
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)

    token_data   = token_resp.json()
    access_token = token_data["access_token"]
    expires_in   = token_data.get("expires_in", 3600)
    print(f"✓ Access token obtained (expires in {expires_in}s)")

    # ── Step 2: Call Sellers API ──────────────────────────────────────────────

    url = f"{endpoint}/sellers/v1/marketplaceParticipations"
    print(f"→ Calling {url}...")

    try:
        resp = httpx.get(
            url,
            headers={
                "x-amz-access-token": access_token,
                "Content-Type":       "application/json",
                "Accept":             "application/json",
            },
            timeout=30,
        )
    except httpx.TimeoutException:
        print("ERROR: SP API call timed out after 30s", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as exc:
        print(f"ERROR: Network error reaching SP API: {exc}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code != 200:
        body = resp.text
        result = {
            "status":      "failed",
            "step":        "marketplace_participations",
            "http_status": resp.status_code,
            "error":       body[:300],
            "hint":        _explain_error(resp.status_code, body),
        }
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)

    # ── Step 3: Parse response ────────────────────────────────────────────────

    payload = resp.json().get("payload", [])
    print(f"✓ SP API responded with {len(payload)} marketplace(s)\n")

    marketplaces   = []
    primary_country = None

    for item in payload:
        mkt  = item.get("marketplace", {})
        part = item.get("participation", {})
        marketplaces.append({
            "id":                     mkt.get("id"),
            "country":                mkt.get("countryCode"),
            "name":                   mkt.get("name"),
            "currency":               mkt.get("defaultCurrencyCode"),
            "participating":          part.get("isParticipating"),
            "has_suspended_listings": part.get("hasSuspendedListings"),
        })
        if mkt.get("id") == marketplace_id:
            primary_country = mkt.get("countryCode")

    if not primary_country and marketplaces:
        primary_country = marketplaces[0]["country"]

    result = {
        "status":       "connected",
        "marketplace":  primary_country,
        "sp_api_access": True,
        "marketplaces": marketplaces,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run_test()
