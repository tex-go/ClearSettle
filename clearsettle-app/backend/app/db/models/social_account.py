"""
SocialAccount — one row per (user, identity_provider) pair.

Design principles:
  1. One user can link multiple providers (Google + Instagram + Microsoft).
  2. Adding a new provider (Apple, LinkedIn) requires zero schema changes.
  3. Tokens are Fernet-encrypted at rest; never stored or logged in plaintext.
  4. provider_user_id is the stable identifier from the IdP — email can change.
  5. Duplicate detection: UNIQUE on (provider, provider_user_id).

Future providers to add — just register a new 'provider' string:
  google | instagram | microsoft | apple | linkedin | facebook | github
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SocialAccount(Base):
    """
    One row per (user_id, provider) pair.

    A user may have multiple rows — one per linked identity provider.
    Duplicate login attempts (same provider + provider_user_id) are safe:
    the UNIQUE constraint triggers a lookup instead of an insert.
    """
    __tablename__ = "social_accounts"
    __table_args__ = (
        # Prevent two users from claiming the same IdP account
        UniqueConstraint("provider", "provider_user_id",
                         name="uq_social_provider_user_id"),
        # Fast lookup: find all providers linked to a user
        Index("idx_social_user_provider", "user_id", "provider"),
    )

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identity Provider ─────────────────────────────────────────────────────
    # Values: google | instagram | microsoft | apple | linkedin | facebook | github
    # No enum — new providers are added by deploying new code, not migrations.
    provider            = Column(String(50), nullable=False, index=True)
    provider_user_id    = Column(String(255), nullable=False)   # stable ID from the IdP
    provider_email      = Column(String(320), nullable=True)    # may be None (Instagram Basic API)
    provider_name       = Column(String(255), nullable=True)
    profile_picture_url = Column(Text, nullable=True)
    provider_username   = Column(String(255), nullable=True)    # e.g. Instagram @handle

    # ── Encrypted token storage ───────────────────────────────────────────────
    # All token columns store Fernet-encrypted values (base64url).
    # Use app.core.crypto.encrypt() / decrypt().
    access_token_enc    = Column(Text, nullable=True)
    refresh_token_enc   = Column(Text, nullable=True)
    token_expiry        = Column(DateTime, nullable=True)       # UTC; None = no expiry known
    token_scope         = Column(String(500), nullable=True)    # space-separated scopes

    # ── Metadata ──────────────────────────────────────────────────────────────
    is_primary          = Column(Boolean, nullable=False, default=False)  # preferred login method
    last_used_at        = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at          = Column(DateTime, nullable=False, default=datetime.utcnow,
                                 onupdate=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", back_populates="social_accounts", lazy="raise")
