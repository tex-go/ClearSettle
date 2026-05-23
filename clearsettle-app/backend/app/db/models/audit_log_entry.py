import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.db.base import Base


class AuditLogEntry(Base):
    """
    Immutable audit log.  Written on sensitive events (login, logout,
    password change, invitation, role change, etc.).
    Rows are never updated or deleted; retention is handled by a
    scheduled job / pg_partman partition drop.
    """
    __tablename__ = "audit_log_entries"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Actor — None for system events or unauthenticated requests
    user_id    = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"),
                        nullable=True, index=True)
    action     = Column(String(100), nullable=False, index=True)   # e.g. "auth.login"
    resource   = Column(String(100))                                # e.g. "user", "company"
    resource_id = Column(String(255))                               # UUID or slug of target
    ip_address = Column(String(45))
    user_agent = Column(Text)
    metadata   = Column(JSONB, default=dict)                        # arbitrary extra context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
