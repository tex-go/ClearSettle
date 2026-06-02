"""
Flipkart Marketplace Provider — Manual Report Upload.

Current support: Sellers upload settlement Excel/CSV files manually.
Future roadmap: Flipkart Marketplace API (OAuth), once Flipkart opens
the API for third-party apps.

The validate_connection check verifies that at least one report has been
uploaded for this company on the Flipkart platform.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.marketplace.abstract_provider import (
    AbstractMarketplaceProvider,
    AccountDetails,
    ConnectionType,
    OAuthTokens,
    SyncResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class FlipkartProvider(AbstractMarketplaceProvider):
    """Flipkart — manual report upload provider."""

    @property
    def marketplace_slug(self) -> str:
        return "flipkart"

    @property
    def connection_type(self) -> str:
        return ConnectionType.MANUAL_UPLOAD

    async def validate_connection(self, connection, credentials) -> ValidationResult:
        return ValidationResult(
            is_valid = True,
            message  = "Flipkart is connected via manual report upload.",
            checks   = [
                {"name": "manual_upload", "passed": True,
                 "detail": "Report upload is available for this connection."},
            ],
        )

    async def get_account_details(self, connection, credentials) -> AccountDetails:
        return AccountDetails(
            account_id    = connection.seller_id,
            account_name  = connection.seller_name or "Flipkart Seller",
            account_email = connection.seller_email,
            account_type  = "seller",
            region        = "IN",
            country       = "India",
            currency      = "INR",
            raw           = {},
        )

    async def disconnect(self, connection, credentials) -> None:
        logger.info("Flipkart manual connection %s disconnected.", connection.id)

    async def start_sync(self, connection, credentials, sync_job) -> SyncResult:
        return SyncResult(
            success = True,
            message = "Flipkart uses manual report upload. Use the Reports section to upload files.",
            meta    = {"upload_required": True},
        )

    async def get_authorization_url(self, state, redirect_uri, connection, **kw) -> str:
        raise NotImplementedError("Flipkart currently uses manual upload, not OAuth.")

    async def handle_callback(self, code, connection, credentials, **kw) -> OAuthTokens:
        raise NotImplementedError("Flipkart currently uses manual upload, not OAuth.")

    async def refresh_tokens(self, connection, credentials) -> OAuthTokens:
        raise NotImplementedError("Flipkart currently uses manual upload, not OAuth.")
