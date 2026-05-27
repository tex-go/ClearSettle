"""
Amazon LWA (Login with Amazon) OAuth 2.0 utilities.

Handles the full OAuth lifecycle:
  1. build_authorization_url()  → redirect user to Seller Central
  2. exchange_code_for_tokens() → one-time code → access + refresh tokens
  3. refresh_access_token()     → use refresh token to get new access token
  4. get_valid_access_token()   → auto-refresh if expiring within 5 min

Credential resolution order (all functions):
  1. Explicit keyword argument (supplied by caller from DB connection row)
  2. Environment variable / Settings (SP_API_* env vars)
  Raises ValueError when neither source provides the required value.

All sensitive token values are stored Fernet-encrypted via app.core.crypto.
This module does NOT touch the database — callers are responsible for
persisting the mutated PlatformConnection and calling `await db.commit()`.
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.services.amazon.constants import LWA_TOKEN_URL, DEFAULT_ENDPOINT

logger = logging.getLogger(__name__)

_REFRESH_BUFFER_MINUTES = 5


def _s():
    return get_settings()


def _resolve(explicit: Optional[str], env_value: str, name: str) -> str:
    """Return explicit if set, else env_value, else raise ValueError."""
    value = explicit or env_value
    if not value:
        raise ValueError(
            f"{name} is not configured. "
            f"Set it via POST /sp-api/config or the {name.upper().replace(' ', '_')} environment variable."
        )
    return value


# ── OAuth URL builder ─────────────────────────────────────────────────────────

def build_authorization_url(
    state: str,
    *,
    app_id: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> str:
    """
    Construct the Amazon Seller Central OAuth consent page URL.

    Args:
        state:        Cryptographically random CSRF token.
        app_id:       SP API Application ID (DB-sourced; falls back to SP_API_APP_ID env var).
        redirect_uri: OAuth redirect URI (DB-sourced; falls back to SP_API_REDIRECT_URI env var).
    """
    s = _s()
    resolved_app_id      = _resolve(app_id,       s.sp_api_app_id,       "SP_API_APP_ID")
    resolved_redirect_uri = _resolve(redirect_uri, s.sp_api_redirect_uri, "SP_API_REDIRECT_URI")

    params = "&".join([
        f"application_id={resolved_app_id}",
        f"state={state}",
        f"redirect_uri={resolved_redirect_uri}",
        "version=beta",
    ])
    return f"https://sellercentral.amazon.in/apps/authorize/consent?{params}"


def generate_oauth_state() -> str:
    """Return a cryptographically secure, URL-safe random state token."""
    return secrets.token_urlsafe(32)


# ── Token exchange ────────────────────────────────────────────────────────────

def exchange_code_for_tokens(
    code: str,
    *,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> dict:
    """
    Exchange a one-time LWA authorization code for access + refresh tokens.

    Credentials are resolved DB-first (explicit kwargs) then env vars.
    Returns dict with keys: access_token, refresh_token, expires_in, token_type.
    Raises httpx.HTTPStatusError on failure.
    """
    s = _s()
    resolved_client_id     = _resolve(client_id,     s.sp_api_client_id,     "SP_API_CLIENT_ID")
    resolved_client_secret = _resolve(client_secret, s.sp_api_client_secret, "SP_API_CLIENT_SECRET")
    resolved_redirect_uri  = _resolve(redirect_uri,  s.sp_api_redirect_uri,  "SP_API_REDIRECT_URI")

    resp = httpx.post(
        LWA_TOKEN_URL,
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  resolved_redirect_uri,
            "client_id":     resolved_client_id,
            "client_secret": resolved_client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_data = resp.json()
    logger.info("LWA token exchange successful (expires_in=%s)", token_data.get("expires_in"))
    return token_data


def refresh_access_token(
    refresh_token_enc: str,
    *,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> dict:
    """
    Obtain a new access token using a stored (Fernet-encrypted) refresh token.

    Credentials resolved DB-first (explicit kwargs) then env vars.
    Returns dict with keys: access_token, expires_in, token_type.
    """
    s = _s()
    resolved_client_id     = _resolve(client_id,     s.sp_api_client_id,     "SP_API_CLIENT_ID")
    resolved_client_secret = _resolve(client_secret, s.sp_api_client_secret, "SP_API_CLIENT_SECRET")

    refresh_token = decrypt(refresh_token_enc)
    resp = httpx.post(
        LWA_TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
            "client_id":     resolved_client_id,
            "client_secret": resolved_client_secret,
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

    Reads client_id / client_secret from the connection row first,
    falling back to environment variables.

    Automatically refreshes if within _REFRESH_BUFFER_MINUTES of expiry.
    Mutates connection.sp_access_token_enc and connection.sp_access_token_expires_at.
    Caller must persist: `db.add(conn); await db.commit()`.
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
        # Resolve client credentials from DB row, fall back to env vars
        client_secret = None
        if connection.sp_client_secret_enc:
            try:
                client_secret = decrypt(connection.sp_client_secret_enc)
            except Exception:
                pass
        token_data = refresh_access_token(
            connection.sp_refresh_token_enc,
            client_id=connection.sp_client_id or None,
            client_secret=client_secret,
        )
        connection.sp_access_token_enc = encrypt(token_data["access_token"])
        connection.sp_access_token_expires_at = (
            datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
        )

    return decrypt(connection.sp_access_token_enc)
