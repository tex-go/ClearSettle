from fastapi import APIRouter
from app.data.mock_data import COMMISSIONS

router = APIRouter()


@router.get("/")
def get_commissions():
    flagged = [c for c in COMMISSIONS if c["flag"]]
    return {
        "items": COMMISSIONS,
        "summary": {
            "total_overcharge": sum(c["over"] for c in flagged),
            "flagged_count": len(flagged),
            "affected_orders": sum(c["orders"] for c in flagged),
        },
    }


@router.post("/bulk-dispute")
def bulk_dispute():
    flagged = [c for c in COMMISSIONS if c["flag"]]
    total = sum(c["over"] for c in flagged)
    return {"message": "Bulk dispute raised", "count": len(flagged), "total": total}
