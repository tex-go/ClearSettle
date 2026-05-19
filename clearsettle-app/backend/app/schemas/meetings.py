"""Pydantic schemas for the Meeting Scheduling API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


VALID_MEETING_TYPES   = {"internal", "external", "client", "vendor", "team"}
VALID_STATUSES        = {"scheduled", "confirmed", "cancelled", "completed", "rescheduled"}
VALID_PLATFORMS       = {"teams", "zoom", "meet", "in_person", "phone", None}
VALID_RSVP_STATUSES   = {"pending", "accepted", "declined", "tentative"}
VALID_PARTICIPANT_ROLES = {"organizer", "required", "optional"}
VALID_NOTE_TYPES      = {"pre_meeting", "action_item", "decision", "general", "follow_up"}
VALID_REMINDER_TYPES  = {"email", "whatsapp", "in_app"}


# ── Participant ───────────────────────────────────────────────────────────────

class ParticipantCreate(BaseModel):
    email: str = Field(..., max_length=255)
    name:  Optional[str] = Field(default=None, max_length=255)
    role:  str = Field(default="required")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in VALID_PARTICIPANT_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_PARTICIPANT_ROLES)}")
        return v


class ParticipantRSVP(BaseModel):
    rsvp_status: str
    notes: Optional[str] = None

    @field_validator("rsvp_status")
    @classmethod
    def validate_rsvp(cls, v):
        if v not in VALID_RSVP_STATUSES:
            raise ValueError(f"rsvp_status must be one of {sorted(VALID_RSVP_STATUSES)}")
        return v


class ParticipantOut(BaseModel):
    id:           str
    meeting_id:   str
    email:        str
    name:         Optional[str]
    role:         str
    rsvp_status:  str
    responded_at: Optional[str]
    notes:        Optional[str]
    created_at:   str


# ── Note ─────────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    note_type: str = Field(default="general")
    content:   str = Field(..., min_length=1, max_length=10000)

    @field_validator("note_type")
    @classmethod
    def validate_note_type(cls, v):
        if v not in VALID_NOTE_TYPES:
            raise ValueError(f"note_type must be one of {sorted(VALID_NOTE_TYPES)}")
        return v


class NoteOut(BaseModel):
    id:         str
    meeting_id: str
    note_type:  str
    content:    str
    created_by: str
    created_at: str


# ── Reminder ──────────────────────────────────────────────────────────────────

class ReminderCreate(BaseModel):
    reminder_type:     str     = Field(..., description="email|whatsapp|in_app")
    minutes_before:    int     = Field(..., ge=1, le=10080, description="Minutes before meeting")
    participant_email: Optional[str] = Field(default=None, max_length=255)

    @field_validator("reminder_type")
    @classmethod
    def validate_reminder_type(cls, v):
        if v not in VALID_REMINDER_TYPES:
            raise ValueError(f"reminder_type must be one of {sorted(VALID_REMINDER_TYPES)}")
        return v


class ReminderOut(BaseModel):
    id:                str
    meeting_id:        str
    participant_email: Optional[str]
    reminder_type:     str
    minutes_before:    int
    scheduled_at:      str
    sent_at:           Optional[str]
    status:            str
    created_at:        str


# ── Meeting ───────────────────────────────────────────────────────────────────

class MeetingCreate(BaseModel):
    title:        str = Field(..., min_length=1, max_length=255)
    description:  Optional[str] = None
    meeting_type: str = Field(default="internal")
    start_at:     datetime
    end_at:       datetime
    timezone:     str = Field(default="Asia/Kolkata", max_length=50)
    location:     Optional[str] = Field(default=None, max_length=500)
    platform:     Optional[str] = Field(default=None, max_length=50)
    platform_meeting_url: Optional[str] = Field(default=None, max_length=1000)
    organizer_email: str = Field(..., max_length=255)
    organizer_name:  Optional[str] = Field(default=None, max_length=255)
    agenda:          Optional[str] = None
    recurrence_rule: Optional[str] = Field(default=None, max_length=500)
    participants:    list[ParticipantCreate] = Field(default_factory=list)
    reminders:       list[ReminderCreate]   = Field(default_factory=list)

    @field_validator("meeting_type")
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_MEETING_TYPES:
            raise ValueError(f"meeting_type must be one of {sorted(VALID_MEETING_TYPES)}")
        return v

    @field_validator("end_at")
    @classmethod
    def validate_end(cls, v, info):
        start = info.data.get("start_at")
        if start and v <= start:
            raise ValueError("end_at must be after start_at")
        return v


class MeetingPatch(BaseModel):
    title:        Optional[str] = Field(default=None, max_length=255)
    description:  Optional[str] = None
    meeting_type: Optional[str] = None
    status:       Optional[str] = None
    start_at:     Optional[datetime] = None
    end_at:       Optional[datetime] = None
    timezone:     Optional[str] = Field(default=None, max_length=50)
    location:     Optional[str] = Field(default=None, max_length=500)
    platform:     Optional[str] = Field(default=None, max_length=50)
    platform_meeting_url: Optional[str] = Field(default=None, max_length=1000)
    organizer_email: Optional[str] = Field(default=None, max_length=255)
    organizer_name:  Optional[str] = Field(default=None, max_length=255)
    agenda:          Optional[str] = None
    status_reason:   Optional[str] = None  # for status change history

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


class MeetingOut(BaseModel):
    id:           str
    company_id:   str
    parent_meeting_id: Optional[str]
    title:        str
    description:  Optional[str]
    meeting_type: str
    status:       str
    start_at:     str
    end_at:       str
    timezone:     str
    location:     Optional[str]
    platform:     Optional[str]
    platform_meeting_url: Optional[str]
    platform_meeting_id:  Optional[str]
    organizer_email: str
    organizer_name:  Optional[str]
    agenda:          Optional[str]
    recurrence_rule: Optional[str]
    created_by:      str
    created_at:      str
    updated_at:      str
    participants:    list[ParticipantOut] = []
    notes:           list[NoteOut]        = []
    reminders:       list[ReminderOut]    = []
    status_history:  list[dict]           = []


# ── Calendar view ─────────────────────────────────────────────────────────────

class CalendarEvent(BaseModel):
    """Compact meeting for calendar grid rendering."""
    id:           str
    title:        str
    meeting_type: str
    status:       str
    start_at:     str
    end_at:       str
    platform:     Optional[str]
    organizer_name: Optional[str]
    participant_count: int
