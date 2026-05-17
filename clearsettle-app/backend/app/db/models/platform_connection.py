import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class PlatformConnection(Base, TimestampMixin):
    """
    One row per (company, platform) pair.

    Credential columns ending in _enc are Fernet-encrypted at the application
    layer before being written.  Decrypt with app.core.crypto.decrypt().

    Status lifecycle:
        disconnected → oauth_pending → connected → error | disconnected
    """
    __tablename__ = "platform_connections"
    __table_args__ = (
        UniqueConstraint("company_id", "platform", name="uq_company_platform"),
    )

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    platform   = Column(String(50), nullable=False)   # amazon | flipkart | meesho | …

    # Connection lifecycle
    status = Column(String(50), default="disconnected", nullable=False, index=True)

    # ── Amazon SP API credentials (sensitive values Fernet-encrypted) ─────────
    sp_client_id           = Column(String(500))
    sp_client_secret_enc   = Column(Text)
    sp_refresh_token_enc   = Column(Text)
    sp_access_token_enc    = Column(Text)
    sp_access_token_expires_at = Column(DateTime)

    # Seller identity
    sp_selling_partner_id  = Column(String(255))
    sp_marketplace_id      = Column(String(50))
    sp_region              = Column(String(10), default="eu")
    sp_endpoint            = Column(String(200), default="https://sellingpartnerapi-eu.amazon.com")

    # CSRF state token used during OAuth; cleared after successful callback
    oauth_state = Column(String(255))

    # Generic fields for non-SP-API platforms (Flipkart, Meesho, etc.)
    api_key_display    = Column(String(50))
    webhook_secret_enc = Column(Text)

    # Sync tracking
    last_sync_at         = Column(DateTime)
    last_sync_error      = Column(Text)
    total_orders_synced  = Column(Integer, default=0)

    # Relationships
    company   = relationship("Company",  back_populates="connections")
    sync_jobs = relationship("SyncJob",  back_populates="connection", cascade="all, delete-orphan", lazy="selectin")
