import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SyncJob(Base):
    """
    One row per sync attempt.

    Status lifecycle
    ----------------
    pending → running → completed
                     → failed  (retry_count < max_retries  → re-queued as pending)
                     → failed  (retry_count >= max_retries → terminal)
    cancelled (via API, only from pending state)

    Denormalized columns (company_id, platform) allow dashboard queries without JOIN.

    job_type values:    orders | settlements
    triggered_by values: manual | scheduler | webhook
    """
    __tablename__ = "sync_jobs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    connection_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("platform_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,   # nullable: existing rows pre-005 migration won't have it
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    platform     = Column(String(50), nullable=True, index=True)
    job_type     = Column(String(50), nullable=False)
    triggered_by = Column(String(50), default="manual", nullable=False)

    # ── Status ────────────────────────────────────────────────────────────────
    status = Column(String(50), default="pending", nullable=False, index=True)

    # ── Timing ────────────────────────────────────────────────────────────────
    scheduled_at     = Column(DateTime)   # set by scheduler; NULL = immediate
    started_at       = Column(DateTime)
    completed_at     = Column(DateTime)
    duration_seconds = Column(Float)      # (completed_at - started_at).total_seconds()

    # ── Retry ─────────────────────────────────────────────────────────────────
    retry_count = Column(Integer, default=0,  nullable=False)
    max_retries = Column(Integer, default=3,  nullable=False)

    # ── Results ───────────────────────────────────────────────────────────────
    records_synced  = Column(Integer, default=0)   # kept for backward compat
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    error_message   = Column(Text)

    # ── Options ───────────────────────────────────────────────────────────────
    # JSON: {"days_back": 30, "marketplace_id": "A21TJRUUN4KGV"}
    job_options_json = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    connection = relationship("PlatformConnection", back_populates="sync_jobs")
    logs       = relationship(
        "SyncLog",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
