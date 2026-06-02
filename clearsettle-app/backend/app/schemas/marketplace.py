"""
Pydantic v2 schemas for the Marketplace Integration Framework.

All request/response models live here.
Sensitive credentials (tokens, secrets) are never included in response models.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Marketplace registry schemas ──────────────────────────────────────────────

class MarketplaceOut(BaseModel):
    id:                        UUID
    name:                      str
    slug:                      str
    connection_type:           str
    description:               Optional[str]
    website_url:               Optional[str]
    docs_url:                  Optional[str]
    logo_url:                  Optional[str]
    is_active:                 bool
    is_live:                   bool
    required_credential_fields: Optional[list[str]]
    oauth_scopes:              Optional[str]
    region_support:            Optional[dict[str, str]]
    sort_order:                int

    model_config = {"from_attributes": True}


# ── Connection schemas ────────────────────────────────────────────────────────

class MarketplaceConnectionOut(BaseModel):
    """Public view of a connection — NO sensitive credential data."""
    id:               UUID
    marketplace_id:   UUID
    marketplace:      MarketplaceOut
    connection_type:  str
    status:           str
    display_name:     Optional[str]
    seller_name:      Optional[str]
    seller_email:     Optional[str]
    seller_id:        Optional[str]
    region:           Optional[str]
    shop_domain:      Optional[str]
    # Sync summary
    last_sync_at:     Optional[datetime]
    last_sync_status: Optional[str]
    last_sync_error:  Optional[str]
    total_syncs:      int
    # Lifecycle
    connected_at:    Optional[datetime]
    created_at:      datetime
    updated_at:      datetime
    # Credential presence (never plaintext)
    has_credentials: bool = False
    credential_display: Optional[str] = None  # masked api_key display

    model_config = {"from_attributes": True}


class MarketplaceConnectionListResponse(BaseModel):
    items:      list[MarketplaceConnectionOut]
    total:      int
    connected:  int
    error:      int


# ── OAuth flow schemas ────────────────────────────────────────────────────────

class OAuthInitRequest(BaseModel):
    """Client sends this to start an OAuth flow."""
    marketplace_slug: str
    redirect_uri:     Optional[str] = None
    shop_domain:      Optional[str] = None
    # Shopify requires the shop subdomain upfront

    @field_validator("marketplace_slug")
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower().strip()


class OAuthInitResponse(BaseModel):
    """Returned after creating the OAuth state — client should redirect here."""
    authorization_url: str
    state:             str
    expires_at:        datetime


class OAuthCallbackRequest(BaseModel):
    """Body sent by the client after the OAuth provider redirects back."""
    code:         str
    state:        str
    marketplace_slug: str
    shop:         Optional[str] = None  # Shopify passes the shop subdomain


class OAuthCallbackResponse(BaseModel):
    connection: MarketplaceConnectionOut
    message:    str


# ── API-key / credential connect schemas ──────────────────────────────────────

class CredentialConnectRequest(BaseModel):
    """Payload for connecting non-OAuth platforms."""
    marketplace_slug: str
    credentials:      dict[str, str] = Field(
        ...,
        description="Key-value credential map (api_key, api_secret, store_url, etc.)"
    )
    display_name:     Optional[str] = None

    @field_validator("credentials")
    @classmethod
    def credentials_not_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("credentials must not be empty")
        return v


# ── Manual upload schema ──────────────────────────────────────────────────────

class ManualConnectionRequest(BaseModel):
    """For manual-upload marketplaces — just creates the connection row."""
    marketplace_slug: str
    display_name:     Optional[str] = None


# ── Sync schemas ──────────────────────────────────────────────────────────────

class SyncRequest(BaseModel):
    sync_type: str = "full"
    date_from: Optional[datetime] = None
    date_to:   Optional[datetime] = None

    @field_validator("sync_type")
    @classmethod
    def valid_sync_type(cls, v: str) -> str:
        valid = {"orders", "settlements", "fees", "taxes", "inventory", "reports", "full"}
        if v not in valid:
            raise ValueError(f"sync_type must be one of: {', '.join(sorted(valid))}")
        return v


class SyncJobOut(BaseModel):
    id:            UUID
    connection_id: UUID
    sync_type:     str
    status:        str
    triggered_by:  Optional[str]
    date_from:     Optional[datetime]
    date_to:       Optional[datetime]
    started_at:    Optional[datetime]
    completed_at:  Optional[datetime]
    items_synced:  int
    items_failed:  int
    error_message: Optional[str]
    created_at:    datetime

    model_config = {"from_attributes": True}


class SyncJobListResponse(BaseModel):
    items: list[SyncJobOut]
    total: int


# ── Account schemas ───────────────────────────────────────────────────────────

class MarketplaceAccountOut(BaseModel):
    account_id:       Optional[str]
    account_name:     Optional[str]
    account_email:    Optional[str]
    account_type:     Optional[str]
    region:           Optional[str]
    country:          Optional[str]
    currency:         Optional[str]
    last_verified_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Validation / test schemas ─────────────────────────────────────────────────

class ConnectionCheckResult(BaseModel):
    name:   str
    passed: bool
    detail: Optional[str] = None


class ValidateConnectionResponse(BaseModel):
    is_valid: bool
    message:  str
    checks:   list[ConnectionCheckResult]
    error:    Optional[str] = None


# ── Audit log schemas ─────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id:            UUID
    action:        str
    performed_by:  Optional[UUID]
    created_at:    datetime
    new_value:     Optional[dict[str, Any]]

    model_config = {"from_attributes": True}


# ── Admin schemas ─────────────────────────────────────────────────────────────

class AdminConnectionListResponse(BaseModel):
    """Super-admin view — includes company info."""
    items: list[dict[str, Any]]
    total: int


class DisconnectResponse(BaseModel):
    message:          str
    marketplace_slug: str
    status:           str
