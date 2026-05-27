"""
Platform-connection schemas and the platform registry.

The registry is the single source of truth for:
  - supported platforms
  - authentication type (oauth2 | api_key)
  - required credential field names
  - display metadata (name, colour)

Adding a new platform = add one entry to PLATFORM_REGISTRY.
No other code changes required until the sync logic is built.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ── Platform registry ─────────────────────────────────────────────────────────

PLATFORM_REGISTRY: dict[str, dict] = {
    "amazon": {
        "name":                 "Amazon India",
        "auth_type":            "oauth2",
        "color":                "#FF9900",
        "sp_api":               True,
        "required_cred_fields": [],          # OAuth — no direct key/secret needed
        "optional_cred_fields": [],
        "description":          "Connect via Amazon Seller Central OAuth",
    },
    "flipkart": {
        "name":                 "Flipkart",
        "auth_type":            "api_key",
        "color":                "#2874F0",
        "sp_api":               False,
        "required_cred_fields": ["api_key", "api_secret"],
        "optional_cred_fields": ["seller_id"],
        "description":          "Flipkart Seller API key + secret",
    },
    "meesho": {
        "name":                 "Meesho",
        "auth_type":            "api_key",
        "color":                "#9B2D8E",
        "sp_api":               False,
        "required_cred_fields": ["api_key"],
        "optional_cred_fields": ["seller_id"],
        "description":          "Meesho Supplier Panel API key",
    },
    "myntra": {
        "name":                 "Myntra",
        "auth_type":            "api_key",
        "color":                "#FF3F6C",
        "sp_api":               False,
        "required_cred_fields": ["api_key", "api_secret"],
        "optional_cred_fields": ["seller_id"],
        "description":          "Myntra Partner API credentials",
    },
    "nykaa": {
        "name":                 "Nykaa",
        "auth_type":            "api_key",
        "color":                "#FC2779",
        "sp_api":               False,
        "required_cred_fields": ["api_key"],
        "optional_cred_fields": ["seller_id"],
        "description":          "Nykaa Seller Panel API key",
    },
    "ajio": {
        "name":                 "AJIO",
        "auth_type":            "api_key",
        "color":                "#D32730",
        "sp_api":               False,
        "required_cred_fields": ["api_key", "seller_id"],
        "optional_cred_fields": ["api_secret"],
        "description":          "AJIO Business Partner credentials",
    },
    "snapdeal": {
        "name":                 "Snapdeal",
        "auth_type":            "api_key",
        "color":                "#E40046",
        "sp_api":               False,
        "required_cred_fields": ["api_key", "api_secret"],
        "optional_cred_fields": ["seller_id"],
        "description":          "Snapdeal Seller Portal API credentials",
    },
    "jiomart": {
        "name":                 "JioMart",
        "auth_type":            "api_key",
        "color":                "#003087",
        "sp_api":               False,
        "required_cred_fields": ["api_key"],
        "optional_cred_fields": ["seller_id"],
        "description":          "JioMart Seller Hub API key",
    },
}

SUPPORTED_PLATFORMS = list(PLATFORM_REGISTRY.keys())


def get_platform_meta(platform: str) -> dict:
    """Return registry entry or a sensible default for unknown platforms."""
    return PLATFORM_REGISTRY.get(platform, {
        "name":                 platform.capitalize(),
        "auth_type":            "api_key",
        "color":                "#6B7280",
        "sp_api":               False,
        "required_cred_fields": ["api_key"],
        "optional_cred_fields": [],
        "description":          "",
    })


# ── Connection request / response schemas ─────────────────────────────────────

class ConnectApiKeyRequest(BaseModel):
    """
    Generic connect payload for API-key platforms.

    `credentials` is a flat dict of field names → values.
    Required fields are validated against the platform registry.
    Example for Flipkart: {"api_key": "FK…", "api_secret": "S…", "seller_id": "123"}
    """
    credentials: dict[str, str]
    seller_id:   Optional[str] = None   # convenience alias (also accepted inside credentials)
    webhook_url: Optional[str] = None

    @field_validator("credentials")
    @classmethod
    def no_empty_values(cls, v: dict) -> dict:
        for key, val in v.items():
            if not val or not val.strip():
                raise ValueError(f"Credential field '{key}' must not be empty")
        return v


class CredentialFieldOut(BaseModel):
    """Masked representation of a single stored credential field."""
    key:          str
    masked_value: str
    present:      bool


class CredentialsOut(BaseModel):
    """Response for GET /{pid}/credentials."""
    platform:    str
    auth_type:   str
    fields:      list[CredentialFieldOut]
    seller_id:   Optional[str] = None
    webhook_url: Optional[str] = None


class ConnectionOut(BaseModel):
    """Full connection representation returned by list and detail endpoints."""
    id:                  str
    platform:            str
    platform_name:       str
    auth_type:           str
    color:               str
    status:              str
    seller_id:           Optional[str] = None
    marketplace_id:      Optional[str] = None
    credentials_present: bool = False
    webhook_url:         Optional[str] = None
    last_sync_at:        Optional[datetime] = None
    last_sync_error:     Optional[str] = None
    total_orders_synced: int = 0
    connection_id:       str               # UUID of the DB row
    key:                 str = ""          # masked api_key_display (frontend compat)
    created_at:          datetime
    updated_at:          datetime


class ConnectionSummary(BaseModel):
    total:        int
    connected:    int
    disconnected: int
    pending:      int
    error:        int
    oauth_pending: int = 0


class ConnectionsResponse(BaseModel):
    items:   list[ConnectionOut]
    summary: ConnectionSummary


# ── Connection test result ────────────────────────────────────────────────────

class CheckResult(BaseModel):
    name:    str
    passed:  bool
    detail:  str


class TestConnectionResult(BaseModel):
    platform:  str
    status:    str    # ok | warning | failed | unconfigured
    message:   str
    checks:    list[CheckResult]


# ── Platform list (no auth required) ─────────────────────────────────────────

class PlatformInfo(BaseModel):
    """Static info about a supported platform (no connection state)."""
    platform:    str
    name:        str
    auth_type:   str
    color:       str
    description: str
    required_fields: list[str]
