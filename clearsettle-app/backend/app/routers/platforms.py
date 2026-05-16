from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from app.data.mock_data import PLATFORMS
import copy

router = APIRouter()
_platforms = copy.deepcopy(PLATFORMS)


@router.get("/")
def get_platforms():
    connected = sum(1 for p in _platforms if p["status"] == "connected")
    pending = sum(1 for p in _platforms if p["status"] == "pending")
    disconnected = sum(1 for p in _platforms if p["status"] == "disconnected")
    return {"items": _platforms, "summary": {"connected": connected, "pending": pending, "disconnected": disconnected}}


@router.get("/{pid}")
def get_platform(pid: str):
    item = next((p for p in _platforms if p["id"] == pid), None)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Platform not found")
    return item


class PlatformUpdate(BaseModel):
    api_key: Optional[str] = None
    status: Optional[str] = None


@router.put("/{pid}")
def update_platform(pid: str, body: PlatformUpdate):
    item = next((p for p in _platforms if p["id"] == pid), None)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Platform not found")
    if body.api_key:
        item["key"] = body.api_key[:4] + "****"
    if body.status:
        item["status"] = body.status
    return item


@router.post("/{pid}/sync")
def sync_platform(pid: str):
    return {"message": "Sync initiated for " + pid, "status": "syncing"}


class ConnectRequest(BaseModel):
    api_key: str
    secret: str
    seller_id: str


@router.post("/{pid}/connect")
def connect_platform(pid: str, body: ConnectRequest):
    item = next((p for p in _platforms if p["id"] == pid), None)
    if item:
        item["status"] = "connected"
        item["key"] = body.api_key[:4] + "****"
    return {"message": pid + " connected successfully", "status": "connected"}


@router.delete("/{pid}/disconnect")
def disconnect_platform(pid: str):
    item = next((p for p in _platforms if p["id"] == pid), None)
    if item:
        item["status"] = "disconnected"
    return {"message": pid + " disconnected"}
