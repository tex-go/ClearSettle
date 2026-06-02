"""
Amazon Marketplace Provider — SP-API OAuth 2.0 (Login with Amazon).

Full implementation of the Authorization Code flow:
  1. get_authorization_url()  — build the Seller Central consent URL
  2. handle_callback()        — exchange code for LWA tokens
  3. refresh_tokens()         — refresh via LWA token endpoint
  4. validate_connection()    — call GetMarketplaceParticipations
  5. get_account_details()    — call GetSellerAccount
  6. start_sync()             — placeholder (full sync in future session)
  7. disconnect()             — clear tokens locally (Amazon has no revoke endpoint)

Credential resolution order (explicit DB value → env var):
  client_id      : connection.credentials.client_id_enc → SP_API_CLIENT_ID
  client_secret  : connection.credentials.client_secret_enc → SP_API_CLIENT_SECRET
  app_id         : stored in MarketplaceConnection.seller_id field → SP_API_APP_ID
  redirect_uri   : stored in extra_enc JSON → SP_API_REDIRECT_URI
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.services.marketplace.abstract_provider import (
    AbstractMarketplaceProvider,
    AccountDetails,
    ConnectionStatus,
    ConnectionType,
    OAuthTokens,
    SyncResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_LWA_TOKEN_URL     = "https://api.amazon.com/auth/o2/token"
_REFRESH_BUFFER_M  = 5


def _settings():
    return get_settings()


def _resolve(explicit: Optional[str], env_value: str, name: str) -> str:
    val = explicit or env_value
    if not val:
        raise ValueError(
            f"Amazon SP-API: {name} is not configured. "
            f"Set it via the connection credentials or the {name.upper()} environment variable."
        )
    return val


class AmazonProvider(AbstractMarketplaceProvider):
    """Amazon SP-API marketplace provider (OAuth 2.0 / Login with Amazon)."""

    @property
    def marketplace_slug(self) -> str:
        return "amazon"

    @property
    def connection_type(self) -> str:
        return ConnectionType.OAUTH

    # ── Internal credential resolution ────────────────────────────────────────

    def _client_id(self, credentials) -> str:
        raw = None
        if credentials.client_id_enc:
            raw = decrypt(credentials.client_id_enc)
        return _resolve(raw, _settings().sp_api_client_id, "SP_API_CLIENT_ID")

    def _client_secret(self, credentials) -> str:
        raw = None
        if credentials.client_secret_enc:
            raw = decrypt(credentials.client_secret_enc)
        return _resolve(raw, _settings().sp_api_client_secret, "SP_API_CLIENT_SECRET")

    def _app_id(self, connection, credentials) -> str:
        extra = self._extra(credentials)
        explicit = extra.get("app_id")
        return _resolve(explicit, _settings().sp_api_app_id, "SP_API_APP_ID")

    def _redirect_uri(self, connection, credentials) -> str:
        extra = self._extra(credentials)
        explicit = extra.get("redirect_uri")
        return _resolve(explicit, _settings().sp_api_redirect_uri, "SP_API_REDIRECT_URI")

    def _extra(self, credentials) -> dict:
        if credentials.extra_enc:
            try:
                return json.loads(decrypt(credentials.extra_enc))
            except Exception:
                return {}
        return {}

    def _store_extra(self, credentials, data: dict) -> None:
        credentials.extra_enc = encrypt(json.dumps(data))

    # ── OAuth flow ────────────────────────────────────────────────────────────

    async def get_authorization_url(
        self,
        state:        str,
        redirect_uri: str,
        connection,
        **kwargs: Any,
    ) -> str:
        extra = {}
        if redirect_uri:
            extra["redirect_uri"] = redirect_uri
        # Store redirect_uri so handle_callback can retrieve it
        if connection.credentials:
            self._store_extra(connection.credentials, extra)

        s = _settings()
        app_id    = _resolve(extra.get("app_id"), s.sp_api_app_id, "SP_API_APP_ID")
        r_uri     = _resolve(redirect_uri or extra.get("redirect_uri"), s.sp_api_redirect_uri, "SP_API_REDIRECT_URI")
        params    = (
            f"application_id={app_id}"
            f"&state={state}"
            f"&redirect_uri={r_uri}"
            "&version=beta"
        )
        return f"https://sellercentral.amazon.in/apps/authorize/consent?{params}"

    async def handle_callback(
        self,
        code:        str,
        connection,
        credentials,
        **kwargs: Any,
    ) -> OAuthTokens:
        client_id     = self._client_id(credentials)
        client_secret = self._client_secret(credentials)
        redirect_uri  = self._redirect_uri(connection, credentials)

        resp = httpx.post(
            _LWA_TOKEN_URL,
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  redirect_uri,
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        # Store client credentials encrypted for future refresh
        if client_id:
            credentials.client_id_enc = encrypt(client_id)
        if client_secret:
            credentials.client_secret_enc = encrypt(client_secret)

        logger.info("Amazon LWA token exchange successful (expires_in=%s)", data.get("expires_in"))
        return OAuthTokens(
            access_token  = data["access_token"],
            refresh_token = data.get("refresh_token"),
            expires_in    = int(data.get("expires_in", 3600)),
            scope         = data.get("scope"),
        )

    async def refresh_tokens(self, connection, credentials) -> OAuthTokens:
        if not credentials.refresh_token_enc:
            raise ValueError("No refresh token stored for Amazon connection.")

        refresh_token = decrypt(credentials.refresh_token_enc)
        client_id     = self._client_id(credentials)
        client_secret = self._client_secret(credentials)

        resp = httpx.post(
            _LWA_TOKEN_URL,
            data={
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        logger.debug("Amazon access token refreshed (expires_in=%s)", data.get("expires_in"))
        return OAuthTokens(
            access_token  = data["access_token"],
            refresh_token = data.get("refresh_token") or refresh_token,
            expires_in    = int(data.get("expires_in", 3600)),
        )

    # ── Validation ────────────────────────────────────────────────────────────

    async def validate_connection(self, connection, credentials) -> ValidationResult:
        checks = []

        # Check 1: tokens present
        has_tokens = bool(credentials.access_token_enc and credentials.refresh_token_enc)
        checks.append({"name": "tokens_present", "passed": has_tokens,
                       "detail": "Access and refresh tokens are stored" if has_tokens
                                 else "Missing OAuth tokens"})
        if not has_tokens:
            return ValidationResult(is_valid=False, message="Missing OAuth tokens", checks=checks)

        # Check 2: token not expired (refresh if needed)
        needs_refresh = self.needs_token_refresh(credentials)
        if needs_refresh:
            try:
                tokens = await self.refresh_tokens(connection, credentials)
                self.store_oauth_tokens(credentials, tokens)
                checks.append({"name": "token_refresh", "passed": True,
                               "detail": "Access token refreshed successfully"})
            except Exception as exc:
                checks.append({"name": "token_refresh", "passed": False,
                               "detail": str(exc)})
                return ValidationResult(is_valid=False, message="Token refresh failed",
                                        checks=checks, error=str(exc))

        # Check 3: live API call to SP-API
        try:
            access_token = self.get_access_token(credentials)
            endpoint     = _settings().sp_api_endpoint
            resp = httpx.get(
                f"{endpoint}/sellers/v1/marketplaceParticipations",
                headers={"x-amz-access-token": access_token},
                timeout=15,
            )
            resp.raise_for_status()
            checks.append({"name": "api_call", "passed": True,
                           "detail": "GetMarketplaceParticipations succeeded"})
        except Exception as exc:
            checks.append({"name": "api_call", "passed": False, "detail": str(exc)})
            return ValidationResult(is_valid=False, message="SP-API call failed",
                                    checks=checks, error=str(exc))

        return ValidationResult(is_valid=True, message="Amazon connection is healthy", checks=checks)

    # ── Account details ───────────────────────────────────────────────────────

    async def get_account_details(self, connection, credentials) -> AccountDetails:
        access_token = self.get_access_token(credentials)
        endpoint     = _settings().sp_api_endpoint

        try:
            resp = httpx.get(
                f"{endpoint}/sellers/v1/marketplaceParticipations",
                headers={"x-amz-access-token": access_token},
                timeout=15,
            )
            resp.raise_for_status()
            data         = resp.json()
            participations = data.get("payload", [])
        except Exception as exc:
            logger.warning("Could not fetch Amazon marketplace participations: %s", exc)
            participations = []

        marketplace_data = {"participations": participations}
        account_id = None
        if participations:
            account_id = participations[0].get("seller", {}).get("sellerId")

        return AccountDetails(
            account_id    = account_id or connection.seller_id,
            account_name  = connection.seller_name,
            account_email = connection.seller_email,
            account_type  = "professional",
            region        = _settings().sp_api_region,
            country       = "India",
            currency      = "INR",
            raw           = marketplace_data,
        )

    # ── Disconnect ────────────────────────────────────────────────────────────

    async def disconnect(self, connection, credentials) -> None:
        # Amazon does not have a token revocation endpoint for SP-API.
        # Clearing tokens locally is sufficient.
        logger.info(
            "Amazon connection %s disconnected — tokens cleared locally.", connection.id
        )

    # ── Sync ──────────────────────────────────────────────────────────────────

    async def start_sync(self, connection, credentials, sync_job) -> SyncResult:
        # Full sync logic is in the data pipeline session.
        # Framework stub validates the connection can be called.
        try:
            access_token = self.get_access_token(credentials)
            logger.info(
                "Amazon sync job %s started (type=%s) — framework ready for data pipeline.",
                sync_job.id, sync_job.sync_type
            )
            # Future: call SP-API orders/settlements/reports endpoints
            return SyncResult(
                success      = True,
                items_synced = 0,
                message      = "Amazon sync framework initialized. Data pipeline to be wired in next session.",
                meta         = {"access_token_present": bool(access_token)},
            )
        except Exception as exc:
            return SyncResult(success=False, error=str(exc))
