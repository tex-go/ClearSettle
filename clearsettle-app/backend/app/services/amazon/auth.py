"""
Amazon LWA (Login with Amazon) OAuth 2.0 utilities.

Handles the full OAuth lifecycle:
  1. build_authorization_url()  → redirect user to Seller Central
  2. exchange_code_for_tokens() → one-time code → access + refresh tokens
  3. refresh_access_token()     → use refresh token to get new access token
  4. get_valid_access_token()   → auto-refresh if expiring within 5 min

All sensitive token values are stored Fernet-encrypted via app.core.crypto.
This module does NOT touch the database — callers are responsible for
persisting the mutated PlatformConnection and calling `await db.commit()`.
"""
import logging
import secrets
from datetime import datetime, timedelta

import httpx

from app.core.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.services.amazon.constants import LWA_TOKEN_URL, DEFAULT_ENDPOINT

logger = logging.getLogger(__name__)

# Access tokens expire after 3600s; we refresh 5 min early as a buffer.
_REFRESH_BUFFER_MINUTES = 5


# ── OAuth URL builder ─────────────────────────────────────────────────────────

def build_authorization_url(state: str) -> str:
    """
    Construct the Amazon Seller Central OAuth consent page URL.

    The user is redirected here to grant the application permission to
    access their Selling Partner data.

    Args:
        state: Cryptographically random CSRF token (store in DB before redirect).

    Returns:
        Full URL string; redirect the user's browser to this.
    """
    s = get_settings()
    if not s.sp_api_app_id:
        raise ValueError("SP_API_APP_ID is not configured")
    if not s.sp_api_redirect_uri:
        raise ValueError("SP_API_REDIRECT_URI is not configured")

    params = "&".join([
        f"application_id={s.sp_api_app_id}",
        f"state={state}",
        f"redirect_uri={s.sp_api_redirect_uri}",
        "version=beta",
    ])
    return f"https://sellercentral.amazon.in/apps/authorize/consent?{params}"


def generate_oauth_state() -> str:
    """Return a cryptographically secure, URL-safe random state token."""
    return secrets.token_urlsafe(32)


# ── Token exchange ────────────────────────────────────────────────────────────

def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange a one-time LWA authorization code for access + refresh tokens.
    Called exactly once from the OAuth callback endpoint.

    Returns dict with keys: access_token, refresh_token, expires_in, token_type.
    Raises httpx.HTTPStatusError on failure.
    """
    s = get_settings()
    _require_lwa_config(s)

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
    token_data = resp.json()
    logger.info("LWA token exchange successful (expires_in=%s)", token_data.get("expires_in"))
    return token_data


def refresh_access_token(refresh_token_enc: str) -> dict:
    """
    Obtain a new access token using a stored (Fernet-encrypted) refresh token.

    Returns dict with keys: access_token, expires_in, token_type.
    Raises httpx.HTTPStatusError if the refresh token is revoked or expired.
    """
    s = get_settings()
    _require_lwa_config(s)

    refresh_token = decrypt(refresh_token_enc)
    resp = httpx.post(
        LWA_TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
            "client_id":     s.sp_api_client_id,
            "client_secret": s.sp_api_client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_data = resp.json()
    logger.debug("Access token refreshed (expires_in=%s)", token_data.get("expires_in"))
    return token_data


# ── Token lifecycle ───────────────────────────────────────────────────────────

def get_valid_access_token(connection) -> str:
    """
    Return a valid (non-expired) access token for *connection*.

    Automatically refreshes if the access token is within
    _REFRESH_BUFFER_MINUTES of expiry (or is missing).

    Side effects:
      - Mutates connection.sp_access_token_enc
      - Mutates connection.sp_access_token_expires_at

    The caller must persist these changes: `db.add(conn); await db.commit()`.

    Raises:
        ValueError   — no refresh token stored (OAuth not completed).
        httpx.HTTPStatusError — LWA refresh request failed.
    """
    if not connection.sp_refresh_token_enc:
        raise ValueError(
            "No refresh token stored for this connection. "
            "Complete the Amazon OAuth flow via /sp-api/authorize."
        )

    needs_refresh = (
        not connection.sp_access_token_enc
        or not connection.sp_access_token_expires_at
        or connection.sp_access_token_expires_at
            <= datetime.utcnow() + timedelta(minutes=_REFRESH_BUFFER_MINUTES)
    )

    if needs_refresh:
        logger.info("Refreshing SP API access token for connection %s", connection.id)
        token_data = refresh_access_token(connection.sp_refresh_token_enc)
        connection.sp_access_token_enc = encrypt(token_data["access_token"])
        connection.sp_access_token_expires_at = (
            datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
        )

    return decrypt(connection.sp_access_token_enc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_lwa_config(s) -> None:
    missing = [
        name for name, val in [
            ("SP_API_CLIENT_ID",     s.sp_api_client_id),
            ("SP_API_CLIENT_SECRET", s.sp_api_client_secret),
        ]
        if not val
    ]
    if missing:
        raise ValueError(f"Amazon LWA credentials not configured: {', '.join(missing)}")
