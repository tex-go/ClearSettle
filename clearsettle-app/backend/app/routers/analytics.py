from fastapi import APIRouter
from app.data.mock_data import PROFIT

router = APIRouter()


@router.get("/")
def get_analytics():
    total_rev = sum(p["rev"] for p in PROFIT)
    total_net = sum(p["net"] for p in PROFIT)
    avg_margin = sum(p["margin"] for p in PROFIT) / len(PROFIT) if PROFIT else 0
    loss_making = sum(1 for p in PROFIT if p["net"] < 0)
    return {
        "items": PROFIT,
        "summary": {
            "total_revenue": total_rev,
            "total_net": total_net,
            "avg_margin": round(avg_margin, 1),
            "loss_making": loss_making,
        },
    }


@router.get("/{sku}")
def get_sku(sku: str):
    item = next((p for p in PROFIT if p["sku"] == sku), None)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="SKU not found")
    return item
