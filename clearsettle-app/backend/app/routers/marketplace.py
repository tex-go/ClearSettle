"""
Marketplace Integration Framework — FastAPI router.

Prefix: /marketplace

Endpoints
---------
GET  /marketplace/                                  — list all available marketplaces
GET  /marketplace/connections/                      — list this company's connections
GET  /marketplace/connections/{connection_id}       — single connection detail
POST /marketplace/connections/manual                — connect a manual-upload marketplace
POST /marketplace/connections/credentials           — connect an API-key marketplace
DELETE /marketplace/connections/{marketplace_slug}  — disconnect

POST /marketplace/oauth/initiate                    — start OAuth flow (returns authorization_url)
GET  /marketplace/oauth/callback                    — OAuth provider redirect target
POST /marketplace/oauth/callback                    — same as GET (some providers POST)

POST /marketplace/connections/{connection_id}/sync  — trigger sync job
GET  /marketplace/connections/{connection_id}/jobs  — list sync jobs
POST /marketplace/connections/{connection_id}/validate — validate credentials live

GET  /marketplace/admin/connections                 — super-admin: all company connections
GET  /marketplace/audit/{connection_id}             — audit log for a connection

Security
--------
All mutating endpoints require 'platforms:write' permission.
Read endpoints require 'platforms:read' permission.
Admin endpoints require is_superadmin.
CSRF state tokens validated on OAuth callback.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.rbac import require_permission
from app.db.models.marketplace_connection import Marketplace, MarketplaceAuditLog
from app.schemas.marketplace import (
    AuditLogOut,
    ConnectionCheckResult,
    CredentialConnectRequest,
    DisconnectResponse,
    ManualConnectionRequest,
    MarketplaceConnectionListResponse,
    MarketplaceConnectionOut,
    MarketplaceOut,
    OAuthCallbackResponse,
    OAuthInitRequest,
    OAuthInitResponse,
    SyncJobListResponse,
    SyncJobOut,
    SyncRequest,
    ValidateConnectionResponse,
)
from app.services.marketplace import (
    audit_service,
    connection_service,
    oauth_service,
    sync_manager,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger  = logging.getLogger(__name__)
router  = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _company_id(user) -> UUID:
    if not user.companies:
        raise HTTPException(status_code=400, detail="No company configured for this user.")
    return user.companies[0].id


def _connection_out(conn) -> MarketplaceConnectionOut:
    """Map ORM MarketplaceConnection → schema."""
    has_creds     = conn.credentials is not None and bool(
        conn.credentials.access_token_enc
        or conn.credentials.api_key_enc
        or conn.credentials.refresh_token_enc
    )
    cred_display  = conn.credentials.api_key_display if conn.credentials else None
    return MarketplaceConnectionOut(
        id               = conn.id,
        marketplace_id   = conn.marketplace_id,
        marketplace      = MarketplaceOut.model_validate(conn.marketplace),
        connection_type  = conn.connection_type,
        status           = conn.status,
        display_name     = conn.display_name,
        seller_name      = conn.seller_name,
        seller_email     = conn.seller_email,
        seller_id        = conn.seller_id,
        region           = conn.region,
        shop_domain      = conn.shop_domain,
        last_sync_at     = conn.last_sync_at,
        last_sync_status = conn.last_sync_status,
        last_sync_error  = conn.last_sync_error,
        total_syncs      = conn.total_syncs,
        connected_at     = conn.connected_at,
        created_at       = conn.created_at,
        updated_at       = conn.updated_at,
        has_credentials  = has_creds,
        credential_display = cred_display,
    )


# ── Marketplace registry ──────────────────────────────────────────────────────

@router.get("/", response_model=list[MarketplaceOut])
async def list_marketplaces(
    db:   AsyncSession = Depends(get_db),
    live_only: bool = Query(False, description="Only return marketplaces with live API support"),
):
    """
    Return the full marketplace catalog.
    No authentication required — used by the frontend to build the integrations grid.
    """
    stmt = (
        select(Marketplace)
        .where(Marketplace.is_active.is_(True))
        .order_by(Marketplace.sort_order)
    )
    if live_only:
        stmt = stmt.where(Marketplace.is_live.is_(True))
    markets = (await db.execute(stmt)).scalars().all()
    return [MarketplaceOut.model_validate(m) for m in markets]


# ── Connections — read ────────────────────────────────────────────────────────

@router.get("/connections/", response_model=MarketplaceConnectionListResponse)
async def list_connections(
    db:           AsyncSession = Depends(get_db),
    current_user  = Depends(require_permission("platforms:read")),
):
    company_id  = _company_id(current_user)
    connections = await connection_service.list_connections(company_id, db)
    items       = [_connection_out(c) for c in connections]
    return MarketplaceConnectionListResponse(
        items     = items,
        total     = len(items),
        connected = sum(1 for c in connections if c.status == "connected"),
        error     = sum(1 for c in connections if c.status == "error"),
    )


@router.get("/connections/{connection_id}", response_model=MarketplaceConnectionOut)
async def get_connection(
    connection_id: UUID,
    db:            AsyncSession = Depends(get_db),
    current_user   = Depends(require_permission("platforms:read")),
):
    company_id = _company_id(current_user)
    conn       = await connection_service.get_connection_by_id(connection_id, company_id, db)
    return _connection_out(conn)


# ── Connections — connect ─────────────────────────────────────────────────────

@router.post("/connections/manual", response_model=MarketplaceConnectionOut, status_code=201)
async def connect_manual(
    body:         ManualConnectionRequest,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user  = Depends(require_permission("platforms:write")),
):
    """Create a connection for a manual-upload marketplace (Flipkart, Meesho, Myntra, AJIO)."""
    company_id = _company_id(current_user)
    conn = await connection_service.create_manual_connection(
        company_id       = company_id,
        marketplace_slug = body.marketplace_slug,
        db               = db,
        display_name     = body.display_name,
        performed_by     = current_user.id,
        ip_address       = request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(conn)
    conn = await connection_service.get_connection_by_id(conn.id, company_id, db)
    return _connection_out(conn)


@router.post("/connections/credentials", response_model=MarketplaceConnectionOut, status_code=201)
async def connect_credentials(
    body:         CredentialConnectRequest,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user  = Depends(require_permission("platforms:write")),
):
    """Connect an API-key marketplace (WooCommerce, etc.)."""
    company_id = _company_id(current_user)
    conn = await connection_service.create_credential_connection(
        company_id       = company_id,
        marketplace_slug = body.marketplace_slug,
        raw_credentials  = body.credentials,
        db               = db,
        display_name     = body.display_name,
        performed_by     = current_user.id,
        ip_address       = request.client.host if request.client else None,
    )
    await db.commit()
    conn = await connection_service.get_connection_by_id(conn.id, company_id, db)
    return _connection_out(conn)


@router.delete("/connections/{marketplace_slug}", response_model=DisconnectResponse)
async def disconnect(
    marketplace_slug: str,
    request:          Request,
    db:               AsyncSession = Depends(get_db),
    current_user      = Depends(require_permission("platforms:write")),
):
    company_id = _company_id(current_user)
    conn = await connection_service.disconnect(
        company_id       = company_id,
        marketplace_slug = marketplace_slug,
        db               = db,
        performed_by     = current_user.id,
        ip_address       = request.client.host if request.client else None,
    )
    await db.commit()
    return DisconnectResponse(
        message          = f"Disconnected from {marketplace_slug} successfully.",
        marketplace_slug = marketplace_slug,
        status           = conn.status,
    )


# ── OAuth flow ────────────────────────────────────────────────────────────────

@router.post("/oauth/initiate", response_model=OAuthInitResponse)
async def oauth_initiate(
    body:         OAuthInitRequest,
    db:           AsyncSession = Depends(get_db),
    current_user  = Depends(require_permission("platforms:write")),
):
    """
    Start an OAuth flow.
    Returns the authorization_url the frontend should redirect the user to.
    """
    company_id = _company_id(current_user)
    extra = {}
    if body.shop_domain:
        extra["shop_domain"] = body.shop_domain

    state_row, auth_url = await oauth_service.create_oauth_state(
        company_id       = company_id,
        marketplace_slug = body.marketplace_slug,
        db               = db,
        redirect_uri     = body.redirect_uri,
        extra_params     = extra or None,
    )
    await db.commit()

    return OAuthInitResponse(
        authorization_url = auth_url,
        state             = state_row.state_token,
        expires_at        = state_row.expires_at,
    )


@router.get("/oauth/callback")
@router.post("/oauth/callback")
async def oauth_callback(
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    # Query parameters from OAuth provider redirect
    code:         Optional[str] = Query(None),
    state:        Optional[str] = Query(None),
    marketplace_slug: Optional[str] = Query(None),
    shop:         Optional[str] = Query(None),
    error:        Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """
    OAuth callback endpoint.
    The OAuth provider redirects here with ?code=...&state=...
    No session auth here — state token IS the auth mechanism.
    """
    if error:
        raise HTTPException(
            status_code = 400,
            detail      = f"OAuth authorization denied: {error_description or error}",
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter.")

    try:
        conn = await oauth_service.handle_oauth_callback(
            code         = code,
            state_token  = state,
            db           = db,
            shop         = shop,
            ip_address   = request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await db.commit()

    # Reload with relationships
    conn = (await db.execute(
        select(type(conn))
        .where(type(conn).id == conn.id)
        .options(
            selectinload(type(conn).marketplace),
            selectinload(type(conn).credentials),
        )
    )).scalar_one()

    return OAuthCallbackResponse(
        connection = _connection_out(conn),
        message    = f"Successfully connected to {conn.marketplace.name}.",
    )


# ── Sync ──────────────────────────────────────────────────────────────────────

@router.post("/connections/{connection_id}/sync", response_model=SyncJobOut)
async def trigger_sync(
    connection_id: UUID,
    body:          SyncRequest,
    request:       Request,
    db:            AsyncSession = Depends(get_db),
    current_user   = Depends(require_permission("platforms:write")),
):
    company_id = _company_id(current_user)
    try:
        job = await sync_manager.create_and_run_sync(
            connection_id = connection_id,
            company_id    = company_id,
            sync_type     = body.sync_type,
            db            = db,
            date_from     = body.date_from,
            date_to       = body.date_to,
            triggered_by  = str(current_user.id),
            ip_address    = request.client.host if request.client else None,
        )
        await db.commit()
        return SyncJobOut.model_validate(job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/connections/{connection_id}/jobs", response_model=SyncJobListResponse)
async def list_sync_jobs(
    connection_id: UUID,
    db:            AsyncSession = Depends(get_db),
    current_user   = Depends(require_permission("platforms:read")),
    limit:         int = Query(20, le=100),
):
    company_id = _company_id(current_user)
    # Verify the connection belongs to this company
    await connection_service.get_connection_by_id(connection_id, company_id, db)
    jobs = await sync_manager.list_sync_jobs(connection_id, db, limit=limit)
    return SyncJobListResponse(
        items = [SyncJobOut.model_validate(j) for j in jobs],
        total = len(jobs),
    )


# ── Validate ──────────────────────────────────────────────────────────────────

@router.post("/connections/{connection_id}/validate", response_model=ValidateConnectionResponse)
async def validate_connection(
    connection_id: UUID,
    db:            AsyncSession = Depends(get_db),
    current_user   = Depends(require_permission("platforms:read")),
):
    """Perform a live credentials check against the marketplace API."""
    from app.services.marketplace.provider_registry import get_provider, is_supported
    company_id = _company_id(current_user)
    conn = await connection_service.get_connection_by_id(connection_id, company_id, db)

    if not is_supported(conn.marketplace.slug):
        raise HTTPException(status_code=400,
                            detail=f"No provider for '{conn.marketplace.slug}'.")

    provider = get_provider(conn.marketplace.slug)
    result   = await provider.validate_connection(conn, conn.credentials)
    return ValidateConnectionResponse(
        is_valid = result.is_valid,
        message  = result.message,
        checks   = [ConnectionCheckResult(**c) for c in result.checks],
        error    = result.error,
    )


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit/{connection_id}", response_model=list[AuditLogOut])
async def get_audit_log(
    connection_id: UUID,
    db:            AsyncSession = Depends(get_db),
    current_user   = Depends(require_permission("platforms:read")),
    limit:         int = Query(50, le=500),
):
    company_id = _company_id(current_user)
    logs = (await db.execute(
        select(MarketplaceAuditLog)
        .where(
            MarketplaceAuditLog.connection_id == connection_id,
            MarketplaceAuditLog.company_id    == company_id,
        )
        .order_by(MarketplaceAuditLog.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return [AuditLogOut.model_validate(log) for log in logs]


# ── Super admin ───────────────────────────────────────────────────────────────

@router.get("/admin/connections")
async def admin_list_all_connections(
    db:           AsyncSession = Depends(get_db),
    current_user  = Depends(get_current_user),
    limit:         int = Query(100, le=500),
    offset:        int = Query(0),
):
    """Super-admin endpoint: list all marketplace connections across all companies."""
    if not getattr(current_user, "is_superadmin", False):
        raise HTTPException(status_code=403, detail="Super admin access required.")

    from app.db.models.marketplace_connection import MarketplaceConnection
    rows = (await db.execute(
        select(MarketplaceConnection)
        .where(MarketplaceConnection.deleted_at.is_(None))
        .options(
            selectinload(MarketplaceConnection.marketplace),
        )
        .order_by(MarketplaceConnection.created_at.desc())
        .limit(limit)
        .offset(offset)
    )).scalars().all()

    return {
        "items": [
            {
                "id":              str(r.id),
                "company_id":      str(r.company_id),
                "marketplace":     r.marketplace.name,
                "slug":            r.marketplace.slug,
                "status":          r.status,
                "seller_id":       r.seller_id,
                "last_sync_at":    r.last_sync_at.isoformat() if r.last_sync_at else None,
                "connected_at":    r.connected_at.isoformat() if r.connected_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }
