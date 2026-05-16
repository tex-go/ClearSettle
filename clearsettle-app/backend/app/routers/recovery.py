from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.data.mock_data import RECOVERY
import copy

router = APIRouter()
_recovery = copy.deepcopy(RECOVERY)


@router.get("/")
def get_recovery():
    won = [r for r in _recovery if r["status"] == "won"]
    open_items = [r for r in _recovery if r["status"] == "open"]
    gst_items = [r for r in _recovery if r["status"] == "gst_pending"]
    return {
        "items": _recovery,
        "summary": {
            "total_amount": sum(r["amount"] for r in _recovery),
            "won_amount": sum(r["amount"] for r in won),
            "open_amount": sum(r["amount"] for r in open_items),
            "gst_amount": sum(r["amount"] for r in gst_items),
        },
    }


class RecoveryUpdate(BaseModel):
    note: Optional[str] = None
    new_status: Optional[str] = None


@router.put("/{rid}/update")
def update_recovery(rid: str, body: RecoveryUpdate):
    item = next((r for r in _recovery if r["id"] == rid), None)
    if item and body.new_status:
        item["status"] = body.new_status
    return {"message": "Recovery " + rid + " updated", "note": body.note}


@router.post("/{rid}/legal-notice")
def legal_notice(rid: str):
    return {"message": "Legal notice drafted for " + rid, "status": "ready_for_review"}
