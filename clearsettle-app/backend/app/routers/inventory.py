from fastapi import APIRouter
from app.data.mock_data import INVENTORY

router = APIRouter()


@router.get("/")
def get_inventory():
    critical = [i for i in INVENTORY if i["st"] == "critical"]
    low = [i for i in INVENTORY if i["st"] == "low"]
    ok = [i for i in INVENTORY if i["st"] == "ok"]
    return {
        "items": INVENTORY,
        "summary": {
            "critical_count": len(critical),
            "low_count": len(low),
            "ok_count": len(ok),
        },
    }


@router.post("/sync")
def sync_inventory():
    return {"message": "Inventory sync initiated across all connected platforms", "status": "syncing"}
