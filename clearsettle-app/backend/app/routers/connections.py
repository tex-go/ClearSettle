"""
Connections API — marketplace connection management and on-demand sync.

Prefix: /connections

Endpoints:
  GET    /connections                       — list all marketplace connections for company
  GET    /connections/{id}                  — connection details + health status
  POST   /connections/{id}/sync             — trigger an on-demand sync via the connector
  GET    /connections/{id}/sync-history     — list recent sync executions
  POST   /connections/{id}/validate         — health-check the connection (no data fetch)
  DELETE /connections/{id}                  — disconnect marketplace (revoke tokens)

This router bridges the existing MarketplaceConnection models (migration 032)
with the new connector framework (migration 036).

When POST /connections/{id}/sync is called:
  1. Load MarketplaceConnection + MarketplaceCredentials from DB
  2. Build the appropriate connector (AmazonConnector, FlipkartConnector, …)
     using ConnectorRegistry.build()
  3. Create an UploadedFile record (so the file list stays consistent)
  4. Run LedgerSyncExecutor
  5. Update MarketplaceSyncJob status

This means the dashboard, analytics, and reconciliation layers work identically
whether data came from a file upload or an API sync.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.database import AsyncSessionLocal
from app.db.models.ingestion import IngestionLedger, UploadedFile
from app.db.models.marketplace_connection import (
    MarketplaceConnection,
    MarketplaceSyncJob,
    MarketplaceSyncLog,
)
from app.models.canonical.events import SourceType

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _company_id(user) -> UUID:
    if hasattr(user, "companies") and user.companies:
        return user.companies[0].id
    raise HTTPException(status_code=422, detail="No company associated with this account.")


def _assert_owner(conn: MarketplaceConnection, company_id: UUID) -> None:
    if conn.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")


# ── Serialisers ───────────────────────────────────────────────────────────────

def _conn_to_dict(c: MarketplaceConnection) -> Dict[str, Any]:
    return {
        "id":                   str(c.id),
        "marketplace_id":       str(c.marketplace_id),
        "marketplace_slug":     c.marketplace_slug,
        "status":               c.status,
        "display_name":         c.display_name,
        "seller_id":            c.seller_id,
        "last_sync_at":         c.last_sync_at.isoformat() if c.last_sync_at else None,
        "last_sync_status":     c.last_sync_status,
        "total_syncs":          c.total_syncs,
        "connected_at":         c.connected_at.isoformat() if c.connected_at else None,
        "created_at":           c.created_at.isoformat(),
    }


def _job_to_dict(j: MarketplaceSyncJob) -> Dict[str, Any]:
    return {
        "id":              str(j.id),
        "sync_type":       j.sync_type,
        "status":          j.status,
        "trigger":         j.trigger,
        "started_at":      j.started_at.isoformat() if j.started_at else None,
        "completed_at":    j.completed_at.isoformat() if j.completed_at else None,
        "records_fetched": j.records_fetched,
        "records_stored":  j.records_stored,
        "error_message":   j.error_message,
        "created_at":      j.created_at.isoformat(),
    }


# ── GET /connections ──────────────────────────────────────────────────────────

@router.get("")
async def list_connections(
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all marketplace connections for the authenticated company."""
    company_id = _company_id(user)
    conns = (
        await db.execute(
            select(MarketplaceConnection)
            .where(MarketplaceConnection.company_id == company_id)
            .order_by(desc(MarketplaceConnection.created_at))
        )
    ).scalars().all()
    return {"items": [_conn_to_dict(c) for c in conns], "total": len(conns)}


# ── GET /connections/{id} ─────────────────────────────────────────────────────

@router.get("/{connection_id}")
async def get_connection(
    connection_id: UUID,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get full details for a single marketplace connection."""
    company_id = _company_id(user)
    conn = await db.get(MarketplaceConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    _assert_owner(conn, company_id)

    # Latest sync job
    latest_job = (
        await db.execute(
            select(MarketplaceSyncJob)
            .where(MarketplaceSyncJob.connection_id == connection_id)
            .order_by(desc(MarketplaceSyncJob.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()

    # Ledger stats for this connection
    ledger_count = (
        await db.execute(
            select(IngestionLedger.company_id)  # any column — just counting
            .where(
                IngestionLedger.company_id == company_id,
                IngestionLedger.connection_id == connection_id,
            )
        )
    ).all()

    result = _conn_to_dict(conn)
    result["latest_sync_job"] = _job_to_dict(latest_job) if latest_job else None
    result["ledger_rows"] = len(ledger_count)
    return result


# ── POST /connections/{id}/validate ──────────────────────────────────────────

@router.post("/{connection_id}/validate")
async def validate_connection(
    connection_id: UUID,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Health-check the marketplace connection without fetching any data.
    Useful for verifying credentials are still valid after a long period.
    """
    company_id = _company_id(user)
    conn = await db.get(MarketplaceConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    _assert_owner(conn, company_id)

    connector = _build_connector(conn)
    if connector is None:
        return {
            "connection_id": str(connection_id),
            "platform":      conn.marketplace_slug,
            "ok":            False,
            "message":       f"No connector implemented for {conn.marketplace_slug!r} yet.",
        }

    try:
        ok = await connector.authenticate()
        if not ok:
            return {"connection_id": str(connection_id), "ok": False, "message": "Authentication failed."}

        health = await connector.validate_connection()
        return {
            "connection_id":  str(connection_id),
            "platform":       conn.marketplace_slug,
            "ok":             health.ok,
            "account_name":   health.account_name,
            "marketplace_id": health.marketplace_id,
            "message":        health.message,
        }
    except NotImplementedError:
        return {
            "connection_id": str(connection_id),
            "platform":      conn.marketplace_slug,
            "ok":            False,
            "message":       f"Connector for {conn.marketplace_slug!r} is not yet implemented (Phase 2/3).",
        }
    except Exception as exc:
        return {
            "connection_id": str(connection_id),
            "ok":            False,
            "message":       str(exc)[:300],
        }


# ── POST /connections/{id}/sync ───────────────────────────────────────────────

class SyncRequest(BaseModel):
    sync_type:    str = "settlements"  # settlements | orders | fees | full
    date_from:    Optional[str] = None  # ISO date YYYY-MM-DD
    date_to:      Optional[str] = None
    force_resync: bool = False


@router.post("/{connection_id}/sync", status_code=202)
async def trigger_sync(
    connection_id: UUID,
    body:           SyncRequest,
    background_tasks: BackgroundTasks,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Trigger an on-demand data sync for a marketplace connection.

    The sync runs asynchronously.  Poll GET /connections/{id}/sync-history for status.

    Data flow:
        ConnectorRegistry.build(platform) → IngestionConnector
        ↓  connector.fetch_canonical_events()
        ↓  LedgerSyncExecutor → ingestion_ledger
        ↓  ETL → settlements + payout_events
        ↓  Dashboard shows new data
    """
    company_id = _company_id(user)
    conn = await db.get(MarketplaceConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    _assert_owner(conn, company_id)

    if conn.status not in ("connected", "error"):
        raise HTTPException(
            status_code=409,
            detail=f"Connection is in state '{conn.status}' — only connected/error connections can sync.",
        )

    # Create a MarketplaceSyncJob record
    job = MarketplaceSyncJob(
        id=uuid.uuid4(),
        connection_id=connection_id,
        company_id=company_id,
        sync_type=body.sync_type,
        status="pending",
        trigger="manual",
        created_at=datetime.utcnow(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(
        _run_api_sync,
        job_id=job.id,
        connection_id=connection_id,
        company_id=company_id,
        sync_type=body.sync_type,
        date_from_str=body.date_from,
        date_to_str=body.date_to,
    )

    return {
        "sync_job_id":   str(job.id),
        "connection_id": str(connection_id),
        "platform":      conn.marketplace_slug,
        "status":        "pending",
        "message":       (
            f"Sync started for {conn.marketplace_slug}. "
            f"Poll GET /connections/{connection_id}/sync-history for status."
        ),
    }


# ── GET /connections/{id}/sync-history ───────────────────────────────────────

@router.get("/{connection_id}/sync-history")
async def get_sync_history(
    connection_id: UUID,
    page:   int = Query(1, ge=1),
    limit:  int = Query(20, ge=1, le=100),
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List recent sync jobs for a connection."""
    company_id = _company_id(user)
    conn = await db.get(MarketplaceConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    _assert_owner(conn, company_id)

    jobs = (
        await db.execute(
            select(MarketplaceSyncJob)
            .where(MarketplaceSyncJob.connection_id == connection_id)
            .order_by(desc(MarketplaceSyncJob.created_at))
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).scalars().all()

    return {"connection_id": str(connection_id), "items": [_job_to_dict(j) for j in jobs]}


# ── DELETE /connections/{id} ─────────────────────────────────────────────────

@router.delete("/{connection_id}", status_code=204)
async def disconnect(
    connection_id: UUID,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Disconnect a marketplace (mark as disconnected; ledger data is preserved)."""
    company_id = _company_id(user)
    conn = await db.get(MarketplaceConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    _assert_owner(conn, company_id)

    conn.status = "disconnected"
    conn.disconnected_at = datetime.utcnow()
    await db.commit()


# ── Background sync task ──────────────────────────────────────────────────────

async def _run_api_sync(
    job_id: UUID,
    connection_id: UUID,
    company_id: UUID,
    sync_type: str,
    date_from_str: Optional[str],
    date_to_str: Optional[str],
) -> None:
    """
    Background task: authenticate connector → fetch events → write ledger → ETL.

    This is the same code path as manual uploads.  The only difference is the
    connector class (AmazonConnector vs ManualUploadConnector).
    """
    if AsyncSessionLocal is None:
        return

    from datetime import timedelta

    async with AsyncSessionLocal() as db:
        job  = await db.get(MarketplaceSyncJob, job_id)
        conn = await db.get(MarketplaceConnection, connection_id)
        if not job or not conn:
            return

        job.status     = "running"
        job.started_at = datetime.utcnow()
        await db.commit()

        try:
            # Parse date range
            date_from = (
                datetime.fromisoformat(date_from_str)
                if date_from_str
                else datetime.utcnow() - timedelta(days=90)
            )
            date_to = (
                datetime.fromisoformat(date_to_str)
                if date_to_str
                else datetime.utcnow()
            )

            # Build connector
            connector = _build_connector(conn)
            if connector is None:
                raise NotImplementedError(
                    f"No connector implemented for {conn.marketplace_slug!r}. "
                    f"Implement {conn.marketplace_slug.title()}Connector (Phase 2/3)."
                )

            # Authenticate
            await connector.authenticate()

            # Create an UploadedFile record so the file list stays consistent
            uploaded_file = UploadedFile(
                id=uuid.uuid4(),
                company_id=company_id,
                original_file_name=f"{conn.marketplace_slug}_api_sync_{date_from.date()}_{date_to.date()}.json",
                file_hash_sha256=str(uuid.uuid4()).replace("-", ""),  # synthetic hash
                upload_source="api_sync",
                upload_status="processing",
                source_type=_source_type_for_slug(conn.marketplace_slug),
            )
            db.add(uploaded_file)
            await db.flush()

            # Run the connector through LedgerSyncExecutor
            from app.services.sync.ledger_executor import LedgerSyncExecutor
            executor = LedgerSyncExecutor()
            result = await executor.run(
                connector=connector,
                company_id=company_id,
                db=db,
                uploaded_file_id=uploaded_file.id,
                connection_id=connection_id,
                sync_job_id=job_id,
                date_from=date_from,
                date_to=date_to,
                run_etl=True,
            )

            # Finalise uploaded_file
            uploaded_file.upload_status = "done" if result.success else "needs_review"
            uploaded_file.processed_at  = datetime.utcnow()

            # Update sync job
            job.status          = "completed" if result.success else "failed"
            job.completed_at    = datetime.utcnow()
            job.records_fetched = result.events_total
            job.records_stored  = result.events_written
            if result.errors:
                job.error_message = "; ".join(result.errors[:3])

            # Update connection last sync
            conn.last_sync_at     = datetime.utcnow()
            conn.last_sync_status = job.status
            conn.total_syncs      = (conn.total_syncs or 0) + 1

            await db.commit()

            logger.info(
                "API sync complete",
                extra={
                    "job_id":            str(job_id),
                    "connection_id":     str(connection_id),
                    "platform":          conn.marketplace_slug,
                    "events_written":    result.events_written,
                    "settlements_created": result.settlements_created,
                    "duration_ms":       result.duration_ms,
                },
            )

        except Exception as exc:
            logger.error(
                "API sync failed",
                extra={
                    "job_id":        str(job_id),
                    "connection_id": str(connection_id),
                    "error":         str(exc)[:300],
                },
                exc_info=True,
            )
            try:
                job.status       = "failed"
                job.completed_at = datetime.utcnow()
                job.error_message = str(exc)[:500]
                conn.last_sync_status = "failed"
                await db.commit()
            except Exception:
                pass


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_connector(conn: MarketplaceConnection):
    """
    Build an IngestionConnector for a MarketplaceConnection.

    Reads credentials from the MarketplaceCredentials table (encrypted).
    Returns None if no connector is registered for this platform yet.

    In Phase 2/3, replace the stubs with real credential loading:
        creds = await credential_service.get_decrypted(conn.id)
        return AmazonConnector(
            company_id=conn.company_id,
            refresh_token=creds["refresh_token"],
            client_id=creds["client_id"],
            ...
        )
    """
    from app.connectors.registry import get_connector_registry
    from app.models.canonical.events import SourceType

    slug   = conn.marketplace_slug.lower()
    st_map = {
        "amazon":    SourceType.AMAZON_API,
        "flipkart":  SourceType.FLIPKART_API,
        "meesho":    SourceType.MEESHO_API,
        "shopify":   SourceType.SHOPIFY_API,
        "woocommerce": SourceType.WOOCOMMERCE,
        "myntra":    SourceType.MYNTRA_API,
        "ajio":      SourceType.AJIO_API,
    }
    source_type = st_map.get(slug)
    if source_type is None:
        return None

    registry = get_connector_registry()
    if not registry.is_supported(source_type, slug):
        return None

    # TODO Phase 2/3: load decrypted credentials from MarketplaceCredentials
    # For now return None — connectors are skeletons and raise NotImplementedError
    return None


def _source_type_for_slug(slug: str) -> str:
    mapping = {
        "amazon": "amazon_api", "flipkart": "flipkart_api",
        "meesho": "meesho_api", "shopify": "shopify_api",
        "woocommerce": "woocommerce", "myntra": "myntra_api", "ajio": "ajio_api",
    }
    return mapping.get(slug.lower(), f"{slug.lower()}_api")
