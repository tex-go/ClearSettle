"""
SellerLeadActivity CRUD — immutable per-entry audit log.

Each action (note, status change, classify, score, outreach, follow-up, tag)
creates a new row. Rows are never updated or deleted.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.seller_lead_activity import SellerLeadActivity

logger = logging.getLogger(__name__)

_ICONS = {
    "note":          "📝",
    "follow_up":     "📅",
    "call_log":      "📞",
    "email_log":     "✉️",
    "whatsapp_log":  "💬",
    "tag":           "🏷️",
    "status_change": "🔄",
    "classify":      "🤖",
    "score":         "⭐",
    "outreach":      "📤",
}


def activity_to_dict(a: SellerLeadActivity) -> dict:
    return {
        "id":            str(a.id),
        "lead_id":       str(a.lead_id),
        "activity_type": a.activity_type,
        "icon":          _ICONS.get(a.activity_type, "•"),
        "content":       a.content,
        "metadata_json": a.metadata_json,
        "created_by":    a.created_by,
        "created_at":    a.created_at.isoformat() if a.created_at else None,
    }


async def add_activity(
    db: AsyncSession,
    *,
    lead_id:       UUID,
    activity_type: str,
    content:       str | None = None,
    metadata:      dict | None = None,
    created_by:    str,
) -> SellerLeadActivity:
    act = SellerLeadActivity(
        lead_id=lead_id,
        activity_type=activity_type,
        content=content,
        metadata_json=metadata,
        created_by=created_by,
    )
    db.add(act)
    await db.commit()
    await db.refresh(act)
    logger.debug("activity: lead=%s type=%s by=%s", lead_id, activity_type, created_by)
    return act


async def list_activity(
    db:        AsyncSession,
    lead_id:   UUID,
    *,
    page:      int = 1,
    page_size: int = 100,
) -> list[SellerLeadActivity]:
    result = await db.execute(
        select(SellerLeadActivity)
        .where(SellerLeadActivity.lead_id == lead_id)
        .order_by(SellerLeadActivity.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all())
