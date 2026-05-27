"""
Reminder background scheduler — polls for due reminders and marks them sent.

In this implementation, "sending" is logged only (no actual email/WhatsApp dispatch).
Platform integrations (SMTP, WhatsApp API) can be plugged in to _dispatch().
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meeting_reminder import MeetingReminder

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 60   # check every minute


async def get_due_reminders(
    db: AsyncSession,
    *,
    lookahead_minutes: int = 2,
) -> list[MeetingReminder]:
    """Return pending reminders that are due within the lookahead window."""
    now = datetime.utcnow()
    cutoff = now + timedelta(minutes=lookahead_minutes)
    result = await db.execute(
        select(MeetingReminder)
        .where(
            MeetingReminder.status       == "pending",
            MeetingReminder.scheduled_at <= cutoff,
        )
        .limit(100)
    )
    return list(result.scalars().all())


async def mark_reminder_sent(
    db: AsyncSession,
    reminder: MeetingReminder,
) -> None:
    reminder.status  = "sent"
    reminder.sent_at = datetime.utcnow()
    db.add(reminder)
    await db.commit()


async def mark_reminder_failed(
    db: AsyncSession,
    reminder: MeetingReminder,
    error: str,
) -> None:
    reminder.status        = "failed"
    reminder.error_message = error
    db.add(reminder)
    await db.commit()


async def _dispatch(reminder: MeetingReminder) -> None:
    """
    Placeholder dispatch.  Extend with real integrations here:
      email     → SMTP / SendGrid / SES
      whatsapp  → WhatsApp Business API
      in_app    → WebSocket push or DB notification flag
    """
    logger.info(
        "REMINDER [%s] meeting=%s to=%s type=%s minutes_before=%d",
        reminder.id,
        reminder.meeting_id,
        reminder.participant_email or "all",
        reminder.reminder_type,
        reminder.minutes_before,
    )


async def run_reminder_scheduler() -> None:
    """
    Long-running background coroutine.
    Opens its own DB session on each tick (safe for asyncio task).
    """
    from app.db.database import AsyncSessionLocal

    logger.info("Meeting reminder scheduler started (poll interval=%ds)", _POLL_INTERVAL_SECONDS)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                due = await get_due_reminders(db)
                for reminder in due:
                    try:
                        await _dispatch(reminder)
                        await mark_reminder_sent(db, reminder)
                    except Exception as exc:
                        logger.warning("Reminder dispatch failed: %s — %s", reminder.id, exc)
                        await mark_reminder_failed(db, reminder, str(exc))
        except Exception as exc:
            logger.error("Reminder scheduler tick error: %s", exc)

        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
