"""
SP API router — async version.

All endpoints use AsyncSession.  Background sync tasks are async coroutines
so FastAPI awaits them inside the running event loop.

Credential resolution
---------------------
SP API credentials (app_id, client_id, client_secret, redirect_uri) are stored
per-company in the `platform_connections` row.  The new POST /config endpoint
lets users supply credentials via the UI.  When a DB-stored credential is found
it takes precedence over the corresponding environment variable.

Endpoints
---------
POST /sp-api/config                        — store SP API app credentials
GET  /sp-api/authorize                     — initiate OAuth (DB creds or env fallback)
GET  /sp-api/callback                      — OAuth callback (uses DB-stored creds)
POST /sp-api/connections/{id}/refresh      — force token refresh
GET  /sp-api/connections/{id}/status       — connection health
POST /sp-api/connections/{id}/sync/orders
POST /sp-api/connections/{id}/sync/settlements
GET  /sp-api/connections/{id}/sync-jobs
DELETE /sp-api/connections/{id}
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.core.deps import get_db, require_db_user
from app.db.models import PlatformConnection, User
from app.services.amazon.auth import (
    build_authorization_url,
    exchange_code_for_tokens,
    generate_oauth_state,
    get_valid_access_token,
)
from app.services.sync import job_manager, registry

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SpApiConfigRequest(BaseModel):
    app_id:         str
    client_id:      str
    client_secret:  str
    redirect_uri:   str
    marketplace_id: str = "A21TJRUUN4KGV"
    region:         str = "eu"
    endpoint:       str = "https://sellingpartnerapi-eu.amazon.com"


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
    credentials_configured: bool = False


class SyncResult(BaseModel):
    job_id: str
    status: str
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_connection(company_id, db: AsyncSession) -> PlatformConnection:
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.company_id == company_id,
            PlatformConnection.platform   == "amazon",
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        conn = PlatformConnection(company_id=company_id, platform="amazon")
        db.add(conn)
        await db.flush()
    return conn


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


def _resolve_client_secret(conn: PlatformConnection) -> Optional[str]:
    """Decrypt and return the stored client secret, or None."""
    if conn.sp_client_secret_enc:
        try:
            return decrypt(conn.sp_client_secret_enc)
        except Exception:
            pass
    return None


def _credentials_configured(conn: PlatformConnection) -> bool:
    """True if the connection has app_id + client credentials stored."""
    s = get_settings()
    has_app_id    = bool(conn.sp_app_id or s.sp_api_app_id)
    has_client_id = bool(conn.sp_client_id or s.sp_api_client_id)
    has_secret    = bool(conn.sp_client_secret_enc or s.sp_api_client_secret)
    return has_app_id and has_client_id and has_secret


# ── Step 0: Configure credentials via UI ─────────────────────────────────────

@router.post("/config")
async def configure_sp_api_credentials(
    body: SpApiConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    """
    Store Amazon SP API developer credentials for this company.

    Call this endpoint BEFORE starting the OAuth flow.  Credentials are stored
    encrypted in the database — no environment variables are required after this.

    Required fields:
        app_id        — SP API Application ID from the developer console
                        (amzn1.sellerapps.app.xxx)
        client_id     — LWA Client ID (amzn1.application-oa2-client.xxx)
        client_secret — LWA Client Secret
        redirect_uri  — OAuth redirect URI registered in the developer console
                        (must match exactly what Amazon has on file)
    """
    company = current_user.companies[0] if current_user.companies else None
    if not company:
        raise HTTPException(status_code=400, detail="No company found for this user")

    conn = await _get_or_create_connection(company.id, db)

    conn.sp_app_id            = body.app_id
    conn.sp_client_id         = body.client_id
    conn.sp_client_secret_enc = encrypt(body.client_secret)
    conn.sp_redirect_uri      = body.redirect_uri
    conn.sp_marketplace_id    = body.marketplace_id
    conn.sp_region            = body.region
    conn.sp_endpoint          = body.endpoint

    if conn.status == "disconnected":
        conn.status = "configured"   # credentials set, OAuth not yet done

    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    return {
        "status": "configured",
        "connection_id": str(conn.id),
        "platform": "amazon",
        "message": "SP API credentials saved. You can now start the OAuth flow via GET /sp-api/authorize",
    }


# ── Step 1: Initiate OAuth ────────────────────────────────────────────────────

@router.get("/authorize", response_model=AuthorizeResponse)
async def initiate_oauth(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    """
    Start the Amazon OAuth flow.

    Credentials are resolved in this order:
      1. Values stored in the platform_connections row (via POST /sp-api/config)
      2. Environment variables (SP_API_APP_ID, SP_API_CLIENT_ID, etc.)

    Returns the authorization URL to redirect the user's browser to.
    """
    company = current_user.companies[0] if current_user.companies else None
    if not company:
        raise HTTPException(status_code=400, detail="No company found for this user")

    conn = await _get_or_create_connection(company.id, db)
    s = get_settings()

    # Resolve credentials: DB row takes priority, env vars are fallback
    app_id      = conn.sp_app_id    or s.sp_api_app_id
    client_id   = conn.sp_client_id or s.sp_api_client_id
    client_secret_raw = _resolve_client_secret(conn) or s.sp_api_client_secret
    redirect_uri = conn.sp_redirect_uri or s.sp_api_redirect_uri

    if not app_id or not client_id or not client_secret_raw:
        raise HTTPException(
            status_code=503,
            detail=(
                "Amazon SP API credentials not configured. "
                "Use POST /sp-api/config to provide app_id, client_id, client_secret, and redirect_uri. "
                "Alternatively, set SP_API_APP_ID, SP_API_CLIENT_ID, SP_API_CLIENT_SECRET, "
                "SP_API_REDIRECT_URI as environment variables."
            ),
        )

    state = generate_oauth_state()
    conn.oauth_state          = state
    conn.status               = "oauth_pending"
    conn.sp_client_id         = client_id
    conn.sp_client_secret_enc = encrypt(client_secret_raw)
    conn.sp_marketplace_id    = conn.sp_marketplace_id or s.sp_api_marketplace_id
    conn.sp_region            = conn.sp_region    or s.sp_api_region
    conn.sp_endpoint          = conn.sp_endpoint  or s.sp_api_endpoint
    conn.sp_app_id            = app_id
    conn.sp_redirect_uri      = redirect_uri
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    auth_url = build_authorization_url(
        state,
        app_id=app_id,
        redirect_uri=redirect_uri,
    )

    return AuthorizeResponse(
        authorization_url=auth_url,
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

    # Use credentials stored in the connection row (set during /authorize)
    client_id     = conn.sp_client_id
    client_secret = _resolve_client_secret(conn)
    redirect_uri  = conn.sp_redirect_uri

    # Fallback to env vars in case this is a legacy connection
    s = get_settings()
    client_id     = client_id     or s.sp_api_client_id
    client_secret = client_secret or s.sp_api_client_secret
    redirect_uri  = redirect_uri  or s.sp_api_redirect_uri

    try:
        tokens = exchange_code_for_tokens(
            spapi_oauth_code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except Exception as exc:
        conn.status = "error"
        conn.last_sync_error = f"Token exchange failed: {exc}"
        db.add(conn)
        await db.commit()
        logger.error("SP API token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {exc}")

    conn.sp_selling_partner_id      = selling_partner_id
    conn.sp_refresh_token_enc       = encrypt(tokens["refresh_token"])
    conn.sp_access_token_enc        = encrypt(tokens["access_token"])
    conn.sp_access_token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))
    conn.oauth_state                = None
    conn.status                     = "connected"
    conn.updated_at                 = datetime.utcnow()
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

    try:
        get_valid_access_token(conn)
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
        credentials_configured=_credentials_configured(conn),
    )


# ── Sync: Orders ──────────────────────────────────────────────────────────────

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

    company = current_user.companies[0]
    job = await job_manager.create_job(
        db,
        connection_id=conn.id,
        company_id=company.id,
        platform=conn.platform,
        job_type="orders",
        triggered_by="manual",
        job_options={"days_back": days_back},
    )
    background_tasks.add_task(registry.dispatch, "orders", str(job.id))
    return SyncResult(job_id=str(job.id), status="pending", message=f"Fetching orders for last {days_back} days")


# ── Sync: Settlements ─────────────────────────────────────────────────────────

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

    company = current_user.companies[0]
    job = await job_manager.create_job(
        db,
        connection_id=conn.id,
        company_id=company.id,
        platform=conn.platform,
        job_type="settlements",
        triggered_by="manual",
        job_options={"days_back": days_back},
    )
    background_tasks.add_task(registry.dispatch, "settlements", str(job.id))
    return SyncResult(job_id=str(job.id), status="pending", message=f"Settlement sync started for last {days_back} days")


# ── Sync job audit log ────────────────────────────────────────────────────────

@router.get("/connections/{connection_id}/sync-jobs")
async def list_connection_sync_jobs(
    connection_id: str,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    conn = await _get_connection(connection_id, db, current_user)
    company = current_user.companies[0] if current_user.companies else None
    company_id = company.id if company else None
    jobs = await job_manager.list_jobs(db, connection_id=conn.id, company_id=company_id, limit=limit)
    return [
        {
            "id":               str(j.id),
            "job_type":         j.job_type,
            "triggered_by":     j.triggered_by or "manual",
            "status":           j.status,
            "retry_count":      j.retry_count or 0,
            "max_retries":      j.max_retries or 3,
            "started_at":       j.started_at,
            "completed_at":     j.completed_at,
            "duration_seconds": j.duration_seconds,
            "records_created":  j.records_created or 0,
            "records_synced":   j.records_synced or 0,
            "error_message":    j.error_message,
            "created_at":       j.created_at,
        }
        for j in jobs
    ]


# ── Test connection ───────────────────────────────────────────────────────────

@router.get("/test-connection")
async def test_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_user),
):
    """
    Verify Amazon SP API connectivity for the current user's company.

    Calls GET /sellers/v1/marketplaceParticipations and returns structured
    connectivity status.  Automatically refreshes the access token if needed.

    Returns:
        {
          "status": "connected",
          "marketplace": "IN",
          "sp_api_access": true,
          ...
        }
    """
    company = current_user.companies[0] if current_user.companies else None
    if not company:
        raise HTTPException(status_code=400, detail="No company found for this user")

    conn = await _get_or_create_connection(company.id, db)

    if not conn.sp_refresh_token_enc:
        raise HTTPException(
            status_code=400,
            detail=(
                "No refresh token stored. "
                "Complete the OAuth flow via GET /sp-api/authorize first."
            ),
        )

    if conn.status != "connected":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Connection status is '{conn.status}'. "
                "Must be 'connected' to test. Complete the OAuth flow via GET /sp-api/authorize."
            ),
        )

    # Refresh the access token in a thread (get_valid_access_token is synchronous)
    try:
        access_token = await asyncio.to_thread(get_valid_access_token, conn)
        db.add(conn)
        await db.commit()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Token refresh failed: {exc}")

    endpoint = conn.sp_endpoint or get_settings().sp_api_endpoint or "https://sellingpartnerapi-eu.amazon.com"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{endpoint}/sellers/v1/marketplaceParticipations",
                headers={
                    "x-amz-access-token": access_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="SP API request timed out (>30s)")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Network error reaching SP API: {exc}")

    if resp.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="SP API rejected the access token. Try refreshing via POST /sp-api/connections/{id}/refresh.",
        )
    if resp.status_code == 403:
        raise HTTPException(
            status_code=403,
            detail="SP API returned 403 — check that the app has the Selling Partner Insights role.",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"SP API returned HTTP {resp.status_code}: {resp.text[:300]}",
        )

    payload = resp.json().get("payload", [])
    target_marketplace_id = conn.sp_marketplace_id or get_settings().sp_api_marketplace_id or "A21TJRUUN4KGV"

    marketplaces = []
    primary_country = None

    for item in payload:
        mkt  = item.get("marketplace", {})
        part = item.get("participation", {})
        marketplaces.append({
            "id":                     mkt.get("id"),
            "country":                mkt.get("countryCode"),
            "name":                   mkt.get("name"),
            "currency":               mkt.get("defaultCurrencyCode"),
            "participating":          part.get("isParticipating"),
            "has_suspended_listings": part.get("hasSuspendedListings"),
        })
        if mkt.get("id") == target_marketplace_id:
            primary_country = mkt.get("countryCode")

    if not primary_country and marketplaces:
        primary_country = marketplaces[0]["country"]

    logger.info(
        "SP API test-connection: seller=%s marketplace=%s marketplaces=%d",
        conn.sp_selling_partner_id, primary_country, len(marketplaces),
    )

    return {
        "status":             "connected",
        "marketplace":        primary_country,
        "sp_api_access":      True,
        "selling_partner_id": conn.sp_selling_partner_id,
        "connection_id":      str(conn.id),
        "endpoint":           endpoint,
        "token_expires_at":   conn.sp_access_token_expires_at,
        "marketplaces":       marketplaces,
    }


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
    conn.sp_selling_partner_id     = None
    conn.oauth_state               = None
    conn.status                    = "disconnected"
    conn.updated_at                = datetime.utcnow()
    db.add(conn)
    await db.commit()
    return {"status": "disconnected", "platform": conn.platform}
