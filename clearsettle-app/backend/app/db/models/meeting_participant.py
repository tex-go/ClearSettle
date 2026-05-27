import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (
        UniqueConstraint("meeting_id", "email", name="uq_meeting_participant"),
    )

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(PG_UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    email = Column(String(255), nullable=False)
    name  = Column(String(255), nullable=True)
    role  = Column(String(50),  nullable=False, default="required")
    # organizer / required / optional

    rsvp_status  = Column(String(50),  nullable=False, default="pending")
    # pending / accepted / declined / tentative
    responded_at = Column(DateTime, nullable=True)
    notes        = Column(Text,     nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="participants")
