"""
Amazon SP API client.

Handles:
  - LWA (Login with Amazon) token exchange + refresh
  - Automatic access-token refresh (tokens expire every 60 min)
  - Signed API requests (no AWS SigV4 required for seller-authorised calls)
  - Orders, Financial Events, and Reports endpoints

Design rule:
  SPAPIClient makes HTTP calls ONLY.  It does NOT touch the database.
  Token refresh mutates the PlatformConnection object in place; the caller
  must call `await db.commit()` afterwards to persist the updated tokens.

Reference: https://developer-docs.amazon.com/sp-api/docs
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.crypto import decrypt, encrypt

logger = logging.getLogger(__name__)

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

MARKETPLACE_IDS = {
    "amazon.in":    "A21TJRUUN4KGV",
    "amazon.com":   "ATVPDKIKX0DER",
    "amazon.co.uk": "A1F83G8C2ARO7P",
    "amazon.de":    "A1PA6795UKMFR9",
}

SP_API_ENDPOINTS = {
    "na": "https://sellingpartnerapi-na.amazon.com",
    "eu": "https://sellingpartnerapi-eu.amazon.com",   # India uses EU
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def build_authorization_url(state: str) -> str:
    s = get_settings()
    if not s.sp_api_app_id:
        raise ValueError("SP_API_APP_ID not configured")
    params = (
        f"application_id={s.sp_api_app_id}"
        f"&state={state}"
        f"&redirect_uri={s.sp_api_redirect_uri}"
        f"&version=beta"
    )
    return f"https://sellercentral.amazon.in/apps/authorize/consent?{params}"


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange LWA authorization code → access + refresh tokens (called once)."""
    s = get_settings()
    resp = httpx.post(
        LWA_TOKEN_URL,
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  s.sp_api_redirect_uri,
            "client_id":     s.sp_api_client_id,
            "client_secret": s.sp_api_client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token_enc: str) -> dict:
    """Use stored encrypted refresh token to obtain a new access token."""
    s = get_settings()
    resp = httpx.post(
        LWA_TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "refresh_token": decrypt(refresh_token_enc),
            "client_id":     s.sp_api_client_id,
            "client_secret": s.sp_api_client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Token lifecycle ───────────────────────────────────────────────────────────

def get_valid_access_token(connection) -> str:
    """
    Return a valid (non-expired) access token for *connection*.
    Refreshes automatically if expiry is within 5 minutes.

    Mutates connection.sp_access_token_enc and sp_access_token_expires_at in place.
    The *caller* must `await db.commit()` after this to persist the new token.
    """
    if not connection.sp_refresh_token_enc:
        raise ValueError("No refresh token — re-authorise the connection")

    needs_refresh = (
        not connection.sp_access_token_enc
        or not connection.sp_access_token_expires_at
        or connection.sp_access_token_expires_at <= datetime.utcnow() + timedelta(minutes=5)
    )

    if needs_refresh:
        logger.info("Refreshing SP API access token for connection %s", connection.id)
        token_data = refresh_access_token(connection.sp_refresh_token_enc)
        connection.sp_access_token_enc = encrypt(token_data["access_token"])
        connection.sp_access_token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )

    return decrypt(connection.sp_access_token_enc)


# ── SP API HTTP client ────────────────────────────────────────────────────────

class SPAPIClient:
    """
    Thin HTTP wrapper for the SP API.

    Does NOT touch the database.  Call get_valid_access_token(connection)
    and commit before constructing this client so the token is fresh.
    """

    def __init__(self, connection):
        self.connection = connection
        self.endpoint = connection.sp_endpoint or SP_API_ENDPOINTS["eu"]

    def _headers(self) -> dict:
        # Token must already be fresh — caller refreshed it before constructing us
        token = decrypt(self.connection.sp_access_token_enc)
        return {
            "x-amz-access-token": token,
            "Content-Type":       "application/json",
        }

    def get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.endpoint}{path}"
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=self._headers(), params=params or {})
        self._handle_errors(resp)
        return resp.json()

    def post(self, path: str, body: dict) -> Any:
        url = f"{self.endpoint}{path}"
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=self._headers(), json=body)
        self._handle_errors(resp)
        return resp.json()

    @staticmethod
    def _handle_errors(resp: httpx.Response):
        if resp.status_code == 429:
            raise RuntimeError("SP API rate limit — retry after 1 minute")
        if resp.status_code == 403:
            raise PermissionError("SP API 403 — check seller authorisation and scopes")
        resp.raise_for_status()


# ── Data fetchers (pure HTTP, no DB) ─────────────────────────────────────────

def fetch_orders(connection, days_back: int = 30) -> list[dict]:
    """Fetch orders from the last N days. Connection must have a valid token."""
    client = SPAPIClient(connection)
    created_after = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    marketplace_id = connection.sp_marketplace_id or get_settings().sp_api_marketplace_id

    all_orders: list[dict] = []
    next_token = None

    while True:
        params: dict = {
            "MarketplaceIds":    marketplace_id,
            "CreatedAfter":      created_after,
            "MaxResultsPerPage": 100,
        }
        if next_token:
            params["NextToken"] = next_token

        data       = client.get("/orders/v0/orders", params=params)
        payload    = data.get("payload", {})
        all_orders.extend(payload.get("Orders", []))

        next_token = payload.get("NextToken")
        if not next_token:
            break

    logger.info("Fetched %d orders for connection %s", len(all_orders), connection.id)
    return all_orders


def fetch_financial_events(connection, days_back: int = 30) -> dict:
    """Fetch financial event groups (settlements, refunds, fees)."""
    client = SPAPIClient(connection)
    posted_after = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_groups: list[dict] = []
    next_token = None

    while True:
        params: dict = {"PostedAfter": posted_after, "MaxResultsPerPage": 100}
        if next_token:
            params["NextToken"] = next_token

        data        = client.get("/finances/v0/financialEventGroups", params=params)
        payload     = data.get("payload", {})
        all_groups.extend(payload.get("FinancialEventGroupList", []))

        next_token = payload.get("NextToken")
        if not next_token:
            break

    return {"financial_event_groups": all_groups}


def request_settlement_report(connection) -> str:
    """Request a flat-file settlement report; returns the reportId."""
    client = SPAPIClient(connection)
    marketplace_id = connection.sp_marketplace_id or get_settings().sp_api_marketplace_id
    data = client.post("/reports/2021-06-30/reports", {
        "reportType":    "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE",
        "marketplaceIds": [marketplace_id],
    })
    return data.get("reportId", "")


def get_report_status(connection, report_id: str) -> dict:
    return SPAPIClient(connection).get(f"/reports/2021-06-30/reports/{report_id}")


def fetch_catalog_items(connection, asin_list: list[str]) -> list[dict]:
    client = SPAPIClient(connection)
    marketplace_id = connection.sp_marketplace_id or get_settings().sp_api_marketplace_id
    items = []
    for asin in asin_list:
        try:
            items.append(client.get(
                f"/catalog/2022-04-01/items/{asin}",
                params={"marketplaceIds": marketplace_id},
            ))
        except Exception as exc:
            logger.warning("Could not fetch catalog item %s: %s", asin, exc)
    return items
