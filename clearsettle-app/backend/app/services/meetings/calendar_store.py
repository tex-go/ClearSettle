"""CRUD for Meeting + related tables."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.meeting import Meeting
from app.db.models.meeting_note import MeetingNote
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.meeting_reminder import MeetingReminder
from app.db.models.meeting_status_history import MeetingStatusHistory

logger = logging.getLogger(__name__)


def _dt(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


def participant_to_dict(p: MeetingParticipant) -> dict:
    return {
        "id":           str(p.id),
        "meeting_id":   str(p.meeting_id),
        "email":        p.email,
        "name":         p.name,
        "role":         p.role,
        "rsvp_status":  p.rsvp_status,
        "responded_at": _dt(p.responded_at),
        "notes":        p.notes,
        "created_at":   _dt(p.created_at),
    }


def note_to_dict(n: MeetingNote) -> dict:
    return {
        "id":         str(n.id),
        "meeting_id": str(n.meeting_id),
        "note_type":  n.note_type,
        "content":    n.content,
        "created_by": n.created_by,
        "created_at": _dt(n.created_at),
    }


def reminder_to_dict(r: MeetingReminder) -> dict:
    return {
        "id":                str(r.id),
        "meeting_id":        str(r.meeting_id),
        "participant_email": r.participant_email,
        "reminder_type":     r.reminder_type,
        "minutes_before":    r.minutes_before,
        "scheduled_at":      _dt(r.scheduled_at),
        "sent_at":           _dt(r.sent_at),
        "status":            r.status,
        "created_at":        _dt(r.created_at),
    }


def status_history_to_dict(h: MeetingStatusHistory) -> dict:
    return {
        "id":         str(h.id),
        "meeting_id": str(h.meeting_id),
        "old_status": h.old_status,
        "new_status": h.new_status,
        "changed_by": h.changed_by,
        "reason":     h.reason,
        "changed_at": _dt(h.changed_at),
    }


def meeting_to_dict(
    m: Meeting,
    *,
    include_relations: bool = True,
) -> dict:
    d: dict = {
        "id":                str(m.id),
        "company_id":        str(m.company_id),
        "parent_meeting_id": str(m.parent_meeting_id) if m.parent_meeting_id else None,
        "title":             m.title,
        "description":       m.description,
        "meeting_type":      m.meeting_type,
        "status":            m.status,
        "start_at":          _dt(m.start_at),
        "end_at":            _dt(m.end_at),
        "timezone":          m.timezone,
        "location":          m.location,
        "platform":          m.platform,
        "platform_meeting_url": m.platform_meeting_url,
        "platform_meeting_id":  m.platform_meeting_id,
        "organizer_email":   m.organizer_email,
        "organizer_name":    m.organizer_name,
        "agenda":            m.agenda,
        "recurrence_rule":   m.recurrence_rule,
        "created_by":        m.created_by,
        "created_at":        _dt(m.created_at),
        "updated_at":        _dt(m.updated_at),
        "participants":      [],
        "notes":             [],
        "reminders":         [],
        "status_history":    [],
    }
    if include_relations:
        try:
            d["participants"]   = [participant_to_dict(p) for p in m.participants]
            d["notes"]          = [note_to_dict(n) for n in m.notes]
            d["reminders"]      = [reminder_to_dict(r) for r in m.reminders]
            d["status_history"] = [status_history_to_dict(h) for h in m.status_history]
        except Exception:
            pass   # lazy="raise" guard
    return d


async def _load_meeting(db: AsyncSession, meeting_id: UUID) -> Meeting | None:
    result = await db.execute(
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(
            selectinload(Meeting.participants),
            selectinload(Meeting.notes),
            selectinload(Meeting.reminders),
            selectinload(Meeting.status_history),
        )
    )
    return result.scalar_one_or_none()


async def create_meeting(
    db: AsyncSession,
    company_id: UUID,
    data: dict[str, Any],
    *,
    created_by: str,
) -> Meeting:
    participants_data = data.pop("participants", [])
    reminders_data    = data.pop("reminders", [])

    meeting = Meeting(
        company_id      = company_id,
        created_by      = created_by,
        organizer_email = data.get("organizer_email", created_by),
        **{k: v for k, v in data.items() if hasattr(Meeting, k) and k not in ("id", "company_id", "created_by")},
    )
    db.add(meeting)
    await db.flush()   # get meeting.id

    # Participants
    for p in participants_data:
        db.add(MeetingParticipant(
            meeting_id = meeting.id,
            email = p.get("email"),
            name  = p.get("name"),
            role  = p.get("role", "required"),
        ))

    # Reminders
    for r in reminders_data:
        scheduled_at = meeting.start_at - __import__("datetime").timedelta(
            minutes=r.get("minutes_before", 15)
        )
        db.add(MeetingReminder(
            meeting_id        = meeting.id,
            reminder_type     = r.get("reminder_type"),
            minutes_before    = r.get("minutes_before", 15),
            participant_email = r.get("participant_email"),
            scheduled_at      = scheduled_at,
        ))

    # Initial status history
    db.add(MeetingStatusHistory(
        meeting_id = meeting.id,
        old_status = None,
        new_status = meeting.status,
        changed_by = created_by,
        reason     = "Meeting created",
    ))

    await db.commit()
    return await _load_meeting(db, meeting.id)


async def get_meeting(db: AsyncSession, meeting_id: UUID) -> Meeting | None:
    return await _load_meeting(db, meeting_id)


async def patch_meeting(
    db: AsyncSession,
    meeting: Meeting,
    data: dict[str, Any],
    *,
    changed_by: str,
) -> Meeting:
    old_status = meeting.status
    status_reason = data.pop("status_reason", None)

    for field, value in data.items():
        if value is not None and hasattr(meeting, field):
            setattr(meeting, field, value)

    if data.get("status") and data["status"] != old_status:
        db.add(MeetingStatusHistory(
            meeting_id = meeting.id,
            old_status = old_status,
            new_status = data["status"],
            changed_by = changed_by,
            reason     = status_reason,
        ))

    meeting.updated_at = datetime.utcnow()
    db.add(meeting)
    await db.commit()
    return await _load_meeting(db, meeting.id)


async def list_meetings(
    db: AsyncSession,
    company_id: UUID,
    *,
    status:  str | None = None,
    meeting_type: str | None = None,
    start_from: datetime | None = None,
    start_to:   datetime | None = None,
    page:      int = 1,
    page_size: int = 20,
) -> tuple[list[Meeting], int]:
    from sqlalchemy import func
    filters = [Meeting.company_id == company_id]
    if status:
        filters.append(Meeting.status == status)
    if meeting_type:
        filters.append(Meeting.meeting_type == meeting_type)
    if start_from:
        filters.append(Meeting.start_at >= start_from)
    if start_to:
        filters.append(Meeting.start_at <= start_to)

    count_q = select(func.count(Meeting.id)).where(*filters)
    total   = (await db.execute(count_q)).scalar_one() or 0

    data_q = (
        select(Meeting)
        .where(*filters)
        .options(
            selectinload(Meeting.participants),
            selectinload(Meeting.notes),
            selectinload(Meeting.reminders),
            selectinload(Meeting.status_history),
        )
        .order_by(Meeting.start_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(data_q)
    return list(result.scalars().all()), total


async def add_note(
    db: AsyncSession,
    meeting_id: UUID,
    note_type: str,
    content: str,
    created_by: str,
) -> MeetingNote:
    note = MeetingNote(
        meeting_id = meeting_id,
        note_type  = note_type,
        content    = content,
        created_by = created_by,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def add_reminder(
    db: AsyncSession,
    meeting: Meeting,
    reminder_type: str,
    minutes_before: int,
    participant_email: str | None = None,
) -> MeetingReminder:
    from datetime import timedelta
    scheduled_at = meeting.start_at - timedelta(minutes=minutes_before)
    reminder = MeetingReminder(
        meeting_id        = meeting.id,
        reminder_type     = reminder_type,
        minutes_before    = minutes_before,
        participant_email = participant_email,
        scheduled_at      = scheduled_at,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder
