import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MeetingStatusHistory(Base):
    __tablename__ = "meeting_status_history"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(PG_UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    old_status = Column(String(50),  nullable=True)
    new_status = Column(String(50),  nullable=False)
    changed_by = Column(String(255), nullable=False)
    reason     = Column(Text,        nullable=True)
    changed_at = Column(DateTime,    nullable=False, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="status_history")
