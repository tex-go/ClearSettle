from fastapi import APIRouter
from app.data.mock_data import RETURNS
from collections import Counter

router = APIRouter()


@router.get("/")
def get_returns():
    total_deducted = sum(r["total"] for r in RETURNS)
    disputed = sum(1 for r in RETURNS if r["status"] == "disputed")
    reasons = Counter(r["reason"] for r in RETURNS)
    return {
        "items": RETURNS,
        "summary": {
            "total_count": len(RETURNS),
            "total_deducted": total_deducted,
            "disputed_count": disputed,
            "by_reason": dict(reasons),
        },
    }
