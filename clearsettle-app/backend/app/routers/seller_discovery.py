"""
Seller Discovery Engine API — Phases 3–14.

Prefix: /seller-discovery

Seller Leads:
  GET    /leads                        — paginated list + filters + search
  GET    /leads/{lead_id}              — single lead detail
  POST   /leads                        — create lead manually
  PATCH  /leads/{lead_id}             — partial update
  DELETE /leads/{lead_id}             — soft delete
  POST   /leads/{lead_id}/classify    — Phase 7: trigger AI classification
  POST   /leads/{lead_id}/score       — Phase 8: compute / refresh score
  POST   /leads/{lead_id}/review      — Phase 12: approve / reject / qualify
  PATCH  /leads/{lead_id}/outreach    — Phase 13: update outreach status / notes
  POST   /leads/bulk-classify         — Phase 7: classify all unclassified (bg)

Discovery Jobs:
  GET    /jobs                         — list jobs
  POST   /jobs                         — create + queue a discovery run
  GET    /jobs/{job_id}               — job detail
  PATCH  /jobs/{job_id}               — cancel
  GET    /jobs/{job_id}/events        — SSE real-time progress stream

Discovery Keywords:
  GET    /keywords                     — list seed keywords
  POST   /keywords                     — add keyword
  PATCH  /keywords/{kw_id}            — activate / deactivate / re-prioritise

Queue management:
  GET    /queue/stats                  — counts per status + concurrency info
  POST   /queue/launch-all            — dispatch jobs for all active keywords
  POST   /queue/retry-failed          — re-queue failed jobs with retries remaining

Analytics (Phase 11):
  GET    /analytics                    — full analytics snapshot

Review queue (Phase 12):
  GET    /review-queue                 — leads needing human review

Outreach queue (Phase 13):
  GET    /outreach-queue              — leads ready for outreach

Health (Phase 14):
  GET    /health                       — component health check
"""
from __future__ import annotations

import asyncio
import json as _json
import logging
import math
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.schemas.seller_discovery import (
    ActivityCreate,
    BulkClassifyRequest,
    DiscoveryJobCreate,
    DiscoveryJobPatch,
    DiscoveryKeywordCreate,
    DiscoveryKeywordPatch,
    OutreachPatch,
    ReviewPayload,
    SellerLeadCreate,
    SellerLeadPatch,
)
from app.services.seller_discovery import (
    event_bus as discovery_event_bus,
    job_manager,
    keyword_store,
    lead_store,
    queue_manager,
)
from app.services.seller_discovery import activity_store

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# SELLER LEADS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/leads")
async def list_leads(
    source:         str | None   = Query(default=None),
    country:        str | None   = Query(default=None),
    category:       str | None   = Query(default=None),
    lead_status:    str | None   = Query(default=None),
    priority_level: str | None   = Query(default=None),
    job_id:         UUID | None  = Query(default=None),
    ai_score_min:   float | None = Query(default=None, ge=0, le=1),
    ai_score_max:   float | None = Query(default=None, ge=0, le=1),
    score_min:      float | None = Query(default=None, ge=0, le=100),
    score_max:      float | None = Query(default=None, ge=0, le=100),
    has_website:    bool | None  = Query(default=None),
    has_email:      bool | None  = Query(default=None),
    search:         str | None   = Query(default=None, max_length=200),
    order_by:       str          = Query(default="score", pattern="^(score|ai_score|created_at)$"),
    page:           int          = Query(default=1, ge=1),
    page_size:      int          = Query(default=20, ge=1, le=200),
    db:             AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await lead_store.list_leads(
        db,
        source=source, country=country, category=category,
        lead_status=lead_status, priority_level=priority_level,
        job_id=job_id,
        ai_score_min=ai_score_min, ai_score_max=ai_score_max,
        score_min=score_min, score_max=score_max,
        has_website=has_website, has_email=has_email,
        search=search, order_by=order_by,
        page=page, page_size=page_size,
    )
    return {
        "items":     [lead_store.lead_to_dict(l) for l in items],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     math.ceil(total / page_size) if total else 0,
    }


@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: UUID,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead_store.lead_to_dict(lead)


@router.post("/leads", status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: SellerLeadCreate,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    lead, created = await lead_store.create_lead_from_schema(db, payload)
    result = lead_store.lead_to_dict(lead)
    result["existing"] = not created
    return result


@router.patch("/leads/{lead_id}")
async def patch_lead(
    lead_id: UUID,
    payload: SellerLeadPatch,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if lead.lead_status == "deleted":
        raise HTTPException(status_code=409, detail="Lead has been deleted.")
    lead = await lead_store.patch_lead(db, lead, payload)
    return lead_store.lead_to_dict(lead)


@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: UUID,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if lead.lead_status == "deleted":
        return {"deleted": True, "already_deleted": True}
    await lead_store.soft_delete_lead(db, lead)
    return {"deleted": True, "id": str(lead_id)}


# ── Phase 7: AI Classification ────────────────────────────────────────────────

@router.post("/leads/{lead_id}/classify")
async def classify_lead(
    lead_id: UUID,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Trigger AI classification for a single lead using Claude.

    Immediately scores the lead after classification.
    Returns 424 if no ANTHROPIC_API_KEY is configured.
    """
    from app.services.seller_discovery.classifier import apply_classification_to_lead
    from app.services.seller_discovery.scorer import apply_score_to_lead

    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if not get_settings().anthropic_api_key:
        raise HTTPException(status_code=424, detail="ANTHROPIC_API_KEY not configured.")

    success = await apply_classification_to_lead(db, lead)
    if not success:
        raise HTTPException(status_code=422, detail="Classification skipped — insufficient profile data.")

    await apply_score_to_lead(db, lead)
    actor = getattr(user, "email", None) or "system"
    await activity_store.add_activity(
        db, lead_id=lead_id, activity_type="classify",
        content=f"AI classified — relevance {float(lead.ai_relevance_score or 0)*100:.0f}%, "
                f"ecommerce={'yes' if lead.ai_is_ecommerce else 'no'}, "
                f"category={lead.ai_category or '—'}",
        metadata={"ai_relevance_score": float(lead.ai_relevance_score or 0),
                  "ai_category": lead.ai_category,
                  "ai_is_ecommerce": lead.ai_is_ecommerce},
        created_by=actor,
    )
    return lead_store.lead_to_dict(lead)


@router.post("/leads/bulk-classify", status_code=status.HTTP_202_ACCEPTED)
async def bulk_classify(
    payload:          BulkClassifyRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """
    Classify and score all unclassified leads in the background.

    Returns immediately; poll /analytics for progress.
    Returns 424 if ANTHROPIC_API_KEY is not set.
    """
    if not get_settings().anthropic_api_key:
        raise HTTPException(status_code=424, detail="ANTHROPIC_API_KEY not configured.")

    background_tasks.add_task(
        lead_store.bulk_classify_unclassified,
        limit=payload.limit,
        source=payload.source,
    )
    return {"queued": True, "limit": payload.limit}


# ── Phase 8: Scoring ──────────────────────────────────────────────────────────

@router.post("/leads/{lead_id}/score")
async def score_lead(
    lead_id: UUID,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Compute or refresh the lead score. Idempotent — safe to call repeatedly."""
    from app.services.seller_discovery.scorer import apply_score_to_lead

    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    await apply_score_to_lead(db, lead)
    actor = getattr(user, "email", None) or "system"
    await activity_store.add_activity(
        db, lead_id=lead_id, activity_type="score",
        content=f"Lead scored {float(lead.lead_score or 0):.0f}/100 — priority: {lead.priority_level or 'unscored'}",
        metadata={"lead_score": float(lead.lead_score or 0), "priority_level": lead.priority_level},
        created_by=actor,
    )
    return lead_store.lead_to_dict(lead)


# ── Phase 12: Human Review ────────────────────────────────────────────────────

@router.post("/leads/{lead_id}/review")
async def review_lead(
    lead_id: UUID,
    payload: ReviewPayload,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Apply a review action (approve / reject / qualify / contact_ready / …).

    Records the reviewer identity from the JWT token.
    """
    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if lead.lead_status == "deleted":
        raise HTTPException(status_code=409, detail="Lead has been deleted.")

    reviewer = getattr(user, "email", None) or getattr(user, "username", "unknown")
    old_status = lead.lead_status
    try:
        lead = await lead_store.apply_review(db, lead, payload, reviewer=reviewer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await activity_store.add_activity(
        db, lead_id=lead_id, activity_type="status_change",
        content=payload.notes or f"Status changed: {old_status} → {lead.lead_status}",
        metadata={"old_status": old_status, "new_status": lead.lead_status, "action": payload.action},
        created_by=reviewer,
    )
    return lead_store.lead_to_dict(lead)


# ── Phase 13: Outreach ────────────────────────────────────────────────────────

@router.patch("/leads/{lead_id}/outreach")
async def update_outreach(
    lead_id: UUID,
    payload: OutreachPatch,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update outreach status and/or prep notes on a lead."""
    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    lead = await lead_store.patch_outreach(db, lead, payload)
    actor = getattr(user, "email", None) or "system"
    parts = []
    if payload.outreach_status:
        parts.append(f"status → {payload.outreach_status}")
    if payload.outreach_notes:
        parts.append(payload.outreach_notes)
    await activity_store.add_activity(
        db, lead_id=lead_id, activity_type="outreach",
        content=", ".join(parts) or f"Outreach updated",
        metadata={"outreach_status": payload.outreach_status},
        created_by=actor,
    )
    return lead_store.lead_to_dict(lead)


# ── Phase 14: Activity / Audit Log ───────────────────────────────────────────

@router.get("/leads/{lead_id}/activity")
async def list_lead_activity(
    lead_id:   UUID,
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
    db:        AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return chronological audit trail for a lead (newest first)."""
    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    items = await activity_store.list_activity(db, lead_id, page=page, page_size=page_size)
    return [activity_store.activity_to_dict(a) for a in items]


@router.post("/leads/{lead_id}/activity", status_code=status.HTTP_201_CREATED)
async def add_lead_activity(
    lead_id: UUID,
    payload: ActivityCreate,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Add a note, follow-up, call log, email log, WhatsApp log, or tag to a lead.

    When activity_type='follow_up' and follow_up_at is provided, also updates
    lead.follow_up_at on the lead record.
    """
    from datetime import datetime as _dt
    lead = await lead_store.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    meta = dict(payload.metadata or {})
    if payload.activity_type == "follow_up" and payload.follow_up_at:
        lead.follow_up_at = payload.follow_up_at
        lead.updated_at   = _dt.utcnow()
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        meta["follow_up_at"] = payload.follow_up_at.isoformat()

    actor = getattr(user, "email", None) or "system"
    act = await activity_store.add_activity(
        db,
        lead_id=lead_id,
        activity_type=payload.activity_type,
        content=payload.content,
        metadata=meta or None,
        created_by=actor,
    )
    return activity_store.activity_to_dict(act)


@router.get("/review-queue")
async def review_queue(
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db:        AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Leads pending human review (status: new or review_pending).

    Ordered by lead_score DESC so highest-value leads surface first.
    """
    items, total = await lead_store.list_leads(
        db,
        statuses=["new", "review_pending"],
        order_by="score",
        page=page,
        page_size=page_size,
    )
    return {
        "items":     [lead_store.lead_to_dict(l) for l in items],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     math.ceil(total / page_size) if total else 0,
    }


@router.get("/outreach-queue")
async def outreach_queue(
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db:        AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Leads ready for outreach (status: contact_ready or qualified).

    Ordered by lead_score DESC.
    """
    items, total = await lead_store.list_leads(
        db,
        statuses=["contact_ready", "qualified"],
        order_by="score",
        page=page,
        page_size=page_size,
    )
    return {
        "items":     [lead_store.lead_to_dict(l) for l in items],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     math.ceil(total / page_size) if total else 0,
    }


# ── Phase 11: Analytics ───────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics(
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Full analytics snapshot: overview KPIs + time-series + breakdowns.
    Safe to call at any frequency — all queries use indexed columns.
    """
    from app.services.seller_discovery.analytics import get_full_analytics
    return await get_full_analytics(db)


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVERY JOBS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    source:        str | None = Query(default=None),
    job_type:      str | None = Query(default=None),
    page:          int        = Query(default=1, ge=1),
    page_size:     int        = Query(default=20, ge=1, le=100),
    db:            AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await job_manager.list_jobs(
        db, status=status_filter, source=source,
        job_type=job_type, page=page, page_size=page_size,
    )
    return {
        "items":     [job_manager.job_to_dict(j) for j in items],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     math.ceil(total / page_size) if total else 0,
    }


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    payload:          DiscoveryJobCreate,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Create a discovery job and queue it immediately.
    Job runs asynchronously — concurrency-limited by the queue semaphore.
    Poll GET /jobs/{id} or stream GET /jobs/{id}/events for progress.
    """
    keyword_id = UUID(payload.keyword_id) if payload.keyword_id else None
    job = await job_manager.create_job(
        db,
        source=payload.source, job_type=payload.job_type,
        keyword=payload.keyword, max_leads=payload.max_leads,
        triggered_by="manual", keyword_id=keyword_id,
    )
    background_tasks.add_task(queue_manager.dispatch_job, job.id)
    result = job_manager.job_to_dict(job)
    result["queued"] = True
    return result


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    db:     AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    job = await job_manager.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job_manager.job_to_dict(job)


@router.patch("/jobs/{job_id}")
async def patch_job(
    job_id:  UUID,
    payload: DiscoveryJobPatch,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    job = await job_manager.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if payload.status == "cancelled":
        try:
            job = await job_manager.cancel_job(db, job)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
    return job_manager.job_to_dict(job)


@router.get("/jobs/{job_id}/events")
async def job_event_stream(
    job_id:  UUID,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    SSE stream of real-time job progress events.

    Clients connect here and receive:
      - Replay of all events emitted so far (for late connects)
      - Live events as the scraper runs
      - A final stream_end event when the job finishes

    Uses Authorization: Bearer header — works with fetch() ReadableStream
    (unlike native EventSource which doesn't support auth headers).
    """
    job = await job_manager.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    job_status = job.status
    await db.close()

    async def _event_generator():
        yield ": ping\n\n"

        if job_status in ("completed", "failed", "cancelled"):
            payload = {"type": f"job_{job_status}", "job_id": str(job_id)}
            yield f"data: {_json.dumps(payload)}\n\n"
            yield "data: {\"type\": \"stream_end\"}\n\n"
            return

        q, history = discovery_event_bus.subscribe(job_id)
        try:
            for evt in history:
                yield f"data: {_json.dumps(evt)}\n\n"

            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if discovery_event_bus.is_done(item):
                    yield "data: {\"type\": \"stream_end\"}\n\n"
                    break

                yield f"data: {_json.dumps(item)}\n\n"
        finally:
            discovery_event_bus.unsubscribe(job_id, q)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVERY KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/keywords")
async def list_keywords(
    source:       str | None  = Query(default=None),
    keyword_type: str | None  = Query(default=None),
    is_active:    bool | None = Query(default=None),
    page:         int         = Query(default=1, ge=1),
    page_size:    int         = Query(default=50, ge=1, le=200),
    db:           AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await keyword_store.list_keywords(
        db, source=source, keyword_type=keyword_type,
        is_active=is_active, page=page, page_size=page_size,
    )
    return {
        "items":     [keyword_store.keyword_to_dict(k) for k in items],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     math.ceil(total / page_size) if total else 0,
    }


@router.post("/keywords", status_code=status.HTTP_201_CREATED)
async def create_keyword(
    payload: DiscoveryKeywordCreate,
    db:      AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    kw = await keyword_store.create_keyword(db, payload)
    return keyword_store.keyword_to_dict(kw)


@router.patch("/keywords/{keyword_id}")
async def patch_keyword(
    keyword_id: UUID,
    payload:    DiscoveryKeywordPatch,
    db:         AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    kw = await keyword_store.get_keyword(db, keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found.")
    kw = await keyword_store.patch_keyword(db, kw, payload)
    return keyword_store.keyword_to_dict(kw)


# ─────────────────────────────────────────────────────────────────────────────
# QUEUE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/queue/stats")
async def queue_stats(user=Depends(get_current_user)):
    """Real-time queue statistics."""
    return await queue_manager.get_queue_stats()


@router.post("/queue/launch-all", status_code=status.HTTP_202_ACCEPTED)
async def launch_all_keywords(
    background_tasks: BackgroundTasks,
    source:           str | None = Query(default=None),
    min_hours:        int        = Query(default=24, ge=1),
    user=Depends(get_current_user),
):
    """
    Create and dispatch discovery jobs for every active keyword not crawled
    in the last `min_hours` hours. Idempotent — safe to call repeatedly.
    """
    jobs = await queue_manager.bulk_launch_from_keywords(
        background_tasks,
        source=source,
        min_hours_since_crawl=min_hours,
    )
    return {"dispatched": len(jobs), "jobs": jobs}


@router.post("/queue/retry-failed", status_code=status.HTTP_202_ACCEPTED)
async def retry_failed(
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Re-queue all failed jobs that have retries remaining."""
    requeued = await queue_manager.retry_failed_jobs(background_tasks)
    return {"requeued": requeued}


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH (Phase 14)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health")
async def discovery_health(
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Component health check for the Seller Discovery Engine.

    Checks: DB connectivity, queue state, AI key presence, scheduler status.
    """
    from app.services.seller_discovery import scheduler as discovery_scheduler

    stats = await queue_manager.get_queue_stats()
    settings = get_settings()

    return {
        "status":                "ok",
        "queue":                 stats,
        "anthropic_configured":  bool(settings.anthropic_api_key),
        "scraper_proxy_set":     bool(settings.scraper_proxy_url),
        "scheduler_running":     not (discovery_scheduler._task is None or
                                      (discovery_scheduler._task and discovery_scheduler._task.done())),
        "max_concurrent_jobs":   settings.discovery_max_concurrent_jobs,
        "rate_limit_rps":        settings.discovery_rate_limit_rps,
        "crawl_interval_hours":  settings.discovery_crawl_interval_hours,
    }
