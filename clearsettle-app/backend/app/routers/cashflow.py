from fastapi import APIRouter
from app.data.mock_data import CASHFLOW

router = APIRouter()


@router.get("/")
def get_cashflow():
    expected = [e for e in CASHFLOW if e["type"] in ("expected", "predicted")]
    expected_total = sum(e["amt"] for e in expected)
    upcoming = sorted([e for e in expected], key=lambda x: x["date"])
    next_s = upcoming[0] if upcoming else None
    return {
        "events": CASHFLOW,
        "summary": {
            "expected_total": expected_total,
            "upcoming_count": len(upcoming),
            "next_settlement": next_s,
        },
    }
