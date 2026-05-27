"""CRUD helpers for MeetingParticipant."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meeting_participant import MeetingParticipant


async def add_participant(
    db: AsyncSession,
    meeting_id: UUID,
    email: str,
    name: str | None = None,
    role: str = "required",
) -> MeetingParticipant:
    # Upsert: return existing if already present
    existing = await db.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.email      == email,
        )
    )
    p = existing.scalar_one_or_none()
    if p:
        return p

    p = MeetingParticipant(meeting_id=meeting_id, email=email, name=name, role=role)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def update_rsvp(
    db: AsyncSession,
    meeting_id: UUID,
    email: str,
    rsvp_status: str,
    notes: str | None = None,
) -> MeetingParticipant | None:
    result = await db.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.email      == email,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        return None
    p.rsvp_status  = rsvp_status
    p.responded_at = datetime.utcnow()
    if notes:
        p.notes = notes
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def remove_participant(
    db: AsyncSession,
    meeting_id: UUID,
    email: str,
) -> bool:
    result = await db.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.email      == email,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        return False
    await db.delete(p)
    await db.commit()
    return True
