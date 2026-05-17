"""
SP API router — complete OAuth + sync lifecycle.

Endpoints
---------
GET  /sp-api/authorize                    → returns Amazon OAuth URL
GET  /sp-api/callback                     → OAuth code → tokens → DB
POST /sp-api/connections/{id}/refresh     → force token refresh
GET  /sp-api/connections/{id}/status      → connection health + token info
POST /sp-api/connections/{id}/sync/orders → fetch & store orders (bg task)
POST /sp-api/connections/{id}/sync/settlements → financial events
GET  /sp-api/connections/{id}/sync-jobs   → sync audit log
DELETE /sp-api/connections/{id}           → revoke + disconnect
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import encrypt, decrypt
from app.core.deps import get_db, require_db_user
from app.db.models import PlatformConnection, SyncJob, User
from app.services.sp_api_client import (
    build_authorization_url,
    exchange_code_for_tokens,
    fetch_financial_events,
    fetch_orders,
    generate_oauth_state,
    get_valid_access_token,
)

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
    selling_partner_id: Optional[str]
    marketplace_id: Optional[str]
    token_expires_at: Optional[datetime]
    token_valid: bool
    last_sync_at: Optional[datetime]
    total_orders_synced: int
    last_sync_error: Optional[str]


class SyncResult(BaseModel):
    job_id: str
    status: str
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_connection(connection_id: str, db: Session, user: User) -> PlatformConnection:
    conn = (
        db.query(PlatformConnection)
        .join(PlatformConnection.company)
        .filter(
            PlatformConnection.id == UUID(connection_id),
            PlatformConnection.company.has(user_id=user.id),
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


def _start_sync_job(db: Session, connection_id, job_type: str) -> SyncJob:
    job = SyncJob(
        connection_id=connection_id,
        job_type=job_type,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _finish_sync_job(db: Session, job: SyncJob, records: int = 0, error: str = None):
    job.completed_at = datetime.utcnow()
    job.status = "failed" if error else "completed"
    job.records_synced = records
    job.error_message = error
    db.add(job)
    db.commit()


# ── Step 1: Initiate OAuth ────────────────────────────────────────────────────

@router.get("/authorize", response_model=AuthorizeResponse)
def initiate_oauth(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    """
    Returns the Amazon Seller Central authorization URL.
    Frontend redirects the user to this URL.
    A new PlatformConnection row (status=oauth_pending) is created to hold
    the CSRF state token.
    """
    s = get_settings()
    if not s.sp_api_app_id or not s.sp_api_client_id:
        raise HTTPException(
            status_code=503,
            detail="Amazon SP API credentials not configured on this server. "
                   "Set SP_API_APP_ID, SP_API_CLIENT_ID, SP_API_CLIENT_SECRET, "
                   "SP_API_REDIRECT_URI environment variables.",
        )

    company = current_user.companies[0] if current_user.companies else None
    if not company:
        raise HTTPException(status_code=400, detail="No company found for this user")

    # Reuse existing pending connection or create a new one
    conn = (
        db.query(PlatformConnection)
        .filter_by(company_id=company.id, platform="amazon")
        .first()
    )
    if not conn:
        conn = PlatformConnection(company_id=company.id, platform="amazon")
        db.add(conn)

    state = generate_oauth_state()
    conn.oauth_state = state
    conn.status = "oauth_pending"
    conn.sp_client_id = s.sp_api_client_id
    conn.sp_client_secret_enc = encrypt(s.sp_api_client_secret)
    conn.sp_marketplace_id = s.sp_api_marketplace_id
    conn.sp_region = s.sp_api_region
    conn.sp_endpoint = s.sp_api_endpoint
    db.commit()
    db.refresh(conn)

    auth_url = build_authorization_url(state)
    return AuthorizeResponse(
        authorization_url=auth_url,
        state=state,
        connection_id=str(conn.id),
    )


# ── Step 2: OAuth Callback ────────────────────────────────────────────────────

@router.get("/callback")
def oauth_callback(
    state: str = Query(...),
    spapi_oauth_code: str = Query(...),
    selling_partner_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Amazon redirects here after the seller grants consent.
    Exchanges the code for tokens, stores them encrypted, marks connection active.
    Redirects the browser to the frontend Platform Settings page.
    """
    # Validate CSRF state
    conn = db.query(PlatformConnection).filter_by(oauth_state=state).first()
    if not conn:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state — possible CSRF attack or session expired",
        )

    try:
        tokens = exchange_code_for_tokens(spapi_oauth_code)
    except Exception as exc:
        conn.status = "error"
        conn.last_sync_error = f"Token exchange failed: {exc}"
        db.commit()
        logger.error("SP API token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {exc}")

    from datetime import timedelta
    conn.sp_selling_partner_id = selling_partner_id
    conn.sp_refresh_token_enc = encrypt(tokens["refresh_token"])
    conn.sp_access_token_enc = encrypt(tokens["access_token"])
    conn.sp_access_token_expires_at = datetime.utcnow() + timedelta(
        seconds=tokens.get("expires_in", 3600)
    )
    conn.oauth_state = None          # clear CSRF token
    conn.status = "connected"
    conn.updated_at = datetime.utcnow()
    db.commit()

    logger.info(
        "SP API connected: selling_partner_id=%s connection_id=%s",
        selling_partner_id,
        conn.id,
    )

    # Redirect browser back to frontend
    frontend_url = get_settings().frontend_url
    from fastapi.responses import RedirectResponse
    return RedirectResponse(
        url=f"{frontend_url}/platforms?connected=amazon&status=success",
        status_code=302,
    )


# ── Token Refresh ─────────────────────────────────────────────────────────────

@router.post("/connections/{connection_id}/refresh")
def force_token_refresh(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    """Force-refresh the SP API access token for a connection."""
    conn = _get_connection(connection_id, db, current_user)
    if conn.platform != "amazon":
        raise HTTPException(status_code=400, detail="Token refresh only applies to Amazon SP API")

    try:
        get_valid_access_token(conn)
        db.commit()
        return {"status": "refreshed", "expires_at": conn.sp_access_token_expires_at}
    except Exception as exc:
        conn.status = "error"
        conn.last_sync_error = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc))


# ── Connection Status ─────────────────────────────────────────────────────────

@router.get("/connections/{connection_id}/status", response_model=ConnectionStatus)
def get_connection_status(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = _get_connection(connection_id, db, current_user)
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


# ── Sync: Orders (background task) ───────────────────────────────────────────

def _bg_sync_orders(connection_id: str, job_id: str, days_back: int):
    """Background task: fetch orders from SP API and update sync state."""
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        conn = db.query(PlatformConnection).get(UUID(connection_id))
        job = db.query(SyncJob).get(UUID(job_id))
        if not conn or not job:
            return

        orders = fetch_orders(conn, db, days_back=days_back)

        conn.last_sync_at = datetime.utcnow()
        conn.total_orders_synced = (conn.total_orders_synced or 0) + len(orders)
        conn.last_sync_error = None
        db.add(conn)

        _finish_sync_job(db, job, records=len(orders))
        logger.info("Orders sync completed: %d records, connection %s", len(orders), connection_id)
    except Exception as exc:
        logger.error("Orders sync failed for connection %s: %s", connection_id, exc)
        try:
            job = db.query(SyncJob).get(UUID(job_id))
            conn = db.query(PlatformConnection).get(UUID(connection_id))
            if job:
                _finish_sync_job(db, job, error=str(exc))
            if conn:
                conn.status = "error"
                conn.last_sync_error = str(exc)
                db.add(conn)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/connections/{connection_id}/sync/orders", response_model=SyncResult)
def sync_orders(
    connection_id: str,
    background_tasks: BackgroundTasks,
    days_back: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = _get_connection(connection_id, db, current_user)
    if conn.status != "connected":
        raise HTTPException(
            status_code=400,
            detail=f"Connection is '{conn.status}' — must be 'connected' to sync",
        )

    job = _start_sync_job(db, conn.id, "orders")
    background_tasks.add_task(_bg_sync_orders, str(conn.id), str(job.id), days_back)

    return SyncResult(
        job_id=str(job.id),
        status="running",
        message=f"Sync started — fetching orders for last {days_back} days",
    )


# ── Sync: Financial Events ────────────────────────────────────────────────────

def _bg_sync_financial_events(connection_id: str, job_id: str, days_back: int):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        conn = db.query(PlatformConnection).get(UUID(connection_id))
        job = db.query(SyncJob).get(UUID(job_id))
        if not conn or not job:
            return

        result = fetch_financial_events(conn, db, days_back=days_back)
        groups = result.get("financial_event_groups", [])

        conn.last_sync_at = datetime.utcnow()
        conn.last_sync_error = None
        db.add(conn)

        _finish_sync_job(db, job, records=len(groups))
    except Exception as exc:
        logger.error("Financial events sync failed for connection %s: %s", connection_id, exc)
        try:
            job = db.query(SyncJob).get(UUID(job_id))
            if job:
                _finish_sync_job(db, job, error=str(exc))
        except Exception:
            pass
    finally:
        db.close()


@router.post("/connections/{connection_id}/sync/settlements", response_model=SyncResult)
def sync_settlements(
    connection_id: str,
    background_tasks: BackgroundTasks,
    days_back: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = _get_connection(connection_id, db, current_user)
    if conn.status != "connected":
        raise HTTPException(status_code=400, detail="Connection must be 'connected' to sync")

    job = _start_sync_job(db, conn.id, "settlements")
    background_tasks.add_task(_bg_sync_financial_events, str(conn.id), str(job.id), days_back)

    return SyncResult(
        job_id=str(job.id),
        status="running",
        message=f"Settlement sync started for last {days_back} days",
    )


# ── Sync Jobs Audit Log ───────────────────────────────────────────────────────

@router.get("/connections/{connection_id}/sync-jobs")
def list_sync_jobs(
    connection_id: str,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = _get_connection(connection_id, db, current_user)
    jobs = (
        db.query(SyncJob)
        .filter_by(connection_id=conn.id)
        .order_by(SyncJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(j.id),
            "job_type": j.job_type,
            "status": j.status,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "records_synced": j.records_synced,
            "error_message": j.error_message,
            "created_at": j.created_at,
        }
        for j in jobs
    ]


# ── Disconnect ────────────────────────────────────────────────────────────────

@router.delete("/connections/{connection_id}")
def disconnect(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = _get_connection(connection_id, db, current_user)
    conn.sp_refresh_token_enc = None
    conn.sp_access_token_enc = None
    conn.sp_access_token_expires_at = None
    conn.sp_client_secret_enc = None
    conn.sp_selling_partner_id = None
    conn.oauth_state = None
    conn.status = "disconnected"
    conn.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "disconnected", "platform": conn.platform}
