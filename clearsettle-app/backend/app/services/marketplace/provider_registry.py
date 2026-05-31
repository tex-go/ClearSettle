"""
Marketplace provider registry.

Maps marketplace slugs to their provider classes.

Adding a new marketplace requires only:
  1. Creating a new provider in app/services/marketplace/providers/
  2. Importing and registering it in PROVIDER_REGISTRY below.
  No other code changes needed.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Type

from app.services.marketplace.abstract_provider import AbstractMarketplaceProvider

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Import providers ──────────────────────────────────────────────────────────

from app.services.marketplace.providers.amazon      import AmazonProvider
from app.services.marketplace.providers.shopify     import ShopifyProvider
from app.services.marketplace.providers.woocommerce import WooCommerceProvider
from app.services.marketplace.providers.flipkart    import FlipkartProvider
from app.services.marketplace.providers.meesho      import MeeshoProvider
from app.services.marketplace.providers.myntra      import MyntraProvider
from app.services.marketplace.providers.ajio        import AjioProvider

# ── Registry ──────────────────────────────────────────────────────────────────

PROVIDER_REGISTRY: dict[str, Type[AbstractMarketplaceProvider]] = {
    "amazon":      AmazonProvider,
    "shopify":     ShopifyProvider,
    "woocommerce": WooCommerceProvider,
    "flipkart":    FlipkartProvider,
    "meesho":      MeeshoProvider,
    "myntra":      MyntraProvider,
    "ajio":        AjioProvider,
}

# ── Public API ────────────────────────────────────────────────────────────────

def get_provider(slug: str) -> AbstractMarketplaceProvider:
    """
    Return an instantiated provider for the given marketplace slug.
    Raises ValueError if the slug is not registered.
    """
    provider_class = PROVIDER_REGISTRY.get(slug)
    if provider_class is None:
        registered = ", ".join(sorted(PROVIDER_REGISTRY.keys()))
        raise ValueError(
            f"No provider registered for marketplace '{slug}'. "
            f"Registered providers: {registered}"
        )
    return provider_class()


def is_supported(slug: str) -> bool:
    """Return True if a provider is registered for this slug."""
    return slug in PROVIDER_REGISTRY


def list_supported_slugs() -> list[str]:
    """Return all registered marketplace slugs."""
    return sorted(PROVIDER_REGISTRY.keys())
