from fastapi import APIRouter, Query
from app.data.mock_data import SETTLEMENTS

router = APIRouter()


@router.get("/")
def get_settlements(status: str = Query(None), platform: str = Query(None), search: str = Query(None)):
    items = list(SETTLEMENTS)
    if status:
        items = [s for s in items if s["status"] == status]
    if platform:
        items = [s for s in items if s["plat"].lower() == platform.lower()]
    if search:
        q = search.lower()
        items = [s for s in items if q in s["id"].lower() or q in s["plat"].lower()]
    total_net = sum(s["net"] for s in items if s["status"] == "paid")
    pending_net = sum(s["net"] for s in items if s["status"] == "pending")
    total_penalties = sum(s["pen"] for s in items)
    return {"items": items, "total": len(items), "summary": {"total_net": total_net, "pending_net": pending_net, "total_penalties": total_penalties}}


@router.get("/{sid}")
def get_settlement(sid: str):
    item = next((s for s in SETTLEMENTS if s["id"] == sid), None)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Settlement not found")
    breakdown = {
        "base": item["base"],
        "commission": -item["comm"],
        "logistics": -item["logi"],
        "returns": -item["ret"],
        "tcs": -item["tcs"],
        "penalty": -item["pen"],
        "net": item["net"],
    }
    return {**item, "breakdown": breakdown}


@router.post("/{sid}/dispute")
def raise_dispute(sid: str):
    return {"message": "Dispute raised for settlement " + sid, "status": "open", "ref": "DISP-AUTO-" + sid}
