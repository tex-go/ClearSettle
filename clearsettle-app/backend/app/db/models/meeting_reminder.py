import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MeetingReminder(Base):
    __tablename__ = "meeting_reminders"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(PG_UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    participant_email = Column(String(255), nullable=True)   # None = all participants
    reminder_type     = Column(String(50),  nullable=False)  # email/whatsapp/in_app
    minutes_before    = Column(Integer,     nullable=False)  # 15, 60, 1440

    scheduled_at = Column(DateTime, nullable=False, index=True)
    sent_at      = Column(DateTime, nullable=True)
    status       = Column(String(50), nullable=False, default="pending")
    # pending / sent / failed / skipped
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="reminders")
