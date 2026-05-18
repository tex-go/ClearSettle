import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class OnboardingCheckpoint(Base):
    """
    Saved state snapshot at a particular step, enabling safe retry/resume.

    Only one checkpoint per (session_id, step_name) is kept — upserted on save.
    data_json holds whatever partial result or state the step needs to resume cleanly.
    """
    __tablename__ = "onboarding_checkpoints"
    __table_args__ = (
        UniqueConstraint("session_id", "step_name", name="uq_oc_session_step"),
    )

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("onboarding_sessions.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    step_name = Column(String(100), nullable=False)
    data_json = Column(Text, nullable=False, default="{}")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    session = relationship("OnboardingSession", back_populates="checkpoints")
