"""
Google ID Token verification.

Flow (mobile):
  1. Flutter google_sign_in authenticates the user
  2. google_sign_in.authentication.idToken is sent to POST /auth/google
  3. Backend verifies the token with Google's public keys
  4. Returns a SocialProfile from the verified claims

The ID token is a JWT signed by Google.  We use google-auth to verify it
against Google's public keys, which are cached automatically.

Requirements:
  pip install google-auth>=2.0.0

Environment:
  GOOGLE_CLIENT_ID — your OAuth 2.0 Client ID from Google Cloud Console
                     Must match the clientId used in the Flutter app.
                     Can be a comma-separated list for multiple platforms
                     (e.g. "web_client_id,android_client_id,ios_client_id").
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Google Client IDs — load from environment
# Format: comma-separated list of valid client IDs
_GOOGLE_CLIENT_IDS = [
    cid.strip()
    for cid in os.environ.get("GOOGLE_CLIENT_ID", "").split(",")
    if cid.strip()
]


@dataclass
class GoogleProfile:
    sub: str              # stable Google user ID
    email: str
    email_verified: bool
    name: Optional[str]
    picture: Optional[str]
    given_name: Optional[str]
    family_name: Optional[str]
    locale: Optional[str]
    hd: Optional[str]     # hosted domain (Google Workspace accounts)


async def verify_google_token(id_token: str) -> GoogleProfile:
    """
    Verify a Google ID token and return the decoded profile.

    Raises:
        ValueError — if GOOGLE_CLIENT_ID is not configured
        google.auth.exceptions.GoogleAuthError — if token is invalid / expired
    """
    if not _GOOGLE_CLIENT_IDS:
        raise ValueError(
            "GOOGLE_CLIENT_ID environment variable not set. "
            "Set it to your OAuth 2.0 Client ID from Google Cloud Console."
        )

    try:
        from google.oauth2 import id_token as google_id_token
        import urllib.request
    except ImportError:
        raise RuntimeError(
            "google-auth is not installed. Run: pip install google-auth>=2.0.0"
        )

    # Use stdlib urllib transport — avoids requiring the `requests` package.
    # google-auth's transport interface expects __call__ to return a response
    # object with .status (int), .headers (dict), and .data (bytes).
    class _Response:
        def __init__(self, status, headers, data):
            self.status = status
            self.headers = headers
            self.data = data

    class _UrllibRequest:
        """Minimal google-auth transport using stdlib urllib (no extra deps)."""
        def __call__(self, url, method="GET", body=None, headers=None, timeout=30, **_):
            req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return _Response(resp.status, dict(resp.headers), resp.read())

    # Try each client ID (handles web + Android + iOS client IDs)
    last_exc: Exception = ValueError("No client IDs configured")
    for client_id in _GOOGLE_CLIENT_IDS:
        try:
            idinfo = google_id_token.verify_oauth2_token(
                id_token,
                _UrllibRequest(),
                client_id,
            )

            if not idinfo.get("email"):
                raise ValueError("Google token does not contain email address")

            logger.info(
                "Google token verified",
                extra={
                    "google_sub": idinfo["sub"],
                    "email": idinfo["email"],
                    "email_verified": idinfo.get("email_verified", False),
                },
            )

            return GoogleProfile(
                sub            = idinfo["sub"],
                email          = idinfo["email"].lower().strip(),
                email_verified = idinfo.get("email_verified", False),
                name           = idinfo.get("name"),
                picture        = idinfo.get("picture"),
                given_name     = idinfo.get("given_name"),
                family_name    = idinfo.get("family_name"),
                locale         = idinfo.get("locale"),
                hd             = idinfo.get("hd"),
            )
        except Exception as exc:
            last_exc = exc
            continue

    logger.warning(
        "Google token verification failed",
        extra={"error": str(last_exc)[:200]},
    )
    raise last_exc
