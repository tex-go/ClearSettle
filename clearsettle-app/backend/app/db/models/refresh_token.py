import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class RefreshToken(Base):
    """
    Persisted refresh tokens for JWT rotation.

    Security design:
      - Plaintext token is NEVER stored.
      - We store SHA-256(token) in token_hash (unique index).
      - On use: revoke the old row, issue a new one (token rotation).
      - On logout: revoke all tokens for the user.

    A revoked or expired token is rejected immediately without hitting the DB
    once we implement a Redis deny-list; for now a simple DB lookup suffices.
    """
    __tablename__ = "refresh_tokens"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id    = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked    = Column(Boolean, default=False, nullable=False)

    # Optional audit fields
    user_agent = Column(Text)
    ip_address = Column(String(45))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
