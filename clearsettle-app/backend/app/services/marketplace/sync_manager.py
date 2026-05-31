"""
MarketplaceSyncManager — create and execute sync jobs.

The sync manager:
  1. Creates a MarketplaceSyncJob row with status='queued'
  2. Calls provider.start_sync()
  3. Updates the job status and connection metadata on completion

All DB writes are flushed but NOT committed by this module.
The caller commits after receiving the SyncJob result.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.marketplace_connection import (
    MarketplaceConnection,
    MarketplaceSyncJob,
    MarketplaceSyncLog,
)
from app.services.marketplace import audit_service
from app.services.marketplace.abstract_provider import SyncResult
from app.services.marketplace.audit_service import AuditAction

logger = logging.getLogger(__name__)


async def create_and_run_sync(
    connection_id:  UUID,
    company_id:     UUID,
    sync_type:      str,
    db:             AsyncSession,
    *,
    date_from:      Optional[datetime] = None,
    date_to:        Optional[datetime] = None,
    triggered_by:   Optional[str] = None,
    ip_address:     Optional[str] = None,
) -> MarketplaceSyncJob:
    """
    Create a sync job and run it synchronously (async).
    Returns the completed/failed SyncJob row (not committed).
    """
    from app.services.marketplace.provider_registry import get_provider

    conn = (await db.execute(
        select(MarketplaceConnection)
        .where(
            MarketplaceConnection.id         == connection_id,
            MarketplaceConnection.company_id == company_id,
            MarketplaceConnection.deleted_at.is_(None),
        )
        .options(
            selectinload(MarketplaceConnection.marketplace),
            selectinload(MarketplaceConnection.credentials),
        )
    )).scalar_one_or_none()

    if conn is None:
        raise ValueError(f"Connection {connection_id} not found.")
    if conn.status != "connected":
        raise ValueError(
            f"Cannot sync: connection status is '{conn.status}' (must be 'connected')."
        )

    # ── Create the job row ─────────────────────────────────────────────────────
    job = MarketplaceSyncJob(
        connection_id = connection_id,
        sync_type     = sync_type,
        status        = "queued",
        triggered_by  = triggered_by,
        date_from     = date_from,
        date_to       = date_to,
    )
    db.add(job)
    await db.flush()

    await audit_service.record(
        db, AuditAction.SYNC_STARTED,
        company_id    = company_id,
        connection_id = connection_id,
        new_value     = {"sync_type": sync_type, "job_id": str(job.id)},
        ip_address    = ip_address,
    )

    # ── Run the sync ───────────────────────────────────────────────────────────
    job.status     = "running"
    job.started_at = datetime.utcnow()
    await db.flush()

    provider = get_provider(conn.marketplace.slug)
    result: SyncResult

    try:
        result = await provider.start_sync(conn, conn.credentials, job)
        job.status        = "completed" if result.success else "failed"
        job.items_synced  = result.items_synced
        job.items_failed  = result.items_failed
        job.error_message = result.error
        job.meta          = result.meta
    except Exception as exc:
        logger.exception("Sync failed for connection %s", connection_id)
        job.status        = "failed"
        job.error_message = str(exc)
        result = SyncResult(success=False, error=str(exc))
    finally:
        job.completed_at = datetime.utcnow()

    # ── Update connection sync metadata ────────────────────────────────────────
    conn.last_sync_at     = datetime.utcnow()
    conn.last_sync_status = job.status
    conn.last_sync_error  = job.error_message
    if job.status == "completed":
        conn.total_syncs = (conn.total_syncs or 0) + 1

    action = AuditAction.SYNC_COMPLETED if job.status == "completed" else AuditAction.SYNC_FAILED
    await audit_service.record(
        db, action,
        company_id    = company_id,
        connection_id = connection_id,
        new_value     = {
            "job_id":      str(job.id),
            "items_synced": job.items_synced,
            "items_failed": job.items_failed,
        },
    )

    await db.flush()
    return job


async def append_log(
    db:            AsyncSession,
    sync_job_id:   UUID,
    connection_id: UUID,
    event:         str,
    *,
    log_level:     str = "info",
    message:       Optional[str] = None,
    extra:         Optional[dict] = None,
) -> None:
    """Append a structured log entry to a running sync job."""
    log = MarketplaceSyncLog(
        sync_job_id   = sync_job_id,
        connection_id = connection_id,
        log_level     = log_level,
        event         = event,
        message       = message,
        extra         = extra,
        created_at    = datetime.utcnow(),
    )
    db.add(log)


async def list_sync_jobs(
    connection_id: UUID,
    db:            AsyncSession,
    *,
    limit: int = 20,
) -> list[MarketplaceSyncJob]:
    jobs = (await db.execute(
        select(MarketplaceSyncJob)
        .where(MarketplaceSyncJob.connection_id == connection_id)
        .order_by(MarketplaceSyncJob.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return list(jobs)
