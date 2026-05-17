"""
Platforms router — returns connection state from DB when available,
falls back to mock data otherwise.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db_optional, get_current_user
from app.data.mock_data import PLATFORMS
import copy

router = APIRouter()
_mock_platforms = copy.deepcopy(PLATFORMS)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _connection_to_dict(conn) -> dict:
    return {
        "id": conn.platform,
        "name": conn.platform.capitalize(),
        "status": conn.status,
        "selling_partner_id": conn.sp_selling_partner_id,
        "marketplace_id": conn.sp_marketplace_id,
        "last_sync": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
        "total_orders_synced": conn.total_orders_synced or 0,
        "connection_id": str(conn.id),
        "key": conn.api_key_display or "",
    }


def _get_platforms_db(db: Session, user) -> list[dict]:
    from app.db.models import PlatformConnection
    company = user.companies[0] if user.companies else None
    if not company:
        return []
    conns = (
        db.query(PlatformConnection)
        .filter_by(company_id=company.id)
        .order_by(PlatformConnection.platform)
        .all()
    )
    return [_connection_to_dict(c) for c in conns]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
def get_platforms(
    db: Session | None = Depends(get_db_optional),
    current_user=Depends(get_current_user),
):
    items = _get_platforms_db(db, current_user) if db is not None else _mock_platforms
    connected    = sum(1 for p in items if p.get("status") == "connected")
    pending      = sum(1 for p in items if p.get("status") in ("pending", "oauth_pending"))
    disconnected = sum(1 for p in items if p.get("status") == "disconnected")
    error_count  = sum(1 for p in items if p.get("status") == "error")
    return {
        "items": items,
        "summary": {"connected": connected, "pending": pending,
                    "disconnected": disconnected, "error": error_count},
    }


@router.get("/{pid}")
def get_platform(
    pid: str,
    db: Session | None = Depends(get_db_optional),
    current_user=Depends(get_current_user),
):
    if db is not None:
        from app.db.models import PlatformConnection
        company = current_user.companies[0] if current_user.companies else None
        if not company:
            raise HTTPException(status_code=404, detail="Platform not found")
        conn = db.query(PlatformConnection).filter_by(
            company_id=company.id, platform=pid
        ).first()
        if not conn:
            raise HTTPException(status_code=404, detail="Platform not found")
        return _connection_to_dict(conn)
    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    if not item:
        raise HTTPException(status_code=404, detail="Platform not found")
    return item


class PlatformUpdate(BaseModel):
    api_key: Optional[str] = None
    status: Optional[str] = None


@router.put("/{pid}")
def update_platform(
    pid: str,
    body: PlatformUpdate,
    db: Session | None = Depends(get_db_optional),
    current_user=Depends(get_current_user),
):
    if db is not None:
        from app.db.models import PlatformConnection
        company = current_user.companies[0] if current_user.companies else None
        conn = db.query(PlatformConnection).filter_by(
            company_id=company.id, platform=pid
        ).first()
        if not conn:
            raise HTTPException(status_code=404, detail="Platform not found")
        if body.api_key:
            conn.api_key_display = body.api_key[:4] + "****"
        if body.status:
            conn.status = body.status
        conn.updated_at = datetime.utcnow()
        db.commit()
        return _connection_to_dict(conn)
    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    if not item:
        raise HTTPException(status_code=404, detail="Platform not found")
    if body.api_key:
        item["key"] = body.api_key[:4] + "****"
    if body.status:
        item["status"] = body.status
    return item


@router.post("/{pid}/sync")
def sync_platform(pid: str):
    return {"message": f"Sync initiated for {pid}", "status": "syncing"}


class ConnectRequest(BaseModel):
    api_key: str
    secret: str
    seller_id: str


@router.post("/{pid}/connect")
def connect_platform(
    pid: str,
    body: ConnectRequest,
    db: Session | None = Depends(get_db_optional),
    current_user=Depends(get_current_user),
):
    if db is not None:
        from app.db.models import PlatformConnection
        from app.core.crypto import encrypt
        company = current_user.companies[0] if current_user.companies else None
        conn = db.query(PlatformConnection).filter_by(
            company_id=company.id, platform=pid
        ).first()
        if not conn:
            conn = PlatformConnection(company_id=company.id, platform=pid)
            db.add(conn)
        conn.status = "connected"
        conn.api_key_display = body.api_key[:4] + "****"
        conn.webhook_secret_enc = encrypt(body.secret)
        conn.sp_selling_partner_id = body.seller_id
        conn.updated_at = datetime.utcnow()
        db.commit()
        return {"message": f"{pid} connected successfully", "status": "connected"}
    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    if item:
        item["status"] = "connected"
        item["key"] = body.api_key[:4] + "****"
    return {"message": f"{pid} connected successfully", "status": "connected"}


@router.delete("/{pid}/disconnect")
def disconnect_platform(
    pid: str,
    db: Session | None = Depends(get_db_optional),
    current_user=Depends(get_current_user),
):
    if db is not None:
        from app.db.models import PlatformConnection
        company = current_user.companies[0] if current_user.companies else None
        conn = db.query(PlatformConnection).filter_by(
            company_id=company.id, platform=pid
        ).first()
        if conn:
            conn.status = "disconnected"
            conn.sp_access_token_enc = None
            conn.sp_refresh_token_enc = None
            conn.updated_at = datetime.utcnow()
            db.commit()
        return {"message": f"{pid} disconnected"}
    item = next((p for p in _mock_platforms if p["id"] == pid), None)
    if item:
        item["status"] = "disconnected"
    return {"message": f"{pid} disconnected"}
