from fastapi import APIRouter
from app.data.mock_data import GST

router = APIRouter()


@router.get("/")
def get_gst():
    total_tcs = sum(g["tcs"] for g in GST)
    total_tds = sum(g["tds"] for g in GST)
    unreconciled = sum(1 for g in GST if not g["ok"])
    return {
        "items": GST,
        "summary": {
            "total_tcs": total_tcs,
            "total_tds": total_tds,
            "unreconciled": unreconciled,
            "claimable": total_tcs + total_tds,
        },
    }


@router.post("/generate-report")
def generate_report():
    return {"message": "GST report generation started", "status": "processing", "ready_in": "30 seconds"}
