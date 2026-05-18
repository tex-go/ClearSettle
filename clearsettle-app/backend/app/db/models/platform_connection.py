import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class PlatformConnection(Base, TimestampMixin):
    """
    One row per (company, platform) pair.

    Credential storage strategy
    ---------------------------
    Amazon (OAuth2 / SP API):
        - sp_client_id            → public, stored plaintext
        - sp_client_secret_enc    → Fernet-encrypted
        - sp_refresh_token_enc    → Fernet-encrypted, long-lived
        - sp_access_token_enc     → Fernet-encrypted, 1-hour expiry

    All other platforms (API-key):
        - credentials_enc         → Fernet-encrypted JSON blob
                                    e.g. {"api_key": "...", "api_secret": "..."}
        - api_key_display         → masked display only, e.g. "FKMT****9ABC"

    Column naming convention: columns ending in _enc are always Fernet-encrypted.
    Use app.core.crypto.{encrypt, decrypt} to read/write them.

    Status state machine
    --------------------
    disconnected ──► oauth_pending ──► connected ──► error
         ▲                                  │
         └──────────────────────────────────┘  (disconnect action)
    """
    __tablename__ = "platform_connections"
    __table_args__ = (
        UniqueConstraint("company_id", "platform", name="uq_company_platform"),
    )

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    company_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform = Column(String(50), nullable=False)
    # amazon | flipkart | meesho | myntra | nykaa | ajio | snapdeal | jiomart

    # ── Connection lifecycle ──────────────────────────────────────────────────
    status = Column(String(50), default="disconnected", nullable=False, index=True)
    # disconnected | oauth_pending | connected | error

    # ── Generic credentials (non-Amazon platforms) ────────────────────────────
    # Fernet-encrypted JSON: {"api_key": "...", "api_secret": "...", ...}
    credentials_enc = Column(Text)

    # Masked display value for UI (first 4 + last 4 chars of api_key, rest ****)
    api_key_display = Column(String(50))

    # Generic webhook secret for platforms that push events
    webhook_secret_enc = Column(Text)

    # Webhook callback URL registered with the platform
    webhook_url = Column(String(500))

    # Generic seller / merchant identifier on the platform side
    platform_seller_id = Column(String(255))

    # ── Amazon SP API credentials (Fernet-encrypted) ──────────────────────────
    sp_client_id               = Column(String(500))   # public LWA app ID, not encrypted
    sp_client_secret_enc       = Column(Text)
    sp_refresh_token_enc       = Column(Text)
    sp_access_token_enc        = Column(Text)
    sp_access_token_expires_at = Column(DateTime)

    # Amazon seller identity
    sp_selling_partner_id = Column(String(255))
    sp_marketplace_id     = Column(String(50))
    sp_region             = Column(String(10),  default="eu")
    sp_endpoint           = Column(String(200), default="https://sellingpartnerapi-eu.amazon.com")

    # CSRF state token (OAuth handshake only; cleared after callback)
    oauth_state = Column(String(255))

    # SP API app identity — configurable via UI (POST /sp-api/config)
    # When set, takes precedence over SP_API_APP_ID / SP_API_REDIRECT_URI env vars
    sp_app_id      = Column(String(500), nullable=True)
    sp_redirect_uri = Column(String(500), nullable=True)

    # ── Sync tracking ─────────────────────────────────────────────────────────
    last_sync_at        = Column(DateTime)
    last_sync_error     = Column(Text)
    total_orders_synced = Column(Integer, default=0)

    # Relationships
    company   = relationship("Company",  back_populates="connections")
    sync_jobs = relationship("SyncJob",  back_populates="connection", cascade="all, delete-orphan", lazy="selectin")
