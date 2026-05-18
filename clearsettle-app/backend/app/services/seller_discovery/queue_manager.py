"""
Discovery queue manager.

Responsibilities:
  1. Concurrency control — asyncio.Semaphore limits simultaneous Chromium instances.
  2. Retry logic          — re-queue failed jobs that have retries remaining.
  3. Queue statistics     — counts per status, backlog size.
  4. Bulk launch          — create + dispatch jobs for all active keywords at once.

Semaphore design:
  Module-level semaphore is created lazily on first use, sized from Settings.
  All scraper invocations go through dispatch_job() which acquires the semaphore
  before calling the orchestrator. This prevents OOM when many jobs are queued
  simultaneously.

  Default: discovery_max_concurrent_jobs = 2
    → max 2 Chromium browsers running at any moment.
    → remaining queued jobs wait inside asyncio.Semaphore.acquire().

Scale note:
  For distributed deployments replace the in-process semaphore with a Redis
  SETNX-based distributed lock — only this module needs to change.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import AsyncSessionLocal
from app.db.models.seller_lead import DiscoveryJob, DiscoveryKeyword
from app.services.seller_discovery import job_manager

logger = logging.getLogger(__name__)

# Lazily created — sized from settings on first call
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        limit = get_settings().discovery_max_concurrent_jobs
        _semaphore = asyncio.Semaphore(limit)
        logger.info("Discovery queue semaphore initialised — max_concurrent=%d", limit)
    return _semaphore


# ── Dispatch ──────────────────────────────────────────────────────────────────

async def dispatch_job(job_id: UUID) -> None:
    """
    Acquire the concurrency semaphore, run the job, then post-process.

    Post-processing (outside the semaphore):
      - Score all new leads from this job (fast, no API).
      - AI-classify up to 10 unclassified leads if ANTHROPIC_API_KEY is set.
      - Re-score classified leads with the enriched AI data.

    All BackgroundTasks calls go through here so concurrency is always respected.
    """
    from app.services.seller_discovery import orchestrator

    sem = _get_semaphore()
    logger.info("Waiting for semaphore slot — job %s", job_id)
    async with sem:
        logger.info("Semaphore acquired — starting job %s", job_id)
        async with AsyncSessionLocal() as db:
            await orchestrator.run_discovery_job(job_id, db)
    logger.info("Semaphore released — job %s done", job_id)

    # Post-process outside the semaphore so it doesn't block the next job
    try:
        await _post_process_job_leads(job_id)
    except Exception as exc:
        logger.exception("Post-process failed for job %s: %s", job_id, exc)


async def _post_process_job_leads(job_id: UUID) -> None:
    """
    Score + optionally classify leads created by a completed job.

    Opens its own session.  Safe to call after the job session is closed.
    Classification cap: 10 leads per job (cost protection).
    """
    from sqlalchemy import select
    from app.core.config import get_settings
    from app.db.models.seller_lead import SellerLead
    from app.services.seller_discovery.scorer import apply_score_to_lead

    settings = get_settings()

    async with AsyncSessionLocal() as db:
        job = await db.get(DiscoveryJob, job_id)
        if not job or job.status != "completed":
            return

        result = await db.execute(
            select(SellerLead)
            .where(SellerLead.job_id == job_id)
            .limit(200)
        )
        leads = list(result.scalars().all())
        if not leads:
            return

        classified = 0
        if settings.anthropic_api_key:
            from app.services.seller_discovery.classifier import apply_classification_to_lead
            for lead in leads:
                if classified >= 10:
                    break
                if lead.ai_classified_at:
                    continue
                try:
                    success = await apply_classification_to_lead(db, lead)
                    if success:
                        classified += 1
                except Exception as exc:
                    logger.warning("Classify failed for lead %s: %s", lead.id, exc)

        # Score all leads (uses AI fields if just classified)
        for lead in leads:
            try:
                fresh = await db.get(SellerLead, lead.id)
                if fresh:
                    await apply_score_to_lead(db, fresh)
            except Exception as exc:
                logger.warning("Score failed for lead %s: %s", lead.id, exc)

        if classified:
            job.leads_classified = classified
            job.updated_at = datetime.utcnow()
            db.add(job)
            await db.commit()

        logger.info(
            "Post-process job %s: %d leads scored, %d classified",
            job_id, len(leads), classified,
        )


# ── Retry ─────────────────────────────────────────────────────────────────────

async def retry_failed_jobs(background_tasks) -> int:
    """
    Find all failed jobs with retries remaining and re-queue them.

    Returns the number of jobs re-queued.
    Called manually via API or automatically by the scheduler.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DiscoveryJob).where(
                DiscoveryJob.status == "failed",
                DiscoveryJob.retry_count < DiscoveryJob.max_retries,
            )
        )
        jobs = list(result.scalars().all())

        requeued = 0
        for job in jobs:
            job.status      = "queued"
            job.retry_count = (job.retry_count or 0) + 1
            job.started_at  = None
            job.completed_at = None
            job.error_message = None
            job.updated_at  = datetime.utcnow()
            db.add(job)
            requeued += 1

        if requeued:
            await db.commit()
            for job in jobs:
                background_tasks.add_task(dispatch_job, job.id)
                logger.info(
                    "Job %s re-queued (attempt %d/%d)",
                    job.id, job.retry_count, job.max_retries,
                )

    logger.info("retry_failed_jobs: re-queued %d jobs", requeued)
    return requeued


# ── Bulk launch ───────────────────────────────────────────────────────────────

async def bulk_launch_from_keywords(
    background_tasks,
    *,
    source:         str | None = None,
    min_hours_since_crawl: int = 24,
) -> list[dict]:
    """
    Create and dispatch one discovery job per active keyword that hasn't been
    crawled in the last `min_hours_since_crawl` hours.

    Returns a list of created job summaries.
    """
    settings  = get_settings()
    cutoff_dt = datetime.utcnow() - timedelta(hours=min_hours_since_crawl)

    async with AsyncSessionLocal() as db:
        q = select(DiscoveryKeyword).where(
            DiscoveryKeyword.is_active == True,  # noqa: E712
        )
        if source:
            q = q.where(DiscoveryKeyword.source == source)

        # Include keywords never crawled OR not crawled since cutoff
        q = q.where(
            (DiscoveryKeyword.last_crawled_at == None) |  # noqa: E711
            (DiscoveryKeyword.last_crawled_at < cutoff_dt)
        ).order_by(DiscoveryKeyword.priority.asc())

        result   = await db.execute(q)
        keywords = list(result.scalars().all())

        created_jobs = []
        for kw in keywords:
            strategy = _keyword_type_to_strategy(kw.keyword_type)
            job = await job_manager.create_job(
                db,
                source       = kw.source,
                job_type     = strategy,
                keyword      = kw.keyword,
                max_leads    = settings.discovery_max_leads_per_job,
                triggered_by = "scheduler",
                keyword_id   = kw.id,
            )
            background_tasks.add_task(dispatch_job, job.id)
            created_jobs.append({
                "job_id":  str(job.id),
                "keyword": kw.keyword,
                "source":  kw.source,
            })
            logger.info("Bulk launch: created job %s for keyword '%s'", job.id, kw.keyword)

    logger.info("bulk_launch_from_keywords: created %d jobs", len(created_jobs))
    return created_jobs


# ── Queue statistics ──────────────────────────────────────────────────────────

async def get_queue_stats() -> dict:
    """
    Return counts per status + concurrency info.
    Safe to call at any frequency — single aggregation query.
    """
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(DiscoveryJob.status, func.count(DiscoveryJob.id))
            .group_by(DiscoveryJob.status)
        )
        counts = {status: cnt for status, cnt in rows.all()}

    sem    = _get_semaphore()
    limit  = get_settings().discovery_max_concurrent_jobs
    in_use = limit - sem._value   # semaphore._value = available slots

    return {
        "queued":           counts.get("queued",    0),
        "running":          counts.get("running",   0),
        "completed":        counts.get("completed", 0),
        "failed":           counts.get("failed",    0),
        "cancelled":        counts.get("cancelled", 0),
        "total":            sum(counts.values()),
        "max_concurrent":   limit,
        "slots_in_use":     max(0, in_use),
        "slots_available":  sem._value,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _keyword_type_to_strategy(keyword_type: str) -> str:
    return {
        "hashtag":    "hashtag",
        "competitor": "competitor_followers",
        "direct":     "direct",
    }.get(keyword_type, "hashtag")
