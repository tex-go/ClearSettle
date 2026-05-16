from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.data.mock_data import DISPUTES
import copy, time

router = APIRouter()
_disputes = copy.deepcopy(DISPUTES)


@router.get("/")
def get_disputes():
    total_amount = sum(d["amt"] for d in _disputes)
    open_count = sum(1 for d in _disputes if d["status"] in ("open", "pending"))
    won = [d for d in _disputes if d["status"] == "won"]
    return {
        "items": _disputes,
        "summary": {
            "total_amount": total_amount,
            "open_count": open_count,
            "won_count": len(won),
            "won_amount": sum(d["amt"] for d in won),
        },
    }


class NewDispute(BaseModel):
    platform: str
    dispute_type: str
    settlement_id: str
    amount: float
    description: str


@router.post("/")
def create_dispute(body: NewDispute):
    ref = "DISP-" + str(int(time.time()))[-4:]
    new = {
        "id": ref, "plat": body.platform, "icon": "⚖️",
        "type": body.dispute_type, "amt": body.amount,
        "desc": body.description, "status": "open",
        "raised": "2026-05-16", "expected": "2026-05-30",
        "ref": ref, "resolution": None,
    }
    _disputes.append(new)
    return new


@router.get("/{did}")
def get_dispute(did: str):
    item = next((d for d in _disputes if d["id"] == did), None)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Dispute not found")
    return item


class DisputeUpdate(BaseModel):
    note: Optional[str] = None


@router.put("/{did}/update")
def update_dispute(did: str, body: DisputeUpdate):
    return {"message": "Dispute " + did + " updated", "note": body.note}
