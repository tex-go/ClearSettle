"""Detect scheduling conflicts for a proposed meeting time."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant


async def find_conflicts(
    db: AsyncSession,
    company_id: UUID,
    start_at: datetime,
    end_at: datetime,
    *,
    participant_emails: list[str] | None = None,
    exclude_meeting_id: UUID | None = None,
) -> list[dict]:
    """
    Return meetings that overlap with the proposed [start_at, end_at) window.

    Overlap condition: existing.start_at < proposed.end_at AND existing.end_at > proposed.start_at
    """
    filters = [
        Meeting.company_id == company_id,
        Meeting.status.not_in(["cancelled"]),
        Meeting.start_at < end_at,
        Meeting.end_at   > start_at,
    ]
    if exclude_meeting_id:
        filters.append(Meeting.id != exclude_meeting_id)

    result = await db.execute(select(Meeting).where(*filters))
    conflicts = list(result.scalars().all())

    out = []
    for m in conflicts:
        # If emails provided, only flag if there's participant overlap
        if participant_emails:
            pq = await db.execute(
                select(MeetingParticipant).where(
                    MeetingParticipant.meeting_id == m.id,
                    MeetingParticipant.email.in_(participant_emails),
                )
            )
            if not pq.scalars().all():
                continue   # no participant overlap — not a real conflict

        out.append({
            "conflict_meeting_id": str(m.id),
            "title":     m.title,
            "start_at":  m.start_at.isoformat(),
            "end_at":    m.end_at.isoformat(),
            "status":    m.status,
            "organizer": m.organizer_email,
        })

    return out
