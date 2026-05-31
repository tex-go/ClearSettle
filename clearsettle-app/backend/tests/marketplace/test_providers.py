"""
Unit tests for marketplace providers.

Tests focus on:
  - Provider interface compliance
  - Provider registry correctness
  - Credential storage helpers
  - OAuth URL construction (Amazon, Shopify)
  - WooCommerce credential validation logic
  - Manual upload providers (Flipkart, Meesho, Myntra, AJIO)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.marketplace.abstract_provider import (
    AbstractMarketplaceProvider,
    ConnectionType,
    ConnectionStatus,
    OAuthTokens,
    ValidationResult,
    AccountDetails,
    SyncResult,
)
from app.services.marketplace.provider_registry import (
    get_provider,
    is_supported,
    list_supported_slugs,
    PROVIDER_REGISTRY,
)
from app.services.marketplace.providers.amazon import AmazonProvider
from app.services.marketplace.providers.shopify import ShopifyProvider
from app.services.marketplace.providers.woocommerce import WooCommerceProvider
from app.services.marketplace.providers.flipkart import FlipkartProvider
from app.services.marketplace.providers.meesho import MeeshoProvider
from app.services.marketplace.providers.myntra import MyntraProvider
from app.services.marketplace.providers.ajio import AjioProvider


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_connection(slug="amazon", status="connected", shop_domain=None):
    conn = MagicMock()
    conn.id           = "test-conn-id"
    conn.company_id   = "test-company-id"
    conn.status       = status
    conn.seller_id    = "SELLER123"
    conn.seller_name  = "Test Seller"
    conn.seller_email = "seller@test.com"
    conn.region       = "IN"
    conn.shop_domain  = shop_domain
    conn.marketplace  = MagicMock()
    conn.marketplace.slug = slug
    return conn


def make_credentials(
    *,
    access_token_enc=None,
    refresh_token_enc=None,
    client_id_enc=None,
    client_secret_enc=None,
    api_key_enc=None,
    api_secret_enc=None,
    extra_enc=None,
    expires_at=None,
):
    creds = MagicMock()
    creds.access_token_enc        = access_token_enc
    creds.refresh_token_enc       = refresh_token_enc
    creds.client_id_enc           = client_id_enc
    creds.client_secret_enc       = client_secret_enc
    creds.api_key_enc             = api_key_enc
    creds.api_secret_enc          = api_secret_enc
    creds.extra_enc               = extra_enc
    creds.access_token_expires_at = expires_at or (datetime.utcnow() + timedelta(hours=1))
    return creds


# ── Provider Registry Tests ───────────────────────────────────────────────────

class TestProviderRegistry:
    def test_all_expected_providers_registered(self):
        expected = {"amazon", "shopify", "woocommerce", "flipkart", "meesho", "myntra", "ajio"}
        assert expected.issubset(set(PROVIDER_REGISTRY.keys()))

    def test_get_provider_returns_correct_type(self):
        assert isinstance(get_provider("amazon"),      AmazonProvider)
        assert isinstance(get_provider("shopify"),     ShopifyProvider)
        assert isinstance(get_provider("woocommerce"), WooCommerceProvider)
        assert isinstance(get_provider("flipkart"),    FlipkartProvider)
        assert isinstance(get_provider("meesho"),      MeeshoProvider)
        assert isinstance(get_provider("myntra"),      MyntraProvider)
        assert isinstance(get_provider("ajio"),        AjioProvider)

    def test_get_provider_raises_for_unknown_slug(self):
        with pytest.raises(ValueError, match="No provider registered"):
            get_provider("nonexistent_marketplace")

    def test_is_supported(self):
        assert is_supported("amazon") is True
        assert is_supported("ebay")   is False

    def test_list_supported_slugs(self):
        slugs = list_supported_slugs()
        assert "amazon"      in slugs
        assert "shopify"     in slugs
        assert "woocommerce" in slugs
        assert "flipkart"    in slugs

    def test_all_providers_implement_interface(self):
        for slug, cls in PROVIDER_REGISTRY.items():
            provider = cls()
            assert isinstance(provider, AbstractMarketplaceProvider), \
                f"{cls.__name__} does not extend AbstractMarketplaceProvider"
            assert isinstance(provider.marketplace_slug, str)
            assert isinstance(provider.connection_type, str)
            assert provider.marketplace_slug == slug


# ── Amazon Provider Tests ─────────────────────────────────────────────────────

class TestAmazonProvider:
    def setup_method(self):
        self.provider = AmazonProvider()

    def test_slug_and_type(self):
        assert self.provider.marketplace_slug == "amazon"
        assert self.provider.connection_type  == ConnectionType.OAUTH

    @patch("app.services.marketplace.providers.amazon.get_settings")
    def test_get_authorization_url(self, mock_settings):
        mock_settings.return_value.sp_api_app_id       = "APP_001"
        mock_settings.return_value.sp_api_redirect_uri = "https://callback.test"
        mock_settings.return_value.sp_api_client_id    = "CID"
        mock_settings.return_value.sp_api_client_secret = "SEC"

        conn  = make_connection()
        conn.credentials = make_credentials()

        import asyncio
        url = asyncio.get_event_loop().run_until_complete(
            self.provider.get_authorization_url(
                state        = "test-state-123",
                redirect_uri = "https://callback.test",
                connection   = conn,
            )
        )
        assert "sellercentral.amazon.in" in url
        assert "application_id=APP_001" in url
        assert "state=test-state-123"   in url

    def test_store_oauth_tokens(self):
        from app.core.crypto import encrypt, decrypt
        creds  = make_credentials()
        tokens = OAuthTokens(
            access_token  = "acc_abc123",
            refresh_token = "ref_xyz789",
            expires_in    = 3600,
            scope         = "sellingpartnerapi::orders:read",
        )
        self.provider.store_oauth_tokens(creds, tokens)
        assert creds.access_token_enc is not None
        assert creds.refresh_token_enc is not None

    def test_needs_token_refresh_when_expired(self):
        creds = make_credentials(expires_at=datetime.utcnow() - timedelta(minutes=10))
        assert self.provider.needs_token_refresh(creds) is True

    def test_needs_token_refresh_when_valid(self):
        creds = make_credentials(expires_at=datetime.utcnow() + timedelta(hours=2))
        assert self.provider.needs_token_refresh(creds) is False

    def test_needs_token_refresh_within_buffer(self):
        creds = make_credentials(expires_at=datetime.utcnow() + timedelta(minutes=3))
        assert self.provider.needs_token_refresh(creds, buffer_minutes=5) is True


# ── Shopify Provider Tests ────────────────────────────────────────────────────

class TestShopifyProvider:
    def setup_method(self):
        self.provider = ShopifyProvider()

    def test_slug_and_type(self):
        assert self.provider.marketplace_slug == "shopify"
        assert self.provider.connection_type  == ConnectionType.OAUTH

    @patch("app.services.marketplace.providers.shopify.get_settings")
    def test_get_authorization_url(self, mock_settings):
        mock_settings.return_value.shopify_api_key      = "shopify_api_key_test"
        mock_settings.return_value.shopify_api_secret   = "shopify_secret"
        mock_settings.return_value.shopify_redirect_uri = "https://callback.test"
        mock_settings.return_value.shopify_scopes       = "read_orders,read_finances"

        conn = make_connection("shopify", shop_domain="mystore.myshopify.com")

        import asyncio
        url = asyncio.get_event_loop().run_until_complete(
            self.provider.get_authorization_url(
                state        = "csrf-state",
                redirect_uri = "https://callback.test",
                connection   = conn,
                shop_domain  = "mystore.myshopify.com",
            )
        )
        assert "mystore.myshopify.com" in url
        assert "shopify_api_key_test"  in url
        assert "read_orders"           in url
        assert "csrf-state"            in url

    def test_shop_domain_normalization(self):
        conn   = make_connection("shopify", shop_domain=None)
        # Without .myshopify.com suffix
        domain = self.provider._shop_domain(conn, {"shop_domain": "mystore"})
        assert domain == "mystore.myshopify.com"

    def test_refresh_tokens_raises(self):
        import asyncio
        with pytest.raises(NotImplementedError):
            asyncio.get_event_loop().run_until_complete(
                self.provider.refresh_tokens(None, None)
            )


# ── WooCommerce Provider Tests ────────────────────────────────────────────────

class TestWooCommerceProvider:
    def setup_method(self):
        self.provider = WooCommerceProvider()

    def test_slug_and_type(self):
        assert self.provider.marketplace_slug == "woocommerce"
        assert self.provider.connection_type  == ConnectionType.API_KEY_SECRET

    def test_get_authorization_url_raises(self):
        import asyncio
        with pytest.raises(NotImplementedError):
            asyncio.get_event_loop().run_until_complete(
                self.provider.get_authorization_url("state", "uri", None)
            )

    def test_handle_credential_connect_missing_fields(self):
        import asyncio
        with pytest.raises(ValueError, match="store_url is required"):
            asyncio.get_event_loop().run_until_complete(
                self.provider.handle_credential_connect(
                    {}, MagicMock(), MagicMock()
                )
            )


# ── Manual Upload Provider Tests ──────────────────────────────────────────────

class TestManualUploadProviders:
    @pytest.mark.parametrize("cls,slug", [
        (FlipkartProvider, "flipkart"),
        (MeeshoProvider,   "meesho"),
        (MyntraProvider,   "myntra"),
        (AjioProvider,     "ajio"),
    ])
    def test_slug_and_type(self, cls, slug):
        p = cls()
        assert p.marketplace_slug    == slug
        assert p.connection_type     == ConnectionType.MANUAL_UPLOAD

    @pytest.mark.parametrize("cls", [FlipkartProvider, MeeshoProvider, MyntraProvider, AjioProvider])
    def test_validate_connection_always_valid(self, cls):
        import asyncio
        provider = cls()
        conn     = make_connection(provider.marketplace_slug)
        creds    = make_credentials()
        result   = asyncio.get_event_loop().run_until_complete(
            provider.validate_connection(conn, creds)
        )
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    @pytest.mark.parametrize("cls", [FlipkartProvider, MeeshoProvider, MyntraProvider, AjioProvider])
    def test_start_sync_returns_success(self, cls):
        import asyncio
        provider = cls()
        conn     = make_connection(provider.marketplace_slug)
        creds    = make_credentials()
        job      = MagicMock()
        result   = asyncio.get_event_loop().run_until_complete(
            provider.start_sync(conn, creds, job)
        )
        assert isinstance(result, SyncResult)
        assert result.success is True

    @pytest.mark.parametrize("cls", [FlipkartProvider, MeeshoProvider, MyntraProvider, AjioProvider])
    def test_oauth_methods_raise_not_implemented(self, cls):
        import asyncio
        provider = cls()
        with pytest.raises(NotImplementedError):
            asyncio.get_event_loop().run_until_complete(
                provider.get_authorization_url("state", "uri", None)
            )
