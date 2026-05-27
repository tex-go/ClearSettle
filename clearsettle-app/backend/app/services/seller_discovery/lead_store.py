"""
SellerLead CRUD — pure DB helpers, no HTTP.

All functions accept an open AsyncSession and commit where noted.
Callers own the session lifecycle.

Soft delete:
  Leads are never hard-deleted.  DELETE endpoint sets lead_status = 'deleted'.
  All list/search queries exclude status='deleted' automatically.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.seller_lead import SellerLead
from app.schemas.seller_discovery import (
    OutreachPatch,
    ReviewPayload,
    SellerLeadCreate,
    SellerLeadPatch,
)
from app.services.seller_discovery import deduplication

logger = logging.getLogger(__name__)

_SEARCH_COLS = (
    SellerLead.username,
    SellerLead.full_name,
    SellerLead.bio,
    SellerLead.website,
)

_REVIEW_ACTION_MAP = {
    "approve":       "approved",
    "reject":        "rejected",
    "qualify":       "qualified",
    "contact_ready": "contact_ready",
    "review":        "review_pending",
    "contacted":     "contacted",
}


# ── Serialisation helper ──────────────────────────────────────────────────────

def _dt(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


def lead_to_dict(lead: SellerLead) -> dict:
    return {
        # Identity
        "id":                    str(lead.id),
        "job_id":                str(lead.job_id) if lead.job_id else None,
        "username":              lead.username,
        "source":                lead.source,
        "profile_url":           lead.profile_url,
        # Profile
        "full_name":             lead.full_name,
        "bio":                   lead.bio,
        "website":               lead.website,
        "category":              lead.category,
        "profile_image_url":     lead.profile_image_url,
        "followers_count":       lead.followers_count,
        "following_count":       lead.following_count,
        "engagement_rate":       float(lead.engagement_rate)  if lead.engagement_rate  is not None else None,
        # Contact
        "email":                 lead.email,
        "whatsapp":              lead.whatsapp,
        # Geo
        "country":               lead.country,
        "language":              lead.language,
        # AI classification
        "ai_is_ecommerce":       lead.ai_is_ecommerce,
        "ai_relevance_score":    float(lead.ai_relevance_score)  if lead.ai_relevance_score  is not None else None,
        "ai_confidence_score":   float(lead.ai_confidence_score) if lead.ai_confidence_score is not None else None,
        "ai_category":           lead.ai_category,
        "ai_estimated_biz_type": lead.ai_estimated_biz_type,
        "ai_revenue_stage":      lead.ai_revenue_stage,
        "ai_is_india_seller":    lead.ai_is_india_seller,
        "ai_is_fake_account":    lead.ai_is_fake_account,
        "ai_tags_json":          lead.ai_tags_json,
        "ai_outreach_suggestion":lead.ai_outreach_suggestion,
        "ai_classified_at":      _dt(lead.ai_classified_at),
        # Scoring
        "lead_score":            float(lead.lead_score)          if lead.lead_score          is not None else None,
        "score_breakdown_json":  lead.score_breakdown_json,
        "priority_level":        lead.priority_level,
        # Lifecycle
        "lead_status":           lead.lead_status,
        "notes":                 lead.notes,
        "tags_json":             lead.tags_json,
        # Review
        "reviewed_at":           _dt(lead.reviewed_at),
        "reviewed_by":           lead.reviewed_by,
        # Outreach
        "outreach_status":       lead.outreach_status,
        "outreach_notes":        lead.outreach_notes,
        # CRM lifecycle
        "follow_up_at":          _dt(lead.follow_up_at),
        "assigned_to":           lead.assigned_to,
        # Provenance
        "discovery_source":      lead.discovery_source,
        "discovery_keyword":     lead.discovery_keyword,
        "last_scraped_at":       _dt(lead.last_scraped_at),
        "created_at":            _dt(lead.created_at),
        "updated_at":            _dt(lead.updated_at),
    }


# ── Create / upsert ───────────────────────────────────────────────────────────

async def create_or_update_lead(
    db: AsyncSession,
    *,
    data: dict[str, Any],
    job_id: UUID | None = None,
) -> tuple[SellerLead, bool]:
    """
    Upsert a seller lead.

    Returns (lead, created) where created=True means a new row was inserted.
    created=False means an existing lead was refreshed (last_scraped_at updated).

    Dedup is checked BEFORE attempting the insert to avoid constraint exceptions.
    The normalized username is stored — raw @prefixes are stripped.
    """
    raw_username = data.get("username", "")
    source       = data.get("source", "")
    username     = deduplication.normalize_username(raw_username)

    existing = await deduplication.check_duplicate_by_username(db, username, source)

    if existing:
        existing.last_scraped_at = datetime.utcnow()
        if job_id and not existing.job_id:
            existing.job_id = job_id
        for field in ("followers_count", "following_count", "engagement_rate",
                      "profile_image_url", "bio", "website", "email", "whatsapp"):
            new_val = data.get(field)
            if new_val is not None:
                setattr(existing, field, new_val)
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        logger.debug("Lead refreshed: %s/%s", source, username)
        return existing, False

    lead = SellerLead(
        username=username,
        source=source,
        job_id=job_id,
        profile_url=data.get("profile_url"),
        full_name=data.get("full_name"),
        bio=data.get("bio"),
        website=data.get("website"),
        category=data.get("category"),
        profile_image_url=data.get("profile_image_url"),
        followers_count=data.get("followers_count"),
        following_count=data.get("following_count"),
        engagement_rate=data.get("engagement_rate"),
        email=data.get("email"),
        whatsapp=data.get("whatsapp"),
        country=data.get("country"),
        language=data.get("language"),
        discovery_source=data.get("discovery_source"),
        discovery_keyword=data.get("discovery_keyword"),
        lead_status="new",
        last_scraped_at=datetime.utcnow(),
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    logger.info("Lead created: %s/%s id=%s", source, username, lead.id)
    return lead, True


async def create_lead_from_schema(
    db: AsyncSession,
    payload: SellerLeadCreate,
    job_id: UUID | None = None,
) -> tuple[SellerLead, bool]:
    return await create_or_update_lead(db, data=payload.model_dump(), job_id=job_id)


# ── Read ──────────────────────────────────────────────────────────────────────

async def get_lead(db: AsyncSession, lead_id: UUID) -> SellerLead | None:
    result = await db.execute(
        select(SellerLead).where(SellerLead.id == lead_id)
    )
    return result.scalar_one_or_none()


# ── Update ────────────────────────────────────────────────────────────────────

async def patch_lead(
    db: AsyncSession,
    lead: SellerLead,
    payload: SellerLeadPatch,
) -> SellerLead:
    changed = False
    ai_updated = False
    for field, value in payload.model_dump(exclude_none=True).items():
        if getattr(lead, field, None) != value:
            setattr(lead, field, value)
            changed = True
        if field.startswith("ai_"):
            ai_updated = True

    if ai_updated:
        lead.ai_classified_at = datetime.utcnow()

    if changed:
        lead.updated_at = datetime.utcnow()
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        logger.info("Lead patched: id=%s fields=%s", lead.id, list(payload.model_fields_set))
    return lead


# ── Review (Phase 12) ─────────────────────────────────────────────────────────

async def apply_review(
    db: AsyncSession,
    lead: SellerLead,
    payload: ReviewPayload,
    *,
    reviewer: str,
) -> SellerLead:
    """
    Apply a human review action to a lead.

    Maps action → status and records who reviewed it.
    """
    new_status = _REVIEW_ACTION_MAP.get(payload.action)
    if not new_status:
        raise ValueError(f"Unknown review action: {payload.action}")

    lead.lead_status = new_status
    lead.reviewed_at  = datetime.utcnow()
    lead.reviewed_by  = reviewer[:100]
    if payload.notes:
        lead.notes = payload.notes
    lead.updated_at = datetime.utcnow()

    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    logger.info("Lead reviewed: id=%s action=%s reviewer=%s", lead.id, payload.action, reviewer)
    return lead


# ── Outreach (Phase 13) ───────────────────────────────────────────────────────

async def patch_outreach(
    db: AsyncSession,
    lead: SellerLead,
    payload: OutreachPatch,
) -> SellerLead:
    """Update outreach status / notes on a lead."""
    changed = False
    if payload.outreach_status is not None:
        lead.outreach_status = payload.outreach_status
        changed = True
    if payload.outreach_notes is not None:
        lead.outreach_notes = payload.outreach_notes
        changed = True

    if changed:
        lead.updated_at = datetime.utcnow()
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
    return lead


# ── Soft delete ───────────────────────────────────────────────────────────────

async def soft_delete_lead(db: AsyncSession, lead: SellerLead) -> SellerLead:
    lead.lead_status = "deleted"
    lead.updated_at  = datetime.utcnow()
    db.add(lead)
    await db.commit()
    logger.info("Lead soft-deleted: id=%s username=%s", lead.id, lead.username)
    return lead


# ── List / search ─────────────────────────────────────────────────────────────

async def list_leads(
    db: AsyncSession,
    *,
    source:         str | None = None,
    country:        str | None = None,
    category:       str | None = None,
    lead_status:    str | None = None,
    statuses:       list[str] | None = None,   # multi-status filter
    priority_level: str | None = None,
    job_id:         UUID | None = None,        # filter by discovery job
    ai_score_min:   float | None = None,
    ai_score_max:   float | None = None,
    score_min:      float | None = None,       # lead_score (0-100)
    score_max:      float | None = None,
    has_website:    bool | None = None,
    has_email:      bool | None = None,
    search:         str | None = None,
    page:           int = 1,
    page_size:      int = 20,
    order_by:       str = "score",             # score | created_at | ai_score
) -> tuple[list[SellerLead], int]:
    """
    Paginated, filtered, searchable lead listing.

    Deleted leads are always excluded.
    Order options:
      score      — lead_score DESC NULLS LAST, created_at DESC
      ai_score   — ai_relevance_score DESC NULLS LAST, created_at DESC
      created_at — created_at DESC
    """
    filters = [SellerLead.lead_status != "deleted"]

    if job_id:
        filters.append(SellerLead.job_id == job_id)
    if source:
        filters.append(SellerLead.source == source)
    if country:
        filters.append(SellerLead.country == country)
    if category:
        filters.append(SellerLead.category.ilike(f"%{category}%"))

    # Status: multi takes precedence over single
    if statuses:
        filters.append(SellerLead.lead_status.in_(statuses))
    elif lead_status:
        filters.append(SellerLead.lead_status == lead_status)

    if priority_level:
        if priority_level == 'unscored':
            filters.append(SellerLead.priority_level.is_(None))
        else:
            filters.append(SellerLead.priority_level == priority_level)
    if ai_score_min is not None:
        filters.append(SellerLead.ai_relevance_score >= ai_score_min)
    if ai_score_max is not None:
        filters.append(SellerLead.ai_relevance_score <= ai_score_max)
    if score_min is not None:
        filters.append(SellerLead.lead_score >= score_min)
    if score_max is not None:
        filters.append(SellerLead.lead_score <= score_max)
    if has_website is True:
        filters.append(SellerLead.website.isnot(None))
    elif has_website is False:
        filters.append(SellerLead.website.is_(None))
    if has_email is True:
        filters.append(SellerLead.email.isnot(None))
    elif has_email is False:
        filters.append(SellerLead.email.is_(None))

    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(*[col.ilike(term) for col in _SEARCH_COLS]))

    count_q = select(func.count(SellerLead.id)).where(*filters)
    total   = (await db.execute(count_q)).scalar_one() or 0

    if order_by == "created_at":
        ordering = [SellerLead.created_at.desc()]
    elif order_by == "ai_score":
        ordering = [SellerLead.ai_relevance_score.desc().nullslast(), SellerLead.created_at.desc()]
    else:  # default: lead_score
        ordering = [SellerLead.lead_score.desc().nullslast(), SellerLead.created_at.desc()]

    offset = (page - 1) * page_size
    data_q = (
        select(SellerLead)
        .where(*filters)
        .order_by(*ordering)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_q)
    items  = list(result.scalars().all())

    return items, total


# ── Bulk operations ───────────────────────────────────────────────────────────

async def bulk_classify_unclassified(
    limit: int = 50,
    source: str | None = None,
) -> int:
    """
    Classify and score all unclassified leads up to `limit`.

    Opens its own session (safe to call from background tasks).
    Returns the number of leads classified.
    """
    from app.db.database import AsyncSessionLocal
    from app.services.seller_discovery.classifier import apply_classification_to_lead
    from app.services.seller_discovery.scorer import apply_score_to_lead

    classified = 0
    async with AsyncSessionLocal() as db:
        filters = [SellerLead.ai_classified_at.is_(None), SellerLead.lead_status != "deleted"]
        if source:
            filters.append(SellerLead.source == source)

        result = await db.execute(
            select(SellerLead)
            .where(*filters)
            .order_by(SellerLead.created_at.desc())
            .limit(limit)
        )
        leads = list(result.scalars().all())

        for lead in leads:
            try:
                success = await apply_classification_to_lead(db, lead)
                if success:
                    classified += 1
                await apply_score_to_lead(db, lead)
            except Exception as exc:
                logger.warning("bulk_classify: failed for lead %s: %s", lead.id, exc)

    logger.info("bulk_classify_unclassified: classified %d/%d leads", classified, len(leads))
    return classified
