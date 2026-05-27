import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class OnboardingEvent(Base):
    """
    Append-only audit log for every notable action during an onboarding session.

    event_type examples:
        session_created | step_started | step_completed | step_failed |
        step_retried | session_completed | session_abandoned |
        validation_passed | validation_failed | sync_triggered | connection_linked
    """
    __tablename__ = "onboarding_events"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("onboarding_sessions.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    event_type  = Column(String(100), nullable=False, index=True)
    step_name   = Column(String(100), nullable=True)   # NULL if session-level event
    description = Column(String(500))
    payload_json = Column(Text)   # arbitrary structured data for the event

    triggered_by = Column(String(50), default="system")   # system | user | api

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    session = relationship("OnboardingSession", back_populates="events")
