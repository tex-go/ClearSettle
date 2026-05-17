"""
SP API router — async version.

All endpoints use AsyncSession.  Background sync tasks are async coroutines
so FastAPI awaits them inside the running event loop.

Endpoints
---------
GET  /sp-api/authorize
GET  /sp-api/callback
POST /sp-api/connections/{id}/refresh
GET  /sp-api/connections/{id}/status
POST /sp-api/connections/{id}/sync/orders
POST /sp-api/connections/{id}/sync/settlements
GET  /sp-api/connections/{id}/sync-jobs
DELETE /sp-api/connections/{id}
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.crypto import encrypt
from app.core.deps import get_db, require_db_user
from app.db.models import PlatformConnection, SyncJob, User

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class AuthorizeResponse(BaseModel):
    authorization_url: str
    state: str
    connection_id: str


class ConnectionStatus(BaseModel):
    id: str
    platform: str
    status: str
    selling_partner_id: Optional[str] = None
    marketplace_id: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    token_valid: bool
    last_sync_at: Optional[datetime] = None
    total_orders_synced: int
    last_sync_error: Optional[str] = None


class SyncResult(BaseModel):
    job_id: str
    status: str
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_connection(connection_id: str, db: AsyncSession, user: User) -> PlatformConnection:
    result = await db.execute(
        select(PlatformConnection)
        .join(PlatformConnection.company)
        .where(
            PlatformConnection.id == UUID(connection_id),
            PlatformConnection.company.has(user_id=user.id),
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


async def _start_sync_job(db: AsyncSession, connection_id, job_type: str) -> SyncJob:
    job = SyncJob(
        connection_id=connection_id,
        job_type=job_type,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def _finish_sync_job(db: AsyncSession, job: SyncJob, *, records: int = 0, error: str | None = None):
    job.completed_at = datetime.utcnow()
    job.status = "failed" if error else "completed"
    job.records_synced = records
    job.error_message = error
    db.add(job)
    await db.commit()


# ── Step 1: Initiate OAuth ────────────────────────────────────────────────────

@router.get("/authorize", response_model=AuthorizeResponse)
async def initiate_oauth(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    s = get_settings()
    if not s.sp_api_app_id or not s.sp_api_client_id:
        raise HTTPException(
            status_code=503,
            detail="Amazon SP API credentials not configured. Set SP_API_APP_ID, SP_API_CLIENT_ID, "
                   "SP_API_CLIENT_SECRET, SP_API_REDIRECT_URI.",
        )

    company = current_user.companies[0] if current_user.companies else None
    if not company:
        raise HTTPException(status_code=400, detail="No company found for this user")

    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.company_id == company.id,
            PlatformConnection.platform   == "amazon",
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        conn = PlatformConnection(company_id=company.id, platform="amazon")
        db.add(conn)

    from app.services.sp_api_client import generate_oauth_state, build_authorization_url
    state = generate_oauth_state()
    conn.oauth_state          = state
    conn.status               = "oauth_pending"
    conn.sp_client_id         = s.sp_api_client_id
    conn.sp_client_secret_enc = encrypt(s.sp_api_client_secret)
    conn.sp_marketplace_id    = s.sp_api_marketplace_id
    conn.sp_region            = s.sp_api_region
    conn.sp_endpoint          = s.sp_api_endpoint
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    return AuthorizeResponse(
        authorization_url=build_authorization_url(state),
        state=state,
        connection_id=str(conn.id),
    )


# ── Step 2: OAuth callback ────────────────────────────────────────────────────

@router.get("/callback")
async def oauth_callback(
    state: str,
    spapi_oauth_code: str,
    selling_partner_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlatformConnection).where(PlatformConnection.oauth_state == state)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=400, detail="Invalid OAuth state — possible CSRF or session expired")

    from app.services.sp_api_client import exchange_code_for_tokens
    try:
        tokens = exchange_code_for_tokens(spapi_oauth_code)
    except Exception as exc:
        conn.status = "error"
        conn.last_sync_error = f"Token exchange failed: {exc}"
        db.add(conn)
        await db.commit()
        logger.error("SP API token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {exc}")

    conn.sp_selling_partner_id     = selling_partner_id
    conn.sp_refresh_token_enc      = encrypt(tokens["refresh_token"])
    conn.sp_access_token_enc       = encrypt(tokens["access_token"])
    conn.sp_access_token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))
    conn.oauth_state               = None
    conn.status                    = "connected"
    conn.updated_at                = datetime.utcnow()
    db.add(conn)
    await db.commit()

    logger.info("SP API connected: seller=%s connection=%s", selling_partner_id, conn.id)
    return RedirectResponse(
        url=f"{get_settings().frontend_url}/platforms?connected=amazon&status=success",
        status_code=302,
    )


# ── Token refresh ─────────────────────────────────────────────────────────────

@router.post("/connections/{connection_id}/refresh")
async def force_token_refresh(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = await _get_connection(connection_id, db, current_user)
    if conn.platform != "amazon":
        raise HTTPException(status_code=400, detail="Token refresh only applies to Amazon SP API")

    from app.services.sp_api_client import get_valid_access_token
    try:
        get_valid_access_token(conn)   # mutates conn in place
        db.add(conn)
        await db.commit()
        return {"status": "refreshed", "expires_at": conn.sp_access_token_expires_at}
    except Exception as exc:
        conn.status = "error"
        conn.last_sync_error = str(exc)
        db.add(conn)
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc))


# ── Connection status ─────────────────────────────────────────────────────────

@router.get("/connections/{connection_id}/status", response_model=ConnectionStatus)
async def get_connection_status(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = await _get_connection(connection_id, db, current_user)
    token_valid = bool(
        conn.sp_access_token_enc
        and conn.sp_access_token_expires_at
        and conn.sp_access_token_expires_at > datetime.utcnow()
    )
    return ConnectionStatus(
        id=str(conn.id),
        platform=conn.platform,
        status=conn.status,
        selling_partner_id=conn.sp_selling_partner_id,
        marketplace_id=conn.sp_marketplace_id,
        token_expires_at=conn.sp_access_token_expires_at,
        token_valid=token_valid,
        last_sync_at=conn.last_sync_at,
        total_orders_synced=conn.total_orders_synced or 0,
        last_sync_error=conn.last_sync_error,
    )


# ── Sync: Orders ──────────────────────────────────────────────────────────────

async def _bg_sync_orders(connection_id: str, job_id: str, days_back: int):
    from app.db.database import AsyncSessionLocal
    if not AsyncSessionLocal:
        return
    async with AsyncSessionLocal() as db:
        from app.services.sp_api_client import fetch_orders, get_valid_access_token
        try:
            conn = await db.get(PlatformConnection, UUID(connection_id))
            job  = await db.get(SyncJob, UUID(job_id))
            if not conn or not job:
                return

            get_valid_access_token(conn)
            db.add(conn)
            await db.commit()

            orders = fetch_orders(conn, days_back=days_back)

            conn.last_sync_at       = datetime.utcnow()
            conn.total_orders_synced = (conn.total_orders_synced or 0) + len(orders)
            conn.last_sync_error    = None
            db.add(conn)

            await _finish_sync_job(db, job, records=len(orders))
            logger.info("Orders sync done: %d records, connection %s", len(orders), connection_id)
        except Exception as exc:
            logger.error("Orders sync failed for %s: %s", connection_id, exc)
            try:
                job  = await db.get(SyncJob, UUID(job_id))
                conn = await db.get(PlatformConnection, UUID(connection_id))
                if job:
                    await _finish_sync_job(db, job, error=str(exc))
                if conn:
                    conn.status = "error"
                    conn.last_sync_error = str(exc)
                    db.add(conn)
                    await db.commit()
            except Exception:
                pass


@router.post("/connections/{connection_id}/sync/orders", response_model=SyncResult)
async def sync_orders(
    connection_id: str,
    background_tasks: BackgroundTasks,
    days_back: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = await _get_connection(connection_id, db, current_user)
    if conn.status != "connected":
        raise HTTPException(status_code=400, detail=f"Connection is '{conn.status}' — must be 'connected' to sync")

    job = await _start_sync_job(db, conn.id, "orders")
    background_tasks.add_task(_bg_sync_orders, str(conn.id), str(job.id), days_back)
    return SyncResult(job_id=str(job.id), status="running", message=f"Fetching orders for last {days_back} days")


# ── Sync: Financial Events ────────────────────────────────────────────────────

async def _bg_sync_financial_events(connection_id: str, job_id: str, days_back: int):
    from app.db.database import AsyncSessionLocal
    if not AsyncSessionLocal:
        return
    async with AsyncSessionLocal() as db:
        from app.services.sp_api_client import fetch_financial_events, get_valid_access_token
        try:
            conn = await db.get(PlatformConnection, UUID(connection_id))
            job  = await db.get(SyncJob, UUID(job_id))
            if not conn or not job:
                return

            get_valid_access_token(conn)
            db.add(conn)
            await db.commit()

            result = fetch_financial_events(conn, days_back=days_back)
            groups = result.get("financial_event_groups", [])

            conn.last_sync_at    = datetime.utcnow()
            conn.last_sync_error = None
            db.add(conn)

            await _finish_sync_job(db, job, records=len(groups))
        except Exception as exc:
            logger.error("Financial events sync failed for %s: %s", connection_id, exc)
            try:
                job = await db.get(SyncJob, UUID(job_id))
                if job:
                    await _finish_sync_job(db, job, error=str(exc))
            except Exception:
                pass


@router.post("/connections/{connection_id}/sync/settlements", response_model=SyncResult)
async def sync_settlements(
    connection_id: str,
    background_tasks: BackgroundTasks,
    days_back: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = await _get_connection(connection_id, db, current_user)
    if conn.status != "connected":
        raise HTTPException(status_code=400, detail="Connection must be 'connected' to sync")

    job = await _start_sync_job(db, conn.id, "settlements")
    background_tasks.add_task(_bg_sync_financial_events, str(conn.id), str(job.id), days_back)
    return SyncResult(job_id=str(job.id), status="running", message=f"Settlement sync started for last {days_back} days")


# ── Sync job audit log ────────────────────────────────────────────────────────

@router.get("/connections/{connection_id}/sync-jobs")
async def list_sync_jobs(
    connection_id: str,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = await _get_connection(connection_id, db, current_user)
    result = await db.execute(
        select(SyncJob)
        .where(SyncJob.connection_id == conn.id)
        .order_by(SyncJob.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id":             str(j.id),
            "job_type":       j.job_type,
            "status":         j.status,
            "started_at":     j.started_at,
            "completed_at":   j.completed_at,
            "records_synced": j.records_synced,
            "error_message":  j.error_message,
            "created_at":     j.created_at,
        }
        for j in result.scalars().all()
    ]


# ── Disconnect ────────────────────────────────────────────────────────────────

@router.delete("/connections/{connection_id}")
async def disconnect(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = await _get_connection(connection_id, db, current_user)
    conn.sp_refresh_token_enc      = None
    conn.sp_access_token_enc       = None
    conn.sp_access_token_expires_at = None
    conn.sp_client_secret_enc      = None
    conn.sp_selling_partner_id     = None
    conn.oauth_state               = None
    conn.status                    = "disconnected"
    conn.updated_at                = datetime.utcnow()
    db.add(conn)
    await db.commit()
    return {"status": "disconnected", "platform": conn.platform}
