from fastapi import APIRouter
from app.data.mock_data import COMPETITORS

router = APIRouter()


@router.get("/")
def get_competitors():
    direct = [c for c in COMPETITORS if c["type"] == "Direct"]
    adjacent = [c for c in COMPETITORS if c["type"] == "Adjacent"]
    with_dispute = sum(1 for c in COMPETITORS if c["disputeEngine"])
    with_bank = sum(1 for c in COMPETITORS if c["bankMatch"])
    with_cash = sum(1 for c in COMPETITORS if c["cashForecast"])
    return {
        "items": COMPETITORS,
        "summary": {
            "total": len(COMPETITORS),
            "direct": len(direct),
            "adjacent": len(adjacent),
            "with_dispute_engine": with_dispute,
            "with_bank_match": with_bank,
            "with_cash_forecast": with_cash,
        },
    }
