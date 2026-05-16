from fastapi import APIRouter, Query
from app.data.mock_data import REPORT_TYPES

router = APIRouter()


@router.get("/")
def get_reports():
    return {"items": REPORT_TYPES}


@router.post("/generate/{report_id}")
def generate_report(report_id: str, format: str = Query("PDF")):
    return {
        "message": "Generating " + report_id + " report",
        "format": format,
        "status": "processing",
        "ready_in": "30 seconds",
    }
