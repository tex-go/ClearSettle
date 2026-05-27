"""
Meeting Scheduling API

Prefix: /meetings

GET    /meetings               — list meetings (filterable by status, type, date range)
POST   /meetings               — create meeting (+ participants + reminders)
GET    /meetings/{id}          — full detail with participants, notes, history
PATCH  /meetings/{id}          — update title/time/status/etc
DELETE /meetings/{id}          — cancel (sets status=cancelled)

GET    /meetings/{id}/participants       — list participants
POST   /meetings/{id}/participants       — add participant
PATCH  /meetings/{id}/participants/{email}/rsvp  — update RSVP status
DELETE /meetings/{id}/participants/{email}        — remove participant

GET    /meetings/{id}/notes    — list notes
POST   /meetings/{id}/notes    — add note

GET    /meetings/{id}/reminders  — list reminders
POST   /meetings/{id}/reminders  — add reminder

GET    /meetings/calendar      — compact list for calendar grid (CalendarEvent)
GET    /meetings/conflicts      — conflict check without creating
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.schemas.meetings import (
    CalendarEvent,
    MeetingCreate,
    MeetingOut,
    MeetingPatch,
    NoteCreate,
    NoteOut,
    ParticipantCreate,
    ParticipantOut,
    ParticipantRSVP,
    ReminderCreate,
    ReminderOut,
)
from app.services.meetings import calendar_store, conflict_detector, participant_store, reminder_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings", tags=["meetings"])


def _company_id(user) -> UUID:
    cid = getattr(user, "company_id", None)
    if not cid:
        raise HTTPException(status_code=400, detail="User has no associated company")
    return cid


def _user_email(user) -> str:
    return getattr(user, "email", str(user.id))


# ── List + Calendar ───────────────────────────────────────────────────────────

@router.get("", response_model=dict)
async def list_meetings(
    status_filter: str  | None = Query(default=None, alias="status"),
    meeting_type:  str  | None = Query(default=None),
    start_from:    str  | None = Query(default=None, description="ISO datetime"),
    start_to:      str  | None = Query(default=None, description="ISO datetime"),
    page:          int         = Query(default=1, ge=1),
    page_size:     int         = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    sf = datetime.fromisoformat(start_from) if start_from else None
    st = datetime.fromisoformat(start_to)   if start_to   else None

    meetings, total = await calendar_store.list_meetings(
        db, company_id,
        status       = status_filter,
        meeting_type = meeting_type,
        start_from   = sf,
        start_to     = st,
        page         = page,
        page_size    = page_size,
    )
    items = [calendar_store.meeting_to_dict(m) for m in meetings]
    pages = (total + page_size - 1) // page_size
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


@router.get("/calendar", response_model=list[CalendarEvent])
async def calendar_view(
    start_from: str | None = Query(default=None),
    start_to:   str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    sf = datetime.fromisoformat(start_from) if start_from else None
    st = datetime.fromisoformat(start_to)   if start_to   else None

    meetings, _ = await calendar_store.list_meetings(
        db, company_id, start_from=sf, start_to=st, page_size=200
    )
    return [
        {
            "id":           str(m.id),
            "title":        m.title,
            "meeting_type": m.meeting_type,
            "status":       m.status,
            "start_at":     m.start_at.isoformat(),
            "end_at":       m.end_at.isoformat(),
            "platform":     m.platform,
            "organizer_name": m.organizer_name,
            "participant_count": len(m.participants),
        }
        for m in meetings
    ]


@router.get("/conflicts")
async def check_conflicts(
    start_at: str = Query(..., description="ISO datetime"),
    end_at:   str = Query(..., description="ISO datetime"),
    emails:   str | None = Query(default=None, description="Comma-separated participant emails"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    email_list = [e.strip() for e in emails.split(",")] if emails else None
    conflicts = await conflict_detector.find_conflicts(
        db, company_id,
        start_at=datetime.fromisoformat(start_at),
        end_at=datetime.fromisoformat(end_at),
        participant_emails=email_list,
    )
    return {"conflicts": conflicts, "has_conflicts": bool(conflicts)}


# ── Single meeting CRUD ───────────────────────────────────────────────────────

@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    created_by = _user_email(user)
    data = payload.model_dump()
    meeting = await calendar_store.create_meeting(db, company_id, data, created_by=created_by)
    return calendar_store.meeting_to_dict(meeting)


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return calendar_store.meeting_to_dict(meeting)


@router.patch("/{meeting_id}", response_model=MeetingOut)
async def patch_meeting(
    meeting_id: UUID,
    payload: MeetingPatch,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    data = payload.model_dump(exclude_none=True)
    updated = await calendar_store.patch_meeting(db, meeting, data, changed_by=_user_email(user))
    return calendar_store.meeting_to_dict(updated)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_meeting(
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await calendar_store.patch_meeting(
        db, meeting,
        {"status": "cancelled", "status_reason": "Cancelled via API"},
        changed_by=_user_email(user),
    )


# ── Participants ──────────────────────────────────────────────────────────────

@router.get("/{meeting_id}/participants", response_model=list[ParticipantOut])
async def list_participants(
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return [calendar_store.participant_to_dict(p) for p in meeting.participants]


@router.post("/{meeting_id}/participants", response_model=ParticipantOut,
             status_code=status.HTTP_201_CREATED)
async def add_participant(
    meeting_id: UUID,
    payload: ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    p = await participant_store.add_participant(
        db, meeting_id, payload.email, payload.name, payload.role
    )
    return calendar_store.participant_to_dict(p)


@router.patch("/{meeting_id}/participants/{email}/rsvp", response_model=ParticipantOut)
async def update_rsvp(
    meeting_id: UUID,
    email: str,
    payload: ParticipantRSVP,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    p = await participant_store.update_rsvp(
        db, meeting_id, email, payload.rsvp_status, payload.notes
    )
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    return calendar_store.participant_to_dict(p)


@router.delete("/{meeting_id}/participants/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_participant(
    meeting_id: UUID,
    email: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    removed = await participant_store.remove_participant(db, meeting_id, email)
    if not removed:
        raise HTTPException(status_code=404, detail="Participant not found")


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.get("/{meeting_id}/notes", response_model=list[NoteOut])
async def list_notes(
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return [calendar_store.note_to_dict(n) for n in meeting.notes]


@router.post("/{meeting_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def add_note(
    meeting_id: UUID,
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    note = await calendar_store.add_note(
        db, meeting_id, payload.note_type, payload.content, created_by=_user_email(user)
    )
    return calendar_store.note_to_dict(note)


# ── Reminders ─────────────────────────────────────────────────────────────────

@router.get("/{meeting_id}/reminders", response_model=list[ReminderOut])
async def list_reminders(
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return [calendar_store.reminder_to_dict(r) for r in meeting.reminders]


@router.post("/{meeting_id}/reminders", response_model=ReminderOut,
             status_code=status.HTTP_201_CREATED)
async def add_reminder(
    meeting_id: UUID,
    payload: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    _company_id(user)
    meeting = await calendar_store.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    r = await calendar_store.add_reminder(
        db, meeting, payload.reminder_type, payload.minutes_before, payload.participant_email
    )
    return calendar_store.reminder_to_dict(r)
