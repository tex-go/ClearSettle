from fastapi import APIRouter
from app.data.mock_data import BANK

router = APIRouter()


@router.get("/")
def get_bank():
    total_amount = sum(b["amt"] for b in BANK)
    matched = [b for b in BANK if b["ms"] == "matched"]
    partial = [b for b in BANK if b["ms"] == "partial"]
    unmatched = [b for b in BANK if b["ms"] == "unmatched"]
    return {
        "items": BANK,
        "summary": {
            "total_amount": total_amount,
            "matched_count": len(matched),
            "partial_count": len(partial),
            "unmatched_count": len(unmatched),
            "unmatched_amount": sum(b["amt"] for b in unmatched),
            "partial_variance": sum(b["va"] for b in partial),
        },
    }


@router.post("/auto-match")
def auto_match():
    return {"message": "Auto-match complete", "matched": 6, "unmatched": 2, "partial": 1}


@router.get("/{bid}")
def get_bank_item(bid: str):
    item = next((b for b in BANK if b["id"] == bid), None)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Bank entry not found")
    return item
