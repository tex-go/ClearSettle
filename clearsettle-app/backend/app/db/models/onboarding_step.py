import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class OnboardingStep(Base):
    """
    One step in an OnboardingSession's 8-step flow.

    step_name values (in order):
        company_profile | marketplace_selection | platform_connection |
        credential_verification | initial_sync | settlement_ingestion |
        reconciliation_activation | dashboard_activation

    status:  pending | in_progress | completed | failed | skipped
    attempt_count: how many times this step has been attempted
    """
    __tablename__ = "onboarding_steps"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("onboarding_sessions.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    step_name     = Column(String(100), nullable=False)
    step_order    = Column(Integer,     nullable=False)
    status        = Column(String(30),  nullable=False, default="pending", index=True)
    attempt_count = Column(Integer,     nullable=False, default=0)

    started_at    = Column(DateTime, nullable=True)
    completed_at  = Column(DateTime, nullable=True)
    error_message = Column(String(500), nullable=True)
    result_json   = Column(Text, nullable=True)   # step-specific output data

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("OnboardingSession", back_populates="steps")
