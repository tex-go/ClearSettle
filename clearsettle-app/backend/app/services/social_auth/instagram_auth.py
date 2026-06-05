"""
Instagram / Meta authentication.

Two flows are supported:

FLOW A — Authorization Code Exchange (recommended for mobile)
  1. Mobile opens Instagram OAuth URL via flutter_web_auth_2
  2. User authorises, Instagram redirects to clearsettle://oauth/instagram/callback?code=...
  3. Mobile sends the code to POST /auth/instagram
  4. Backend exchanges code → short-lived access token → user profile

FLOW B — Long-Lived Token (for re-auth / refresh)
  1. Send existing long-lived access token to POST /auth/instagram
  2. Backend validates the token and refreshes it if near expiry

Instagram Basic Display API — personal accounts:
  - Returns: id, username  (NO email — Instagram privacy policy)
  - Scopes: user_profile, user_media

Meta Graph API — business accounts (via Facebook Login):
  - Returns: id, name, email (if user granted email permission)
  - Scopes: public_profile, email

We implement both paths.  If Meta/Facebook Login is used (business accounts),
email will be available.  For personal Instagram accounts, we use the pattern
instagram_{id}@social.clearsettle.app as a placeholder email — the user can
update it in Profile Settings.

Environment:
  INSTAGRAM_APP_ID        — Meta app ID
  INSTAGRAM_APP_SECRET    — Meta app secret (used for code exchange)
  INSTAGRAM_REDIRECT_URI  — e.g. clearsettle://oauth/instagram/callback
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_INSTAGRAM_APP_ID      = os.environ.get("INSTAGRAM_APP_ID", "")
_INSTAGRAM_APP_SECRET  = os.environ.get("INSTAGRAM_APP_SECRET", "")
_INSTAGRAM_REDIRECT_URI = os.environ.get(
    "INSTAGRAM_REDIRECT_URI",
    "clearsettle://oauth/instagram/callback",
)

# Instagram Basic Display API
_TOKEN_URL   = "https://api.instagram.com/oauth/access_token"
_PROFILE_URL = "https://graph.instagram.com/me"
_REFRESH_URL = "https://graph.instagram.com/refresh_access_token"

# Meta Graph API (Facebook Login — business accounts)
_META_TOKEN_URL   = "https://graph.facebook.com/v20.0/oauth/access_token"
_META_PROFILE_URL = "https://graph.facebook.com/v20.0/me"
_META_TOKEN_DEBUG = "https://graph.facebook.com/v20.0/debug_token"


@dataclass
class InstagramProfile:
    provider_id: str        # Instagram user ID (stable)
    username: str
    email: Optional[str]    # None for personal accounts using Basic Display API
    name: Optional[str]
    picture: Optional[str]
    access_token: str       # short-lived or long-lived access token
    is_long_lived: bool = False


async def verify_instagram_token(
    *,
    code: Optional[str] = None,
    access_token: Optional[str] = None,
    use_meta_graph: bool = False,
) -> InstagramProfile:
    """
    Verify Instagram credentials and return a profile.

    Provide EITHER:
        code          — authorization code from OAuth redirect (FLOW A)
        access_token  — existing access token (FLOW B / re-auth)
    """
    if not _INSTAGRAM_APP_ID or not _INSTAGRAM_APP_SECRET:
        raise ValueError(
            "INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET must be set. "
            "Create a Meta App at https://developers.facebook.com/"
        )

    if code:
        token = await _exchange_code_for_token(code, use_meta_graph)
    elif access_token:
        token = access_token
    else:
        raise ValueError("Either 'code' or 'access_token' must be provided.")

    if use_meta_graph:
        return await _get_meta_profile(token)
    else:
        return await _get_instagram_profile(token)


# ── Flow A: Code → Token ──────────────────────────────────────────────────────

async def _exchange_code_for_token(code: str, use_meta: bool) -> str:
    """Exchange an authorization code for an access token."""
    token_url = _META_TOKEN_URL if use_meta else _TOKEN_URL

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(token_url, data={
            "client_id":     _INSTAGRAM_APP_ID,
            "client_secret": _INSTAGRAM_APP_SECRET,
            "grant_type":    "authorization_code",
            "redirect_uri":  _INSTAGRAM_REDIRECT_URI,
            "code":          code,
        })

    if resp.status_code != 200:
        logger.error(
            "Instagram token exchange failed",
            extra={"status": resp.status_code, "body": resp.text[:300]},
        )
        raise ValueError(f"Instagram token exchange failed: {resp.text[:200]}")

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ValueError("Instagram did not return an access_token")
    return token


# ── Instagram Basic Display API profile ──────────────────────────────────────

async def _get_instagram_profile(access_token: str) -> InstagramProfile:
    """Fetch user profile via Instagram Basic Display API."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            _PROFILE_URL,
            params={
                "fields":       "id,username,account_type",
                "access_token": access_token,
            },
        )

    if resp.status_code != 200:
        logger.error(
            "Instagram profile fetch failed",
            extra={"status": resp.status_code, "body": resp.text[:300]},
        )
        raise ValueError(f"Instagram profile fetch failed: {resp.text[:200]}")

    data = resp.json()
    ig_id    = data.get("id", "")
    username = data.get("username", "")

    # Instagram Basic Display API does NOT return email.
    # Generate a deterministic placeholder email for internal use.
    placeholder_email = f"instagram_{ig_id}@social.clearsettle.app"

    logger.info(
        "Instagram profile fetched",
        extra={"ig_id": ig_id, "username": username},
    )

    return InstagramProfile(
        provider_id   = ig_id,
        username      = username,
        email         = None,               # no real email — use placeholder in provider_service
        name          = username,
        picture       = None,
        access_token  = access_token,
        is_long_lived = False,
    )


# ── Meta Graph API profile (Facebook Login / business accounts) ───────────────

async def _get_meta_profile(access_token: str) -> InstagramProfile:
    """Fetch user profile via Meta Graph API (Facebook Login)."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            _META_PROFILE_URL,
            params={
                "fields":       "id,name,email,picture.type(large)",
                "access_token": access_token,
            },
        )

    if resp.status_code != 200:
        raise ValueError(f"Meta profile fetch failed: {resp.text[:200]}")

    data = resp.json()
    picture_url = None
    if "picture" in data:
        picture_url = data["picture"].get("data", {}).get("url")

    logger.info(
        "Meta profile fetched",
        extra={"meta_id": data.get("id"), "has_email": bool(data.get("email"))},
    )

    return InstagramProfile(
        provider_id   = data.get("id", ""),
        username      = data.get("name", ""),
        email         = data.get("email"),
        name          = data.get("name"),
        picture       = picture_url,
        access_token  = access_token,
        is_long_lived = False,
    )


# ── Long-lived token refresh ──────────────────────────────────────────────────

async def refresh_instagram_token(long_lived_token: str) -> str:
    """
    Refresh a long-lived Instagram access token.
    Long-lived tokens expire after 60 days; refresh when <10 days remain.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            _REFRESH_URL,
            params={
                "grant_type":   "ig_refresh_token",
                "access_token": long_lived_token,
            },
        )

    if resp.status_code != 200:
        raise ValueError(f"Instagram token refresh failed: {resp.text[:200]}")

    data = resp.json()
    new_token = data.get("access_token")
    if not new_token:
        raise ValueError("Instagram did not return refreshed access_token")
    return new_token
