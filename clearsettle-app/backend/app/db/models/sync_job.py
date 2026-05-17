import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SyncJob(Base):
    """
    Audit log for every background sync attempt.

    job_type values: orders | settlements | financial_events | returns | commissions
    status values:   pending | running | completed | failed
    """
    __tablename__ = "sync_jobs"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    connection_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("platform_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_type       = Column(String(50), nullable=False)
    status         = Column(String(50), default="pending", nullable=False, index=True)
    started_at     = Column(DateTime)
    completed_at   = Column(DateTime)
    error_message  = Column(Text)
    records_synced = Column(Integer, default=0)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    connection = relationship("PlatformConnection", back_populates="sync_jobs")
