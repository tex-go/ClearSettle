"""
DiscoveryKeyword CRUD — pure DB helpers, no HTTP.

Keywords are the seed inputs for crawl runs:
  hashtag    — #ethnicwear, #d2cbrand, #shopnow
  competitor — competitor brand Instagram handle to mine followers
  direct     — specific public profile username to scrape
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.seller_lead import DiscoveryKeyword
from app.schemas.seller_discovery import DiscoveryKeywordCreate, DiscoveryKeywordPatch

logger = logging.getLogger(__name__)


# ── Serialisation ─────────────────────────────────────────────────────────────

def _dt(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


def keyword_to_dict(kw: DiscoveryKeyword) -> dict:
    return {
        "id":             str(kw.id),
        "keyword":        kw.keyword,
        "keyword_type":   kw.keyword_type,
        "source":         kw.source,
        "is_active":      kw.is_active,
        "priority":       kw.priority,
        "last_crawled_at":_dt(kw.last_crawled_at),
        "crawl_count":    kw.crawl_count or 0,
        "leads_found":    kw.leads_found or 0,
        "notes":          kw.notes,
        "created_at":     _dt(kw.created_at),
        "updated_at":     _dt(kw.updated_at),
    }


# ── Create ────────────────────────────────────────────────────────────────────

async def create_keyword(
    db: AsyncSession,
    payload: DiscoveryKeywordCreate,
) -> DiscoveryKeyword:
    """Create a new keyword and commit."""
    kw = DiscoveryKeyword(
        keyword=payload.keyword.strip(),
        keyword_type=payload.keyword_type,
        source=payload.source,
        priority=payload.priority,
        notes=payload.notes,
        is_active=True,
        crawl_count=0,
        leads_found=0,
    )
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    logger.info("DiscoveryKeyword created id=%s keyword=%s", kw.id, kw.keyword)
    return kw


# ── Read ──────────────────────────────────────────────────────────────────────

async def get_keyword(db: AsyncSession, keyword_id: UUID) -> DiscoveryKeyword | None:
    result = await db.execute(
        select(DiscoveryKeyword).where(DiscoveryKeyword.id == keyword_id)
    )
    return result.scalar_one_or_none()


# ── Update ────────────────────────────────────────────────────────────────────

async def patch_keyword(
    db: AsyncSession,
    kw: DiscoveryKeyword,
    payload: DiscoveryKeywordPatch,
) -> DiscoveryKeyword:
    """Apply a partial update. Only non-None fields are written."""
    changed = False
    for field, value in payload.model_dump(exclude_none=True).items():
        if getattr(kw, field) != value:
            setattr(kw, field, value)
            changed = True

    if changed:
        kw.updated_at = datetime.utcnow()
        db.add(kw)
        await db.commit()
        await db.refresh(kw)
        logger.info("DiscoveryKeyword patched id=%s fields=%s", kw.id, list(payload.model_fields_set))
    return kw


# ── Mark crawled ──────────────────────────────────────────────────────────────

async def mark_crawled(
    db: AsyncSession,
    kw: DiscoveryKeyword,
    *,
    leads_found: int = 0,
) -> DiscoveryKeyword:
    """
    Update crawl metadata after a discovery job completes.

    Called by the orchestrator at the end of each successful run.
    Increments cumulative leads_found so trending keywords surface naturally.
    """
    kw.last_crawled_at = datetime.utcnow()
    kw.crawl_count     = (kw.crawl_count or 0) + 1
    kw.leads_found     = (kw.leads_found or 0) + leads_found
    kw.updated_at      = datetime.utcnow()
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    logger.info("Keyword %s marked crawled — leads_found=%d", kw.id, leads_found)
    return kw


# ── List ──────────────────────────────────────────────────────────────────────

async def list_keywords(
    db: AsyncSession,
    *,
    source:       str | None = None,
    keyword_type: str | None = None,
    is_active:    bool | None = None,
    page:         int = 1,
    page_size:    int = 50,
) -> tuple[list[DiscoveryKeyword], int]:
    """List keywords with optional filtering. Ordered by priority ASC, then created_at DESC."""
    filters = []
    if source:
        filters.append(DiscoveryKeyword.source == source)
    if keyword_type:
        filters.append(DiscoveryKeyword.keyword_type == keyword_type)
    if is_active is not None:
        filters.append(DiscoveryKeyword.is_active == is_active)

    count_q = select(func.count(DiscoveryKeyword.id))
    if filters:
        count_q = count_q.where(*filters)
    total = (await db.execute(count_q)).scalar_one() or 0

    data_q = select(DiscoveryKeyword)
    if filters:
        data_q = data_q.where(*filters)
    data_q = (
        data_q
        .order_by(DiscoveryKeyword.priority.asc(), DiscoveryKeyword.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(data_q)
    return list(result.scalars().all()), total
