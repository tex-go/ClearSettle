import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class OnboardingSession(Base, TimestampMixin):
    """
    Top-level onboarding session for a company + platform combination.

    status lifecycle:  created → in_progress → completed
                                            → failed
                                            → abandoned

    current_step: name of the step currently being executed
    completed_at: set when status transitions to 'completed'
    """
    __tablename__ = "onboarding_sessions"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    platform   = Column(String(50),  nullable=False, default="amazon")

    status       = Column(String(30), nullable=False, default="created", index=True)
    current_step = Column(String(100))
    completed_at = Column(DateTime,   nullable=True)

    # Optional FK to the PlatformConnection created during onboarding
    connection_id = Column(PG_UUID(as_uuid=True),
                           ForeignKey("platform_connections.id", ondelete="SET NULL"),
                           nullable=True)

    metadata_json = Column(Text, default="{}")   # extra context (user agent, source, etc.)

    steps       = relationship("OnboardingStep",       back_populates="session",
                               cascade="all, delete-orphan", lazy="raise",
                               order_by="OnboardingStep.step_order")
    events      = relationship("OnboardingEvent",      back_populates="session",
                               cascade="all, delete-orphan", lazy="raise")
    checkpoints = relationship("OnboardingCheckpoint", back_populates="session",
                               cascade="all, delete-orphan", lazy="raise")
