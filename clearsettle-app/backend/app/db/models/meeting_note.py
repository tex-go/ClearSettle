import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MeetingNote(Base):
    __tablename__ = "meeting_notes"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(PG_UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    note_type  = Column(String(50), nullable=False, default="general")
    # pre_meeting / action_item / decision / general / follow_up
    content    = Column(Text,        nullable=False)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime,    nullable=False, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="notes")
