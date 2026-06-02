"""
WooCommerce Marketplace Provider — API Key + Secret (Consumer Key / Consumer Secret).

WooCommerce uses HTTP Basic Auth with Consumer Key as username
and Consumer Secret as password.

The seller provides:
  store_url       : their WooCommerce store URL (e.g. https://mystore.com)
  consumer_key    : WC consumer key (ck_...)
  consumer_secret : WC consumer secret (cs_...)
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.crypto import decrypt, encrypt
from app.services.marketplace.abstract_provider import (
    AbstractMarketplaceProvider,
    AccountDetails,
    ConnectionType,
    OAuthTokens,
    SyncResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class WooCommerceProvider(AbstractMarketplaceProvider):
    """WooCommerce REST API connector via Consumer Key + Consumer Secret."""

    @property
    def marketplace_slug(self) -> str:
        return "woocommerce"

    @property
    def connection_type(self) -> str:
        return ConnectionType.API_KEY_SECRET

    # ── Credential helpers ────────────────────────────────────────────────────

    def _get_auth(self, credentials) -> tuple[str, str]:
        if not credentials.api_key_enc or not credentials.api_secret_enc:
            raise ValueError("WooCommerce consumer key and secret are not stored.")
        return (decrypt(credentials.api_key_enc), decrypt(credentials.api_secret_enc))

    def _get_store_url(self, credentials) -> str:
        import json
        if credentials.extra_enc:
            extra = json.loads(decrypt(credentials.extra_enc))
            return extra.get("store_url", "").rstrip("/")
        raise ValueError("WooCommerce store URL is not stored.")

    # ── API-key connect ───────────────────────────────────────────────────────

    async def handle_credential_connect(
        self,
        raw_credentials: dict[str, str],
        connection,
        credentials,
        **kwargs: Any,
    ) -> None:
        store_url       = raw_credentials.get("store_url", "").rstrip("/")
        consumer_key    = raw_credentials.get("consumer_key", "")
        consumer_secret = raw_credentials.get("consumer_secret", "")

        if not store_url:
            raise ValueError("store_url is required for WooCommerce connections.")
        if not consumer_key or not consumer_secret:
            raise ValueError("consumer_key and consumer_secret are required.")

        # Validate immediately before storing
        api_url = f"{store_url}/wp-json/wc/v3/system_status"
        try:
            resp = httpx.get(
                api_url,
                auth=(consumer_key, consumer_secret),
                timeout=15,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"WooCommerce credential validation failed (HTTP {exc.response.status_code}): "
                "Check your store URL, consumer key, and consumer secret."
            ) from exc
        except httpx.RequestError as exc:
            raise ValueError(
                f"Cannot reach WooCommerce store at {store_url}: {exc}"
            ) from exc

        # Store encrypted
        import json
        credentials.api_key_enc    = encrypt(consumer_key)
        credentials.api_secret_enc = encrypt(consumer_secret)
        credentials.api_key_display = (
            consumer_key[:4] + "****" + consumer_key[-4:]
            if len(consumer_key) > 8 else "****"
        )
        credentials.extra_enc = encrypt(json.dumps({"store_url": store_url}))

        connection.seller_id   = store_url
        connection.shop_domain = store_url.replace("https://", "").replace("http://", "")
        logger.info("WooCommerce credentials validated and stored for store: %s", store_url)

    # ── Validation ────────────────────────────────────────────────────────────

    async def validate_connection(self, connection, credentials) -> ValidationResult:
        checks = []
        try:
            store_url = self._get_store_url(credentials)
            ck, cs    = self._get_auth(credentials)
            resp = httpx.get(
                f"{store_url}/wp-json/wc/v3/system_status",
                auth=(ck, cs),
                timeout=15,
            )
            resp.raise_for_status()
            checks.append({"name": "api_call", "passed": True,
                           "detail": f"Connected to {store_url}"})
        except Exception as exc:
            checks.append({"name": "api_call", "passed": False, "detail": str(exc)})
            return ValidationResult(is_valid=False, message="WooCommerce API call failed",
                                    checks=checks, error=str(exc))

        return ValidationResult(is_valid=True, message="WooCommerce connection is healthy",
                                checks=checks)

    async def get_account_details(self, connection, credentials) -> AccountDetails:
        store_url = self._get_store_url(credentials)
        ck, cs    = self._get_auth(credentials)

        resp = httpx.get(
            f"{store_url}/wp-json/wc/v3/system_status",
            auth=(ck, cs),
            timeout=15,
        )
        resp.raise_for_status()
        data    = resp.json()
        env     = data.get("environment", {})
        site    = data.get("store", {})

        return AccountDetails(
            account_id    = store_url,
            account_name  = env.get("site_url", store_url),
            account_email = None,
            account_type  = "business",
            region        = None,
            country       = site.get("location", {}).get("country"),
            currency      = site.get("currency"),
            raw           = data,
        )

    async def disconnect(self, connection, credentials) -> None:
        logger.info("WooCommerce store %s disconnected.", connection.shop_domain)

    async def start_sync(self, connection, credentials, sync_job) -> SyncResult:
        return SyncResult(
            success  = True,
            message  = "WooCommerce sync framework ready. Data pipeline coming in next session.",
            meta     = {"store": connection.shop_domain},
        )

    # ── OAuth not supported ───────────────────────────────────────────────────

    async def get_authorization_url(self, state, redirect_uri, connection, **kw) -> str:
        raise NotImplementedError("WooCommerce uses API keys, not OAuth.")

    async def handle_callback(self, code, connection, credentials, **kw) -> OAuthTokens:
        raise NotImplementedError("WooCommerce uses API keys, not OAuth.")

    async def refresh_tokens(self, connection, credentials) -> OAuthTokens:
        raise NotImplementedError("WooCommerce uses API keys, not OAuth.")
