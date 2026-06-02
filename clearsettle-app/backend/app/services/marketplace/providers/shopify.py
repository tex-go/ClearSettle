"""
Shopify Marketplace Provider — OAuth 2.0.

Shopify OAuth uses a per-store authorization URL:
  https://{shop}.myshopify.com/admin/oauth/authorize

The shop subdomain must be provided when initiating the OAuth flow.
Shopify access tokens do not expire (offline access tokens).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import get_settings
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


def _settings():
    return get_settings()


class ShopifyProvider(AbstractMarketplaceProvider):
    """Shopify store connector via OAuth 2.0."""

    @property
    def marketplace_slug(self) -> str:
        return "shopify"

    @property
    def connection_type(self) -> str:
        return ConnectionType.OAUTH

    def _api_key(self) -> str:
        key = _settings().shopify_api_key
        if not key:
            raise ValueError(
                "SHOPIFY_API_KEY is not configured. "
                "Set it in your environment or .env file."
            )
        return key

    def _api_secret(self) -> str:
        secret = _settings().shopify_api_secret
        if not secret:
            raise ValueError("SHOPIFY_API_SECRET is not configured.")
        return secret

    def _shop_domain(self, connection, kwargs: dict) -> str:
        shop = (
            kwargs.get("shop_domain")
            or kwargs.get("shop")
            or connection.shop_domain
        )
        if not shop:
            raise ValueError(
                "Shopify requires the store domain (e.g. 'mystore.myshopify.com'). "
                "Pass shop_domain when initiating the connection."
            )
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        return shop

    # ── OAuth flow ────────────────────────────────────────────────────────────

    async def get_authorization_url(
        self,
        state:        str,
        redirect_uri: str,
        connection,
        **kwargs: Any,
    ) -> str:
        shop    = self._shop_domain(connection, kwargs)
        scopes  = _settings().shopify_scopes
        api_key = self._api_key()
        r_uri   = redirect_uri or _settings().shopify_redirect_uri

        connection.shop_domain = shop

        return (
            f"https://{shop}/admin/oauth/authorize"
            f"?client_id={api_key}"
            f"&scope={scopes}"
            f"&redirect_uri={r_uri}"
            f"&state={state}"
        )

    async def handle_callback(
        self,
        code:        str,
        connection,
        credentials,
        **kwargs: Any,
    ) -> OAuthTokens:
        shop      = kwargs.get("shop") or connection.shop_domain
        api_key   = self._api_key()
        api_secret = self._api_secret()

        resp = httpx.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id":     api_key,
                "client_secret": api_secret,
                "code":          code,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        # Shopify offline access tokens don't expire
        credentials.client_id_enc     = encrypt(api_key)
        credentials.client_secret_enc = encrypt(api_secret)

        logger.info("Shopify OAuth token exchange successful for shop: %s", shop)
        return OAuthTokens(
            access_token  = data["access_token"],
            refresh_token = None,       # Shopify offline tokens don't refresh
            expires_in    = 315360000,  # 10 years
            scope         = data.get("scope"),
        )

    async def refresh_tokens(self, connection, credentials) -> OAuthTokens:
        # Shopify offline access tokens don't expire or refresh
        raise NotImplementedError(
            "Shopify offline access tokens do not expire. No refresh needed."
        )

    # ── Validation ────────────────────────────────────────────────────────────

    async def validate_connection(self, connection, credentials) -> ValidationResult:
        checks = []
        if not credentials.access_token_enc:
            return ValidationResult(is_valid=False, message="No access token stored", checks=checks)

        try:
            token = decrypt(credentials.access_token_enc)
            shop  = connection.shop_domain
            resp  = httpx.get(
                f"https://{shop}/admin/api/2024-01/shop.json",
                headers={"X-Shopify-Access-Token": token},
                timeout=15,
            )
            resp.raise_for_status()
            checks.append({"name": "api_call", "passed": True, "detail": "Shop endpoint accessible"})
        except Exception as exc:
            checks.append({"name": "api_call", "passed": False, "detail": str(exc)})
            return ValidationResult(is_valid=False, message="Shopify API call failed",
                                    checks=checks, error=str(exc))

        return ValidationResult(is_valid=True, message="Shopify connection is healthy", checks=checks)

    async def get_account_details(self, connection, credentials) -> AccountDetails:
        token = decrypt(credentials.access_token_enc)
        shop  = connection.shop_domain

        resp = httpx.get(
            f"https://{shop}/admin/api/2024-01/shop.json",
            headers={"X-Shopify-Access-Token": token},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("shop", {})

        return AccountDetails(
            account_id    = str(data.get("id")),
            account_name  = data.get("name"),
            account_email = data.get("email"),
            account_type  = "business",
            region        = None,
            country       = data.get("country"),
            currency      = data.get("currency"),
            raw           = data,
        )

    async def disconnect(self, connection, credentials) -> None:
        logger.info("Shopify store %s disconnected.", connection.shop_domain)

    async def start_sync(self, connection, credentials, sync_job) -> SyncResult:
        return SyncResult(
            success  = True,
            message  = "Shopify sync framework ready. Data pipeline coming in next session.",
            meta     = {"shop": connection.shop_domain},
        )
