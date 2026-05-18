"""
Platforms router — full connection management.

Endpoints
---------
GET  /platforms/                    → list all connections + summary
GET  /platforms/registry            → static platform info (no auth)
GET  /platforms/{pid}               → single connection
POST /platforms/{pid}/connect       → store credentials, set connected
DELETE /platforms/{pid}/disconnect  → wipe credentials, set disconnected
POST /platforms/{pid}/test          → validate connection config (no live API call)
GET  /platforms/{pid}/credentials   → masked credential info
PUT  /platforms/{pid}/credentials   → update stored credentials
POST /platforms/{pid}/sync          → trigger sync (stub — sync logic in future session)

All DB-backed endpoints fall back to mock data when DATABASE_URL is not set.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.core.rbac import require_permission
from app.data.mock_data import PLATFORMS
from app.schemas.platform import (
    ConnectApiKeyRequest,
    ConnectionOut,
    ConnectionsResponse,
    CredentialsOut,
    PlatformInfo,
    TestConnectionResult,
    PLATFORM_REGISTRY,
    get_platform_meta,
)

import copy

router = APIRouter()
_mock_platforms = copy.deepcopy(PLATFORMS)


# ── Internal: build ConnectionOut from a mock-data dict ──────────────────────

def _mock_to_out(p: dict) -> ConnectionOut:
    meta = get_platform_meta(p["id"])
    return ConnectionOut(
        id=p["id"],
        platform=p["id"],
        platform_name=meta["name"],
        auth_type=meta["auth_type"],
        color=meta["color"],
        status=p.get("status", "disconnected"),
        seller_id=p.get("selling_partner_id"),
        marketplace_id=p.get("marketplace_id"),
        credentials_present=p.get("status") == "connected",
        webhook_url=None,
        last_sync_at=None,
        last_sync_error=None,
        total_orders_synced=p.get("total_orders_synced", 0),
        connection_id=p.get("connection_id", ""),
        key=p.get("key", ""),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _mock_summary(items):
    from app.schemas.platform import ConnectionSummary
    return ConnectionSummary(
        total=len(items),
        connected=sum(1 for i in items if i.status == "connected"),
        disconnected=sum(1 for i in items if i.status == "disconnected"),
        pending=sum(1 for i in items if i.status == "pending"),
        error=sum(1 for i in items if i.status == "error"),
        oauth_pending=sum(1 for i in items if i.status == "oauth_pending"),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/registry", response_model=list[PlatformInfo])
async def list_platform_registry():
    """
    Returns static metadata about every supported platform.
    No authentication required — used by the frontend to build the platform list.
    """
    return [
        PlatformInfo(
            platform=pid,
            name=meta["name"],
            auth_type=meta["auth_type"],
            color=meta["color"],
            description=meta["description"],
            required_fields=meta["required_cred_fields"],
        )
        for pid, meta in PLATFORM_REGISTRY.items()
    ]


@router.get("/", response_model=ConnectionsResponse)
async def get_platforms(
    db: AsyncSession | None = Depends(get_db_optional),
    current_user=Depends(require_permission("platforms:read")),
):
    if db is not None and not isinstance(current_user, dict):
        from app.services.platform_service import list_connections
        company = current_user.companies[0] if current_user.companies else None
        if not company:
            raise HTTPException(status_code=400, detail="No company configured for this user")
        return await list_connections(company.id, db)

    # mock-data fallback
    items = [_mock_to_out(p) for p in _mock_platforms]
    return ConnectionsResponse(items=items, summary=_mock_summary(items))


@router.get("/{pid}", response_model=ConnectionOut)
async def get_platform(
    pid: str,
    db: AsyncSession | None = Depends(get_db_optional),
    current_user=Depends(require_permission("platforms:read")),
):
    if db is not None and not isinstance(current_user, dict):
        from app.services.platform_service import get_connection
        company = current_user.companies[0] if current_user.companies else None
        if not company:
            raise HTTPException(status_code=400, detail="No company configured for this user")
        return await get_connection(pid, company.id, db)

    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    if not item:
        raise HTTPException(status_code=404, detail="Platform not found")
    return _mock_to_out(item)


@router.post("/{pid}/connect", response_model=ConnectionOut)
async def connect_platform(
    pid: str,
    body: ConnectApiKeyRequest,
    db: AsyncSession | None = Depends(get_db_optional),
    current_user=Depends(require_permission("platforms:write")),
):
    """
    Store encrypted credentials for an API-key platform.
    For Amazon, use POST /sp-api/authorize instead (OAuth flow).
    """
    if db is not None and not isinstance(current_user, dict):
        from app.services.platform_service import connect_api_key
        company = current_user.companies[0] if current_user.companies else None
        if not company:
            raise HTTPException(status_code=400, detail="No company configured for this user")
        return await connect_api_key(
            pid, body.credentials, company.id, db,
            seller_id=body.seller_id,
            webhook_url=body.webhook_url,
        )

    # mock-data fallback
    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    if item:
        api_key = body.credentials.get("api_key", "")
        item["status"] = "connected"
        item["key"] = (api_key[:4] + "****") if len(api_key) > 4 else "****"
    return _mock_to_out(item) if item else ConnectionOut(
        id=pid, platform=pid, platform_name=pid.capitalize(),
        auth_type="api_key", color="#6B7280", status="connected",
        credentials_present=True, connection_id="", key="",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


@router.delete("/{pid}/disconnect", response_model=ConnectionOut)
async def disconnect_platform(
    pid: str,
    db: AsyncSession | None = Depends(get_db_optional),
    current_user=Depends(require_permission("platforms:write")),
):
    if db is not None and not isinstance(current_user, dict):
        from app.services.platform_service import disconnect
        company = current_user.companies[0] if current_user.companies else None
        if not company:
            raise HTTPException(status_code=400, detail="No company configured for this user")
        return await disconnect(pid, company.id, db)

    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    if item:
        item["status"] = "disconnected"
        item["key"] = ""
    return _mock_to_out(item) if item else HTTPException(status_code=404, detail="Not found")


@router.post("/{pid}/test", response_model=TestConnectionResult)
async def test_platform_connection(
    pid: str,
    db: AsyncSession | None = Depends(get_db_optional),
    current_user=Depends(require_permission("platforms:read")),
):
    """
    Validate the stored connection configuration.
    Checks: row exists, status, credentials present + decryptable, required fields.
    Does NOT make a live API call (reserved for sync session).
    """
    if db is not None and not isinstance(current_user, dict):
        from app.services.platform_service import test_connection
        company = current_user.companies[0] if current_user.companies else None
        if not company:
            raise HTTPException(status_code=400, detail="No company configured for this user")
        return await test_connection(pid, company.id, db)

    # mock-data fallback
    from app.schemas.platform import CheckResult
    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    meta = get_platform_meta(pid)
    if item and item.get("status") == "connected":
        return TestConnectionResult(
            platform=pid,
            status="ok",
            message=f"{meta['name']} appears connected (mock mode — no DB validation).",
            checks=[CheckResult(name="mock_check", passed=True, detail="Running in mock-data mode")],
        )
    return TestConnectionResult(
        platform=pid,
        status="unconfigured",
        message=f"{meta['name']} is not connected.",
        checks=[CheckResult(name="mock_check", passed=False, detail="Status is not 'connected'")],
    )


@router.get("/{pid}/credentials", response_model=CredentialsOut)
async def get_platform_credentials(
    pid: str,
    db: AsyncSession | None = Depends(get_db_optional),
    current_user=Depends(require_permission("platforms:read")),
):
    """
    Return masked credential information.
    Plaintext credentials are never returned.
    """
    if db is not None and not isinstance(current_user, dict):
        from app.services.platform_service import get_masked_credentials
        company = current_user.companies[0] if current_user.companies else None
        if not company:
            raise HTTPException(status_code=400, detail="No company configured for this user")
        return await get_masked_credentials(pid, company.id, db)

    # mock-data fallback
    from app.schemas.platform import CredentialFieldOut
    meta = get_platform_meta(pid)
    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    has_key = item and item.get("key")
    return CredentialsOut(
        platform=pid,
        auth_type=meta["auth_type"],
        fields=[
            CredentialFieldOut(
                key="api_key",
                masked_value=item.get("key", "") if has_key else "",
                present=bool(has_key),
            )
        ],
        seller_id=item.get("selling_partner_id") if item else None,
        webhook_url=None,
    )


@router.put("/{pid}/credentials", response_model=ConnectionOut)
async def update_platform_credentials(
    pid: str,
    body: ConnectApiKeyRequest,
    db: AsyncSession | None = Depends(get_db_optional),
    current_user=Depends(require_permission("platforms:write")),
):
    """Update stored credentials without changing connection status."""
    if db is not None and not isinstance(current_user, dict):
        from app.services.platform_service import update_credentials
        company = current_user.companies[0] if current_user.companies else None
        if not company:
            raise HTTPException(status_code=400, detail="No company configured for this user")
        return await update_credentials(
            pid, body.credentials, company.id, db,
            seller_id=body.seller_id,
            webhook_url=body.webhook_url,
        )

    raise HTTPException(status_code=503, detail="Credential update requires a database connection")


@router.post("/{pid}/sync")
async def sync_platform(pid: str):
    """Stub: sync logic is implemented in a future session."""
    return {"message": f"Sync initiated for {pid}", "status": "syncing", "note": "Full sync logic coming in Session 4"}
