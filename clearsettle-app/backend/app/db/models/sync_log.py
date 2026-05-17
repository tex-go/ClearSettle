import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SyncLog(Base):
    """
    Step-level log entries for a sync job.

    level values: debug | info | warning | error
    context_json: optional JSON with structured data (e.g. {"count": 42, "page": 3})
    """
    __tablename__ = "sync_logs"

    id     = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    job_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("sync_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    level        = Column(String(20), nullable=False)
    message      = Column(Text, nullable=False)
    context_json = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("SyncJob", back_populates="logs")
