"""
DiscoveryJob lifecycle — pure DB helpers, no HTTP.

Status lifecycle:
  queued → running → completed
                  → failed
  queued → cancelled (via API)

Mirrors app.services.sync.job_manager patterns exactly.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.seller_lead import DiscoveryJob

logger = logging.getLogger(__name__)

# Columns that can be atomically incremented during a run
_COUNTER_COLS = frozenset({
    "leads_found",
    "leads_created",
    "leads_skipped_dupe",
    "leads_classified",
})


# ── Serialisation ─────────────────────────────────────────────────────────────

def _dt(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


def job_to_dict(job: DiscoveryJob) -> dict:
    return {
        "id":                 str(job.id),
        "keyword_id":         str(job.keyword_id) if job.keyword_id else None,
        "source":             job.source,
        "job_type":           job.job_type,
        "keyword":            job.keyword,
        "triggered_by":       job.triggered_by,
        "max_leads":          job.max_leads,
        "status":             job.status,
        "leads_found":        job.leads_found or 0,
        "leads_created":      job.leads_created or 0,
        "leads_skipped_dupe": job.leads_skipped_dupe or 0,
        "leads_classified":   job.leads_classified or 0,
        "started_at":         _dt(job.started_at),
        "completed_at":       _dt(job.completed_at),
        "error_message":      job.error_message,
        "created_at":         _dt(job.created_at),
        "updated_at":         _dt(job.updated_at),
    }


# ── Create ────────────────────────────────────────────────────────────────────

async def create_job(
    db: AsyncSession,
    *,
    source:       str,
    job_type:     str,
    keyword:      str,
    max_leads:    int = 500,
    triggered_by: str = "manual",
    keyword_id:   UUID | None = None,
) -> DiscoveryJob:
    """Create a new job in queued state and commit."""
    job = DiscoveryJob(
        source=source,
        job_type=job_type,
        keyword=keyword,
        max_leads=max_leads,
        triggered_by=triggered_by,
        keyword_id=keyword_id,
        status="queued",
        leads_found=0,
        leads_created=0,
        leads_skipped_dupe=0,
        leads_classified=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info("DiscoveryJob created id=%s type=%s keyword=%s", job.id, job_type, keyword)
    return job


# ── State transitions ─────────────────────────────────────────────────────────

async def start_job(db: AsyncSession, job: DiscoveryJob) -> DiscoveryJob:
    """queued → running. Commits."""
    job.status     = "running"
    job.started_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info("DiscoveryJob started id=%s", job.id)
    return job


async def complete_job(
    db: AsyncSession,
    job: DiscoveryJob,
    *,
    leads_found:        int = 0,
    leads_created:      int = 0,
    leads_skipped_dupe: int = 0,
    leads_classified:   int = 0,
) -> DiscoveryJob:
    """running → completed. Commits."""
    now                  = datetime.utcnow()
    job.status           = "completed"
    job.completed_at     = now
    job.updated_at       = now
    job.leads_found      = leads_found
    job.leads_created    = leads_created
    job.leads_skipped_dupe = leads_skipped_dupe
    job.leads_classified = leads_classified
    job.error_message    = None
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info(
        "DiscoveryJob completed id=%s found=%d created=%d dupes=%d",
        job.id, leads_found, leads_created, leads_skipped_dupe,
    )
    return job


async def fail_job(
    db: AsyncSession,
    job: DiscoveryJob,
    *,
    error: str,
) -> DiscoveryJob:
    """running → failed. Commits."""
    now              = datetime.utcnow()
    job.status       = "failed"
    job.completed_at = now
    job.updated_at   = now
    job.error_message = error[:2000]  # guard against oversized error strings
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.error("DiscoveryJob failed id=%s error=%s", job.id, error[:200])
    return job


async def cancel_job(db: AsyncSession, job: DiscoveryJob) -> DiscoveryJob:
    """queued → cancelled. Commits. Cannot cancel a running job via API."""
    if job.status == "running":
        raise ValueError("Cannot cancel a running job via API — stop the worker instead.")
    now              = datetime.utcnow()
    job.status       = "cancelled"
    job.completed_at = now
    job.updated_at   = now
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info("DiscoveryJob cancelled id=%s", job.id)
    return job


# ── Atomic counter increments ─────────────────────────────────────────────────

async def increment_counters(
    db: AsyncSession,
    job_id: UUID,
    **amounts: int,
) -> None:
    """
    Atomically increment one or more counter columns on a running job.

    Usage:
        await increment_counters(db, job_id, leads_found=5, leads_created=3)

    Safe to call from the orchestrator loop without re-loading the job object.
    Only columns in _COUNTER_COLS are accepted; unknown keys are silently ignored.
    """
    values: dict = {}
    for field, amount in amounts.items():
        if field in _COUNTER_COLS and isinstance(amount, int) and amount != 0:
            col = getattr(DiscoveryJob, field)
            values[field] = col + amount

    if not values:
        return

    await db.execute(
        update(DiscoveryJob)
        .where(DiscoveryJob.id == job_id)
        .values(**values)
    )
    await db.commit()


# ── Queries ───────────────────────────────────────────────────────────────────

async def get_job(db: AsyncSession, job_id: UUID) -> DiscoveryJob | None:
    result = await db.execute(
        select(DiscoveryJob).where(DiscoveryJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    *,
    status:    str | None = None,
    source:    str | None = None,
    job_type:  str | None = None,
    page:      int = 1,
    page_size: int = 20,
) -> tuple[list[DiscoveryJob], int]:
    filters = []
    if status:
        filters.append(DiscoveryJob.status == status)
    if source:
        filters.append(DiscoveryJob.source == source)
    if job_type:
        filters.append(DiscoveryJob.job_type == job_type)

    count_q = select(func.count(DiscoveryJob.id))
    if filters:
        count_q = count_q.where(*filters)
    total = (await db.execute(count_q)).scalar_one() or 0

    data_q = select(DiscoveryJob)
    if filters:
        data_q = data_q.where(*filters)
    data_q = (
        data_q
        .order_by(DiscoveryJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(data_q)
    return list(result.scalars().all()), total
