"""
Amazon SP API client.

Handles:
  - LWA (Login with Amazon) token exchange + refresh
  - Automatic access-token refresh (tokens expire every 60 min)
  - Signed API requests (no AWS SigV4 required for grantless/seller-authorised calls)
  - Orders, Financial Events, and Reports endpoints

Reference:
  https://developer-docs.amazon.com/sp-api/docs
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.crypto import encrypt, decrypt

logger = logging.getLogger(__name__)

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

# ── Marketplace IDs by region ─────────────────────────────────────────────────
MARKETPLACE_IDS = {
    "amazon.in":  "A21TJRUUN4KGV",
    "amazon.com": "ATVPDKIKX0DER",
    "amazon.co.uk": "A1F83G8C2ARO7P",
    "amazon.de":  "A1PA6795UKMFR9",
}

SP_API_ENDPOINTS = {
    "na": "https://sellingpartnerapi-na.amazon.com",
    "eu": "https://sellingpartnerapi-eu.amazon.com",   # India is in EU region
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def build_authorization_url(state: str) -> str:
    """
    Constructs the Amazon Seller Central OAuth consent URL.
    User is redirected here to grant access.
    """
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
    """Cryptographically secure CSRF state token."""
    return secrets.token_urlsafe(32)


def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange LWA authorization code for access + refresh tokens.
    Called once from the OAuth callback.
    Returns: { access_token, refresh_token, expires_in }
    """
    s = get_settings()
    resp = httpx.post(
        LWA_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": s.sp_api_redirect_uri,
            "client_id": s.sp_api_client_id,
            "client_secret": s.sp_api_client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token_enc: str) -> dict:
    """
    Use a stored (encrypted) refresh token to get a new access token.
    Returns: { access_token, expires_in, ... }
    """
    s = get_settings()
    refresh_token = decrypt(refresh_token_enc)
    resp = httpx.post(
        LWA_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": s.sp_api_client_id,
            "client_secret": s.sp_api_client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Token lifecycle (used by router and background tasks) ─────────────────────

def get_valid_access_token(connection) -> str:
    """
    Returns a valid (non-expired) access token for a PlatformConnection.
    Refreshes automatically if expiry is within 5 minutes.

    Mutates connection.sp_access_token_enc and sp_access_token_expires_at in place;
    the caller must commit the DB session.
    """
    if not connection.sp_refresh_token_enc:
        raise ValueError("No refresh token stored — re-authorise the connection")

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
    Thin wrapper around the SP API HTTP interface.
    Handles access-token injection and rate-limit retries.
    """

    def __init__(self, connection, db_session):
        self.connection = connection
        self.db = db_session
        self.endpoint = connection.sp_endpoint or SP_API_ENDPOINTS["eu"]

    def _headers(self) -> dict:
        token = get_valid_access_token(self.connection)
        self.db.add(self.connection)
        self.db.commit()
        return {
            "x-amz-access-token": token,
            "Content-Type": "application/json",
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
            raise RuntimeError("SP API rate limit hit — retry after 1 minute")
        if resp.status_code == 403:
            raise PermissionError("SP API 403 — check seller authorisation and scopes")
        resp.raise_for_status()


# ── Orders ────────────────────────────────────────────────────────────────────

def fetch_orders(connection, db_session, days_back: int = 30) -> list[dict]:
    """
    Fetches orders from the last N days via Orders API v0.
    Returns a list of order dicts.
    """
    client = SPAPIClient(connection, db_session)
    created_after = (datetime.utcnow() - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    marketplace_id = connection.sp_marketplace_id or get_settings().sp_api_marketplace_id

    all_orders = []
    next_token = None

    while True:
        params = {
            "MarketplaceIds": marketplace_id,
            "CreatedAfter": created_after,
            "MaxResultsPerPage": 100,
        }
        if next_token:
            params["NextToken"] = next_token

        data = client.get("/orders/v0/orders", params=params)
        payload = data.get("payload", {})
        orders = payload.get("Orders", [])
        all_orders.extend(orders)

        next_token = payload.get("NextToken")
        if not next_token:
            break

    logger.info("Fetched %d orders for connection %s", len(all_orders), connection.id)
    return all_orders


# ── Financial Events (Settlements) ───────────────────────────────────────────

def fetch_financial_events(connection, db_session, days_back: int = 30) -> dict:
    """
    Fetches financial event groups (settlements, refunds, fees) via Finances API.
    """
    client = SPAPIClient(connection, db_session)
    posted_after = (datetime.utcnow() - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    all_groups = []
    next_token = None

    while True:
        params = {"PostedAfter": posted_after, "MaxResultsPerPage": 100}
        if next_token:
            params["NextToken"] = next_token

        data = client.get("/finances/v0/financialEventGroups", params=params)
        payload = data.get("payload", {})
        groups = payload.get("FinancialEventGroupList", [])
        all_groups.extend(groups)

        next_token = payload.get("NextToken")
        if not next_token:
            break

    return {"financial_event_groups": all_groups}


# ── Reports (Settlement Reports) ─────────────────────────────────────────────

def request_settlement_report(connection, db_session) -> str:
    """
    Requests a GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE report.
    Returns the reportId to poll for completion.
    """
    client = SPAPIClient(connection, db_session)
    marketplace_id = connection.sp_marketplace_id or get_settings().sp_api_marketplace_id

    body = {
        "reportType": "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE",
        "marketplaceIds": [marketplace_id],
    }
    data = client.post("/reports/2021-06-30/reports", body)
    return data.get("reportId", "")


def get_report_status(connection, db_session, report_id: str) -> dict:
    """Poll a report's processing status."""
    client = SPAPIClient(connection, db_session)
    return client.get(f"/reports/2021-06-30/reports/{report_id}")


# ── Catalog / Product Details ─────────────────────────────────────────────────

def fetch_catalog_items(connection, db_session, asin_list: list[str]) -> list[dict]:
    """Fetch product details for a list of ASINs."""
    client = SPAPIClient(connection, db_session)
    marketplace_id = connection.sp_marketplace_id or get_settings().sp_api_marketplace_id

    items = []
    for asin in asin_list:
        try:
            data = client.get(
                f"/catalog/2022-04-01/items/{asin}",
                params={"marketplaceIds": marketplace_id},
            )
            items.append(data)
        except Exception as exc:
            logger.warning("Could not fetch catalog item %s: %s", asin, exc)
    return items
