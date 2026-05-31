"""AJIO Provider — Manual Report Upload. Future: AJIO Partner API."""
from __future__ import annotations

import logging
from app.services.marketplace.abstract_provider import (
    AbstractMarketplaceProvider, AccountDetails, ConnectionType,
    OAuthTokens, SyncResult, ValidationResult,
)

logger = logging.getLogger(__name__)


class AjioProvider(AbstractMarketplaceProvider):
    @property
    def marketplace_slug(self) -> str:
        return "ajio"

    @property
    def connection_type(self) -> str:
        return ConnectionType.MANUAL_UPLOAD

    async def validate_connection(self, connection, credentials) -> ValidationResult:
        return ValidationResult(
            is_valid=True,
            message="AJIO is connected via manual report upload.",
            checks=[{"name": "manual_upload", "passed": True,
                     "detail": "Upload settlement reports from AJIO Seller Portal."}],
        )

    async def get_account_details(self, connection, credentials) -> AccountDetails:
        return AccountDetails(
            account_id=connection.seller_id, account_name=connection.seller_name or "AJIO Seller",
            account_email=connection.seller_email, account_type="seller",
            region="IN", country="India", currency="INR", raw={},
        )

    async def disconnect(self, connection, credentials) -> None:
        logger.info("AJIO connection %s disconnected.", connection.id)

    async def start_sync(self, connection, credentials, sync_job) -> SyncResult:
        return SyncResult(success=True, message="AJIO uses manual upload.",
                          meta={"upload_required": True})

    async def get_authorization_url(self, state, redirect_uri, connection, **kw) -> str:
        raise NotImplementedError("AJIO currently uses manual upload.")

    async def handle_callback(self, code, connection, credentials, **kw) -> OAuthTokens:
        raise NotImplementedError("AJIO currently uses manual upload.")

    async def refresh_tokens(self, connection, credentials) -> OAuthTokens:
        raise NotImplementedError("AJIO currently uses manual upload.")
