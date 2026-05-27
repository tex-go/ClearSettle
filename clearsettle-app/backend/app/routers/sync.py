"""
Sync job management endpoints.

Endpoints
---------
POST   /sync/jobs                  — create + dispatch a new sync job
GET    /sync/jobs                  — list jobs (company-scoped, filterable)
GET    /sync/jobs/{job_id}         — job detail with embedded log entries
POST   /sync/jobs/{job_id}/retry   — re-queue a failed or cancelled job
DELETE /sync/jobs/{job_id}         — cancel a pending job
GET    /sync/types                 — list supported job types
"""
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.rbac import require_db_permission
from app.db.models import PlatformConnection, SyncJob, User
from app.services.sync import job_manager, registry

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Serialiser ────────────────────────────────────────────────────────────────

def _ser_log(log) -> dict:
    ctx = None
    if log.context_json:
        try:
            ctx = json.loads(log.context_json)
        except Exception:
            pass
    return {
        "id":         str(log.id),
        "level":      log.level,
        "message":    log.message,
        "context":    ctx,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _ser_job(job: SyncJob, *, include_logs: bool = True) -> dict:
    return {
        "id":               str(job.id),
        "connection_id":    str(job.connection_id),
        "company_id":       str(job.company_id) if job.company_id else None,
        "platform":         job.platform,
        "job_type":         job.job_type,
        "triggered_by":     job.triggered_by or "manual",
        "status":           job.status,
        "retry_count":      job.retry_count or 0,
        "max_retries":      job.max_retries or 3,
        "records_created":  job.records_created or 0,
        "records_updated":  job.records_updated or 0,
        "duration_seconds": job.duration_seconds,
        "error_message":    job.error_message,
        "scheduled_at":     job.scheduled_at.isoformat() if job.scheduled_at else None,
        "started_at":       job.started_at.isoformat() if job.started_at else None,
        "completed_at":     job.completed_at.isoformat() if job.completed_at else None,
        "created_at":       job.created_at.isoformat() if job.created_at else None,
        "logs":             [_ser_log(l) for l in (job.logs or [])] if include_logs else [],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _company(user: User):
    company = user.companies[0] if getattr(user, "companies", None) else None
    if not company:
        raise HTTPException(status_code=400, detail="No company found for this user")
    return company


async def _resolve_connection(
    db: AsyncSession,
    connection_id: str,
    company_id,
) -> PlatformConnection:
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.id         == UUID(connection_id),
            PlatformConnection.company_id == company_id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


async def _get_owned_job(db: AsyncSession, job_id: str, company_id) -> SyncJob:
    job = await job_manager.get_job(db, UUID(job_id))
    if not job or job.company_id != company_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Create + dispatch ─────────────────────────────────────────────────────────

@router.post("/jobs", status_code=202)
async def create_sync_job(
    connection_id: str,
    job_type: str,
    background_tasks: BackgroundTasks,
    days_back: int = Query(default=30, ge=1, le=365),
    triggered_by: str = Query(default="manual"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("sync:trigger")),
):
    """
    Create a sync job and immediately dispatch it to the background.

    Returns the created job (status=pending) with HTTP 202.
    """
    if job_type not in registry.VALID_JOB_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job_type '{job_type}'. Valid: {sorted(registry.VALID_JOB_TYPES)}",
        )

    company = _company(current_user)
    conn    = await _resolve_connection(db, connection_id, company.id)

    if conn.status != "connected":
        raise HTTPException(
            status_code=400,
            detail=f"Connection is '{conn.status}' — must be 'connected' to sync",
        )

    job = await job_manager.create_job(
        db,
        connection_id=conn.id,
        company_id=company.id,
        platform=conn.platform,
        job_type=job_type,
        triggered_by=triggered_by,
        job_options={"days_back": days_back},
    )

    background_tasks.add_task(registry.dispatch, job_type, str(job.id))
    return _ser_job(job, include_logs=False)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_sync_jobs(
    platform:     Optional[str] = Query(default=None),
    status:       Optional[str] = Query(default=None),
    job_type:     Optional[str] = Query(default=None),
    connection_id: Optional[str] = Query(default=None),
    limit:  int = Query(default=20, le=100),
    offset: int = Query(default=0,  ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("sync:read")),
):
    """List sync jobs scoped to the current user's company."""
    company = _company(current_user)

    jobs = await job_manager.list_jobs(
        db,
        company_id=company.id,
        connection_id=UUID(connection_id) if connection_id else None,
        platform=platform,
        status=status,
        job_type=job_type,
        limit=limit,
        offset=offset,
    )
    return [_ser_job(j, include_logs=False) for j in jobs]


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
async def get_sync_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("sync:read")),
):
    """Return full job detail including all log entries."""
    company = _company(current_user)
    job     = await _get_owned_job(db, job_id, company.id)
    return _ser_job(job, include_logs=True)


# ── Retry ─────────────────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/retry", status_code=202)
async def retry_sync_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("sync:trigger")),
):
    """
    Re-queue a failed or cancelled job.

    Resets retry_count, error_message, and timing fields so the orchestrator
    runs a fresh attempt.
    """
    company = _company(current_user)
    job     = await _get_owned_job(db, job_id, company.id)

    if job.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Only failed or cancelled jobs can be retried (current: '{job.status}')",
        )

    # Reset for a clean retry
    job.status           = "pending"
    job.error_message    = None
    job.started_at       = None
    job.completed_at     = None
    job.duration_seconds = None
    job.retry_count      = 0
    db.add(job)
    await db.commit()

    background_tasks.add_task(registry.dispatch, job.job_type, str(job.id))
    return {"status": "queued", "job_id": str(job.id), "message": "Job re-queued for retry"}


# ── Cancel ────────────────────────────────────────────────────────────────────

@router.delete("/jobs/{job_id}")
async def cancel_sync_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("sync:trigger")),
):
    """Cancel a pending job. Running jobs cannot be cancelled in the current architecture."""
    company = _company(current_user)
    job     = await _get_owned_job(db, job_id, company.id)

    if job.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending jobs can be cancelled (current: '{job.status}')",
        )

    await job_manager.cancel_job(db, job)
    return {"status": "cancelled", "job_id": str(job.id)}


# ── Supported types ───────────────────────────────────────────────────────────

@router.get("/types")
def list_job_types():
    """Return the supported job type strings."""
    return {"job_types": sorted(registry.VALID_JOB_TYPES)}
