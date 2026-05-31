"""
AbstractMarketplaceProvider — the contract every connector must implement.

Design principle
----------------
Adding a new marketplace = create one class that inherits from this ABC.
No existing service, router, or model needs to change.

The framework calls these methods. Providers implement the details.

Connection type matrix
----------------------
OAuth          : get_authorization_url + handle_callback + refresh_tokens
API Key        : store credentials in handle_credential_connect
Manual Upload  : sync delegates to report-upload flow, others raise NotImplemented
Partner API    : provider-specific; implement whatever applies
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Value objects returned by providers ───────────────────────────────────────

@dataclass
class OAuthTokens:
    """Tokens returned from an OAuth token exchange or refresh."""
    access_token: str
    refresh_token: Optional[str]
    expires_in: int                   # seconds
    scope: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def expires_at(self) -> datetime:
        from datetime import timedelta
        return datetime.utcnow() + timedelta(seconds=self.expires_in)


@dataclass
class AccountDetails:
    """Normalised seller account info fetched from the marketplace."""
    account_id:    Optional[str]
    account_name:  Optional[str]
    account_email: Optional[str]
    account_type:  Optional[str]  # individual | professional | business
    region:        Optional[str]
    country:       Optional[str]
    currency:      Optional[str]
    raw:           dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating that a connection is still usable."""
    is_valid:  bool
    message:   str
    checks:    list[dict[str, Any]] = field(default_factory=list)
    error:     Optional[str] = None


@dataclass
class SyncResult:
    """Outcome of a sync operation."""
    success:      bool
    items_synced: int = 0
    items_failed: int = 0
    message:      Optional[str] = None
    error:        Optional[str] = None
    meta:         dict[str, Any] = field(default_factory=dict)


# ── Connection type constants ─────────────────────────────────────────────────

class ConnectionType:
    OAUTH            = "oauth"
    API_KEY          = "api_key"
    API_KEY_SECRET   = "api_key_secret"
    USERNAME_PASSWORD = "username_password"
    MANUAL_UPLOAD    = "manual_upload"
    PARTNER_API      = "partner_api"


class ConnectionStatus:
    DISCONNECTED = "disconnected"
    CONNECTING   = "connecting"
    CONNECTED    = "connected"
    ERROR        = "error"
    SUSPENDED    = "suspended"
    REVOKED      = "revoked"


class SyncType:
    ORDERS      = "orders"
    SETTLEMENTS = "settlements"
    FEES        = "fees"
    TAXES       = "taxes"
    INVENTORY   = "inventory"
    REPORTS     = "reports"
    FULL        = "full"


# ── Abstract base class ───────────────────────────────────────────────────────

class AbstractMarketplaceProvider(ABC):
    """
    Every marketplace connector inherits from this class.

    Implementors MUST provide:
        marketplace_slug   — unique string matching marketplaces.slug
        connection_type    — one of ConnectionType.*
        get_authorization_url — for OAuth providers
        handle_callback       — for OAuth providers
        refresh_tokens        — for OAuth providers
        handle_credential_connect — for API key providers
        validate_connection
        get_account_details
        disconnect
        start_sync

    Non-applicable methods should raise NotImplementedError with a clear message.
    """

    @property
    @abstractmethod
    def marketplace_slug(self) -> str:
        """Unique platform identifier matching marketplaces.slug in the DB."""

    @property
    @abstractmethod
    def connection_type(self) -> str:
        """One of ConnectionType.*"""

    # ── OAuth methods (required for connection_type == 'oauth') ───────────────

    async def get_authorization_url(
        self,
        state: str,
        redirect_uri: str,
        connection,          # MarketplaceConnection ORM object
        **kwargs: Any,
    ) -> str:
        """
        Build the URL the user should be redirected to in order to grant access.
        Only required for OAuth providers.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support OAuth authorization. "
            f"This provider uses connection_type='{self.connection_type}'."
        )

    async def handle_callback(
        self,
        code: str,
        connection,          # MarketplaceConnection ORM object
        credentials,         # MarketplaceCredentials ORM object
        **kwargs: Any,
    ) -> OAuthTokens:
        """
        Exchange an OAuth authorization code for access + refresh tokens.
        Persist encrypted tokens to *credentials* (caller commits).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support OAuth callbacks."
        )

    async def refresh_tokens(
        self,
        connection,    # MarketplaceConnection
        credentials,   # MarketplaceCredentials
    ) -> OAuthTokens:
        """
        Obtain a new access token using the stored refresh token.
        Mutates credentials (caller commits).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support token refresh."
        )

    # ── API-key method (required for api_key / api_key_secret providers) ──────

    async def handle_credential_connect(
        self,
        raw_credentials: dict[str, str],
        connection,    # MarketplaceConnection
        credentials,   # MarketplaceCredentials
        **kwargs: Any,
    ) -> None:
        """
        Validate and store API key credentials.
        Called by the connection service when connection_type != oauth.
        Mutates credentials (caller commits).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not use API key credentials."
        )

    # ── Required for ALL providers ────────────────────────────────────────────

    @abstractmethod
    async def validate_connection(
        self,
        connection,    # MarketplaceConnection
        credentials,   # MarketplaceCredentials
    ) -> ValidationResult:
        """Verify the stored credentials are still valid (live API check)."""

    @abstractmethod
    async def get_account_details(
        self,
        connection,    # MarketplaceConnection
        credentials,   # MarketplaceCredentials
    ) -> AccountDetails:
        """Fetch seller account info from the marketplace."""

    @abstractmethod
    async def disconnect(
        self,
        connection,    # MarketplaceConnection
        credentials,   # MarketplaceCredentials
    ) -> None:
        """
        Revoke access on the marketplace side (if API allows) and clear
        local credentials. Caller is responsible for persisting.
        """

    @abstractmethod
    async def start_sync(
        self,
        connection,    # MarketplaceConnection
        credentials,   # MarketplaceCredentials
        sync_job,      # MarketplaceSyncJob
    ) -> SyncResult:
        """
        Execute the sync. The framework creates the SyncJob row before calling
        this method. Provider should update sync_job.items_synced/items_failed.
        Caller commits after return.
        """

    # ── Optional helpers ──────────────────────────────────────────────────────

    def get_access_token(self, credentials) -> str:
        """
        Decrypt and return the current access token.
        Call refresh_tokens() first if the token is near expiry.
        """
        from app.core.crypto import decrypt
        if not credentials.access_token_enc:
            raise ValueError(
                f"No access token stored for {self.marketplace_slug} connection."
            )
        return decrypt(credentials.access_token_enc)

    def needs_token_refresh(self, credentials, buffer_minutes: int = 5) -> bool:
        """Return True if the access token expires within buffer_minutes."""
        from datetime import timedelta
        if not credentials.access_token_expires_at:
            return True
        return credentials.access_token_expires_at <= (
            datetime.utcnow() + timedelta(minutes=buffer_minutes)
        )

    def store_oauth_tokens(self, credentials, tokens: OAuthTokens) -> None:
        """Encrypt and write OAuthTokens into a credentials ORM object."""
        from app.core.crypto import encrypt
        credentials.access_token_enc        = encrypt(tokens.access_token)
        credentials.access_token_expires_at = tokens.expires_at
        if tokens.refresh_token:
            credentials.refresh_token_enc = encrypt(tokens.refresh_token)
        if tokens.scope:
            credentials.scope = tokens.scope
