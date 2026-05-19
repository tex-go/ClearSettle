import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    parent_meeting_id = Column(PG_UUID(as_uuid=True),
                               ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)

    title        = Column(String(255), nullable=False)
    description  = Column(Text,        nullable=True)
    meeting_type = Column(String(50),  nullable=False, default="internal")
    # internal / external / client / vendor / team

    status   = Column(String(50), nullable=False, default="scheduled", index=True)
    # scheduled / confirmed / cancelled / completed / rescheduled

    start_at = Column(DateTime, nullable=False)
    end_at   = Column(DateTime, nullable=False)
    timezone = Column(String(50), nullable=False, default="Asia/Kolkata")

    location             = Column(String(500),  nullable=True)
    platform             = Column(String(50),   nullable=True)   # teams/zoom/meet/in_person
    platform_meeting_url = Column(String(1000), nullable=True)
    platform_meeting_id  = Column(String(255),  nullable=True)

    organizer_email = Column(String(255), nullable=False)
    organizer_name  = Column(String(255), nullable=True)
    agenda          = Column(Text,        nullable=True)
    recurrence_rule = Column(String(500), nullable=True)   # iCal RRULE

    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    participants   = relationship("MeetingParticipant",  back_populates="meeting",
                                  cascade="all, delete-orphan", lazy="raise")
    notes          = relationship("MeetingNote",         back_populates="meeting",
                                  cascade="all, delete-orphan", lazy="raise")
    reminders      = relationship("MeetingReminder",     back_populates="meeting",
                                  cascade="all, delete-orphan", lazy="raise")
    status_history = relationship("MeetingStatusHistory", back_populates="meeting",
                                  cascade="all, delete-orphan", lazy="raise")
