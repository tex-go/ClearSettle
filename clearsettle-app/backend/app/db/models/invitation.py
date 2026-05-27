import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Invitation(Base):
    """
    Team member invitation.
    Org admins invite users by email; invitee clicks a link, creates account,
    and is linked to the company automatically.
    Token pattern: plaintext → email → store SHA-256 hash.
    """
    __tablename__ = "invitations"

    id           = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id   = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    invited_by   = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
                          nullable=True)
    email        = Column(String(255), nullable=False, index=True)
    role         = Column(String(50), default="member", nullable=False)
    token_hash   = Column(String(128), unique=True, nullable=False, index=True)
    expires_at   = Column(DateTime, nullable=False)
    accepted     = Column(Boolean, default=False, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    company    = relationship("Company", foreign_keys=[company_id])
    inviter    = relationship("User",    foreign_keys=[invited_by])
