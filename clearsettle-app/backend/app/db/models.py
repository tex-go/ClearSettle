"""
SQLAlchemy ORM models.

Tables
------
users                  → app users (email + hashed password)
companies              → seller company profile (1 per user for now)
platform_connections   → one row per marketplace per company
                         - stores encrypted SP API credentials
                         - tracks OAuth state, token expiry, sync status
sync_jobs              → audit log of every background sync attempt
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.database import Base

# Use PostgreSQL-native UUID when available; fall back to String(36) for SQLite
def _uuid_col(primary_key=False, foreign_key=None):
    col_args = []
    if foreign_key:
        col_args.append(ForeignKey(foreign_key, ondelete="CASCADE"))
    return Column(
        PG_UUID(as_uuid=True),
        *col_args,
        primary_key=primary_key,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id            = _uuid_col(primary_key=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name          = Column(String(255))
    role          = Column(String(50), default="admin", nullable=False)
    is_active     = Column(Boolean, default=True, nullable=False)

    companies     = relationship("Company", back_populates="user", cascade="all, delete-orphan")


# ── Companies ─────────────────────────────────────────────────────────────────

class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id       = _uuid_col(primary_key=True)
    user_id  = _uuid_col(foreign_key="users.id")
    name     = Column(String(255), nullable=False)
    gstin    = Column(String(20))
    city     = Column(String(100))
    industry = Column(String(100))

    user        = relationship("User", back_populates="companies")
    connections = relationship("PlatformConnection", back_populates="company", cascade="all, delete-orphan")


# ── Platform Connections ──────────────────────────────────────────────────────

class PlatformConnection(Base, TimestampMixin):
    """
    One row per (company, platform) pair.

    Credential columns ending in _enc are Fernet-encrypted at the application
    layer before being written; decrypt with app.core.crypto.decrypt().
    """
    __tablename__ = "platform_connections"
    __table_args__ = (UniqueConstraint("company_id", "platform", name="uq_company_platform"),)

    id         = _uuid_col(primary_key=True)
    company_id = _uuid_col(foreign_key="companies.id")
    platform   = Column(String(50), nullable=False)   # amazon | flipkart | meesho | …

    # Connection lifecycle
    status            = Column(String(50), default="pending", nullable=False)
    # pending | connected | error | disconnected | oauth_pending

    # ── Amazon SP API credentials (all sensitive values are encrypted) ────────
    # Registered LWA app credentials (from developer console — not per-seller)
    sp_client_id      = Column(String(500))             # public, not encrypted
    sp_client_secret_enc = Column(Text)                 # encrypted

    # Per-seller tokens obtained via OAuth
    sp_refresh_token_enc   = Column(Text)               # encrypted; long-lived
    sp_access_token_enc    = Column(Text)               # encrypted; expires in 1h
    sp_access_token_expires_at = Column(DateTime)

    # Seller identity
    sp_selling_partner_id  = Column(String(255))
    sp_marketplace_id      = Column(String(50))
    sp_region              = Column(String(10), default="eu")
    sp_endpoint            = Column(String(200), default="https://sellingpartnerapi-eu.amazon.com")

    # CSRF state token used during OAuth redirect, cleared after callback
    oauth_state       = Column(String(255))

    # Generic API key fields (for non-SP-API platforms)
    api_key_display   = Column(String(50))    # masked display, e.g. "AKID****"
    webhook_secret_enc = Column(Text)

    # Sync tracking
    last_sync_at      = Column(DateTime)
    last_sync_error   = Column(Text)
    total_orders_synced = Column(Integer, default=0)

    company   = relationship("Company", back_populates="connections")
    sync_jobs = relationship("SyncJob", back_populates="connection", cascade="all, delete-orphan")


# ── Sync Jobs ─────────────────────────────────────────────────────────────────

class SyncJob(Base):
    """Audit log for every background sync attempt."""
    __tablename__ = "sync_jobs"

    id            = _uuid_col(primary_key=True)
    connection_id = _uuid_col(foreign_key="platform_connections.id")

    job_type      = Column(String(50), nullable=False)
    # orders | settlements | financial_events | returns | commissions

    status        = Column(String(50), default="pending", nullable=False)
    # pending | running | completed | failed

    started_at    = Column(DateTime)
    completed_at  = Column(DateTime)
    error_message = Column(Text)
    records_synced = Column(Integer, default=0)

    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)

    connection    = relationship("PlatformConnection", back_populates="sync_jobs")
