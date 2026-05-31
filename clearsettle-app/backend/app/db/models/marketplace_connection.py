"""
ORM models for the Marketplace Integration Framework.

Every table created in migration 032 has a corresponding model here.
All models use the shared Base / TimestampMixin from app.db.base.

Credential security rule
------------------------
All sensitive fields end in _enc — they MUST be read/written via
app.core.crypto.{encrypt, decrypt}. Plaintext credentials are never
stored in the database or returned to callers.
"""
import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Marketplace(Base):
    """Static registry of all supported marketplace platforms."""
    __tablename__ = "marketplaces"

    id   = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(50),  nullable=False, unique=True, index=True)
    connection_type = Column(String(50), nullable=False)
    # oauth | api_key | api_key_secret | username_password | manual_upload | partner_api

    description  = Column(Text,        nullable=True)
    website_url  = Column(Text,        nullable=True)
    docs_url     = Column(Text,        nullable=True)
    logo_url     = Column(Text,        nullable=True)
    is_active    = Column(Boolean,     nullable=False, default=True)
    is_live      = Column(Boolean,     nullable=False, default=False)
    # is_live=False  →  "Coming Soon" in the UI

    required_credential_fields = Column(JSONB, nullable=True)
    oauth_scopes    = Column(Text, nullable=True)
    oauth_auth_url  = Column(Text, nullable=True)
    oauth_token_url = Column(Text, nullable=True)
    region_support  = Column(JSONB, nullable=True)
    sort_order      = Column(Integer, nullable=False, default=0)
    meta            = Column(JSONB, nullable=True)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────────
    connections = relationship(
        "MarketplaceConnection",
        back_populates="marketplace",
        lazy="raise",
    )
    oauth_states = relationship(
        "OAuthState",
        back_populates="marketplace",
        lazy="raise",
    )


class MarketplaceConnection(Base, TimestampMixin):
    """
    One row per (company, marketplace) pair.
    Tracks the connection lifecycle and sync history.
    """
    __tablename__ = "marketplace_connections"
    __table_args__ = (
        UniqueConstraint("company_id", "marketplace_id", name="uq_company_marketplace"),
    )

    id             = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id     = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    marketplace_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplaces.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    connection_type = Column(String(50), nullable=False)

    status = Column(String(50), nullable=False, default="disconnected", index=True)
    # disconnected | connecting | connected | error | suspended | revoked

    display_name = Column(String(255), nullable=True)
    seller_name  = Column(String(255), nullable=True)
    seller_email = Column(String(255), nullable=True)
    seller_id    = Column(String(255), nullable=True)
    region       = Column(String(50),  nullable=True)
    shop_domain  = Column(String(255), nullable=True)  # Shopify only

    # ── Sync tracking ──────────────────────────────────────────────────────────
    last_sync_at     = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    last_sync_error  = Column(Text, nullable=True)
    total_syncs      = Column(Integer, nullable=False, default=0)

    # ── Lifecycle ──────────────────────────────────────────────────────────────
    connected_at    = Column(DateTime, nullable=True)
    disconnected_at = Column(DateTime, nullable=True)
    error_message   = Column(Text,     nullable=True)
    deleted_at      = Column(DateTime, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    marketplace  = relationship("Marketplace",  back_populates="connections",   lazy="selectin")
    company      = relationship("Company",      back_populates="mkt_connections", lazy="raise")
    credentials  = relationship(
        "MarketplaceCredentials",
        back_populates="connection",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="raise",
    )
    account      = relationship(
        "MarketplaceAccount",
        back_populates="connection",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="raise",
    )
    sync_jobs    = relationship(
        "MarketplaceSyncJob",
        back_populates="connection",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    audit_logs   = relationship(
        "MarketplaceAuditLog",
        back_populates="connection",
        lazy="raise",
    )


class MarketplaceCredentials(Base, TimestampMixin):
    """
    Encrypted credentials for a marketplace connection.
    Isolated in a dedicated table so access can be audited independently.

    ALL _enc columns are Fernet-encrypted. Never read/write them raw.
    Use app.core.crypto.{encrypt, decrypt}.
    """
    __tablename__ = "marketplace_credentials"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplace_connections.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    # ── Fernet-encrypted fields ────────────────────────────────────────────────
    access_token_enc  = Column(Text, nullable=True)
    refresh_token_enc = Column(Text, nullable=True)
    client_id_enc     = Column(Text, nullable=True)
    client_secret_enc = Column(Text, nullable=True)
    api_key_enc       = Column(Text, nullable=True)
    api_secret_enc    = Column(Text, nullable=True)
    username_enc      = Column(Text, nullable=True)
    password_enc      = Column(Text, nullable=True)
    extra_enc         = Column(Text, nullable=True)
    # JSON blob for platform-specific additional fields

    # ── Expiry ─────────────────────────────────────────────────────────────────
    access_token_expires_at  = Column(DateTime, nullable=True)
    refresh_token_expires_at = Column(DateTime, nullable=True)

    # ── Display (non-sensitive) ────────────────────────────────────────────────
    api_key_display = Column(String(50), nullable=True)   # "FKMT****9ABC"
    scope           = Column(Text,       nullable=True)   # granted OAuth scopes

    # ── Relationship ───────────────────────────────────────────────────────────
    connection = relationship(
        "MarketplaceConnection",
        back_populates="credentials",
    )


class MarketplaceAccount(Base, TimestampMixin):
    """Account information fetched from the marketplace API after successful auth."""
    __tablename__ = "marketplace_accounts"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplace_connections.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    account_id    = Column(String(255), nullable=True)
    account_name  = Column(String(500), nullable=True)
    account_email = Column(String(255), nullable=True)
    account_type  = Column(String(100), nullable=True)
    region        = Column(String(50),  nullable=True)
    country       = Column(String(100), nullable=True)
    currency      = Column(String(10),  nullable=True)
    marketplace_data  = Column(JSONB, nullable=True)  # raw API payload
    last_verified_at  = Column(DateTime, nullable=True)

    connection = relationship("MarketplaceConnection", back_populates="account")


class MarketplaceSyncJob(Base, TimestampMixin):
    """Tracks the lifecycle of a single sync operation."""
    __tablename__ = "marketplace_sync_jobs"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplace_connections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    sync_type    = Column(String(100), nullable=False)
    # orders | settlements | fees | taxes | inventory | reports | full
    status       = Column(String(50),  nullable=False, default="queued", index=True)
    # queued | running | completed | failed | cancelled
    triggered_by = Column(String(255), nullable=True)
    date_from    = Column(DateTime,    nullable=True)
    date_to      = Column(DateTime,    nullable=True)
    started_at   = Column(DateTime,    nullable=True)
    completed_at = Column(DateTime,    nullable=True)
    items_synced = Column(Integer,     nullable=False, default=0)
    items_failed = Column(Integer,     nullable=False, default=0)
    error_message = Column(Text,       nullable=True)
    meta          = Column(JSONB,      nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    connection = relationship("MarketplaceConnection", back_populates="sync_jobs")
    logs       = relationship(
        "MarketplaceSyncLog",
        back_populates="sync_job",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class MarketplaceSyncLog(Base):
    """Structured event log for a sync job. Append-only."""
    __tablename__ = "marketplace_sync_logs"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_job_id   = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplace_sync_jobs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    connection_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplace_connections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    log_level  = Column(String(20),  nullable=False, default="info")
    event      = Column(String(200), nullable=False)
    message    = Column(Text,        nullable=True)
    extra      = Column(JSONB,       nullable=True)
    created_at = Column(DateTime,    nullable=False)

    sync_job = relationship("MarketplaceSyncJob", back_populates="logs")


class OAuthState(Base):
    """
    Short-lived CSRF state tokens for OAuth flows.
    Expires after 10 minutes. Marked used_at on callback.
    """
    __tablename__ = "oauth_states"

    id             = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id     = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    marketplace_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    state_token  = Column(String(255), nullable=False, unique=True, index=True)
    redirect_uri = Column(Text,        nullable=True)
    extra_params = Column(JSONB,       nullable=True)
    expires_at   = Column(DateTime,    nullable=False, index=True)
    used_at      = Column(DateTime,    nullable=True)
    created_at   = Column(DateTime,    nullable=False)

    marketplace = relationship("Marketplace", back_populates="oauth_states")


class MarketplaceAuditLog(Base):
    """Immutable audit trail for marketplace connection events."""
    __tablename__ = "marketplace_audit_logs"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id    = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    connection_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplace_connections.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    performed_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action     = Column(String(200), nullable=False)
    old_value  = Column(JSONB, nullable=True)
    new_value  = Column(JSONB, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text,       nullable=True)
    created_at = Column(DateTime,   nullable=False, index=True)

    connection = relationship("MarketplaceConnection", back_populates="audit_logs")
