import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class PasswordResetToken(Base):
    """
    Single-use password reset token.
    Pattern: generate plaintext → email to user → store SHA-256 hash.
    On redemption: hash submitted value → compare → mark used.
    """
    __tablename__ = "password_reset_tokens"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
