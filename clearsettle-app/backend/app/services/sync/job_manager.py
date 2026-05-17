"""
SyncJob lifecycle management — pure DB helpers, no HTTP calls.

All functions accept an open AsyncSession and return the mutated ORM object.
The caller owns the session lifecycle; these functions commit where noted.
"""
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.sync_job import SyncJob
from app.db.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


# ── Job creation ───────────────────────────────────────────────────────────────

async def create_job(
    db: AsyncSession,
    *,
    connection_id,
    company_id=None,
    platform: str | None = None,
    job_type: str,
    triggered_by: str = "manual",
    max_retries: int = 3,
    job_options: dict | None = None,
) -> SyncJob:
    """Create a new job in pending state and commit."""
    job = SyncJob(
        connection_id=connection_id,
        company_id=company_id,
        platform=platform,
        job_type=job_type,
        triggered_by=triggered_by,
        status="pending",
        retry_count=0,
        max_retries=max_retries,
        job_options_json=json.dumps(job_options) if job_options else None,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info("Created sync job %s type=%s platform=%s", job.id, job_type, platform)
    return job


# ── State transitions ──────────────────────────────────────────────────────────

async def start_job(db: AsyncSession, job: SyncJob) -> SyncJob:
    """Transition pending → running. Commits."""
    job.status     = "running"
    job.started_at = datetime.utcnow()
    db.add(job)
    await db.commit()
    return job


async def complete_job(
    db: AsyncSession,
    job: SyncJob,
    *,
    records_created: int = 0,
    records_updated: int = 0,
) -> SyncJob:
    """Transition running → completed. Commits all pending session changes."""
    now = datetime.utcnow()
    job.status          = "completed"
    job.completed_at    = now
    job.records_created = records_created
    job.records_updated = records_updated
    job.records_synced  = records_created + records_updated   # backward compat
    job.error_message   = None
    if job.started_at:
        job.duration_seconds = (now - job.started_at).total_seconds()
    db.add(job)
    await db.commit()
    logger.info("Job %s completed: created=%d updated=%d", job.id, records_created, records_updated)
    return job


async def fail_job(
    db: AsyncSession,
    job: SyncJob,
    *,
    error: str,
    retryable: bool = True,
) -> SyncJob:
    """
    Transition running → failed (or → pending if retries remain).

    If retryable and retry_count < max_retries: re-queues as pending (clears
    started_at so the orchestrator restarts cleanly).
    Otherwise: terminal failure.

    Commits all pending session changes.
    """
    job.error_message = error
    job.retry_count   = (job.retry_count or 0) + 1

    will_retry = retryable and (job.retry_count < job.max_retries)
    if will_retry:
        job.status     = "pending"
        job.started_at = None
        logger.warning(
            "Job %s failed — retry %d/%d scheduled: %s",
            job.id, job.retry_count, job.max_retries, error,
        )
    else:
        now              = datetime.utcnow()
        job.status       = "failed"
        job.completed_at = now
        if job.started_at:
            job.duration_seconds = (now - job.started_at).total_seconds()
        logger.error(
            "Job %s terminal failure (attempt %d/%d): %s",
            job.id, job.retry_count, job.max_retries, error,
        )

    db.add(job)
    await db.commit()
    return job


async def cancel_job(db: AsyncSession, job: SyncJob) -> SyncJob:
    """Mark a pending job as cancelled. Commits."""
    now              = datetime.utcnow()
    job.status       = "cancelled"
    job.completed_at = now
    if job.started_at:
        job.duration_seconds = (now - job.started_at).total_seconds()
    db.add(job)
    await db.commit()
    return job


# ── Queries ────────────────────────────────────────────────────────────────────

async def get_job(db: AsyncSession, job_id: UUID) -> SyncJob | None:
    """Fetch a single job with its logs."""
    result = await db.execute(
        select(SyncJob)
        .options(selectinload(SyncJob.logs))
        .where(SyncJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    *,
    company_id=None,
    connection_id=None,
    platform: str | None = None,
    status: str | None = None,
    job_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[SyncJob]:
    """List jobs without loading logs (use get_job for detail view)."""
    q = select(SyncJob)
    if company_id:
        q = q.where(SyncJob.company_id == company_id)
    if connection_id:
        q = q.where(SyncJob.connection_id == connection_id)
    if platform:
        q = q.where(SyncJob.platform == platform)
    if status:
        q = q.where(SyncJob.status == status)
    if job_type:
        q = q.where(SyncJob.job_type == job_type)
    q = q.order_by(SyncJob.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def count_pending(db: AsyncSession, *, company_id=None) -> int:
    """Count pending/running jobs — used by scheduler to avoid over-queuing."""
    from sqlalchemy import func
    q = select(func.count()).select_from(SyncJob).where(
        SyncJob.status.in_(["pending", "running"])
    )
    if company_id:
        q = q.where(SyncJob.company_id == company_id)
    result = await db.execute(q)
    return result.scalar_one() or 0


# ── Logging ────────────────────────────────────────────────────────────────────

async def add_log(
    db: AsyncSession,
    job: SyncJob,
    level: str,
    message: str,
    context: dict | None = None,
) -> SyncLog:
    """Append a log entry to the job and commit."""
    entry = SyncLog(
        job_id=job.id,
        level=level,
        message=message,
        context_json=json.dumps(context) if context else None,
    )
    db.add(entry)
    await db.commit()
    return entry


# ── Options helper ─────────────────────────────────────────────────────────────

def parse_options(job: SyncJob) -> dict:
    """Safely parse job_options_json. Returns {} on any error."""
    if not job.job_options_json:
        return {}
    try:
        return json.loads(job.job_options_json)
    except Exception:
        return {}
