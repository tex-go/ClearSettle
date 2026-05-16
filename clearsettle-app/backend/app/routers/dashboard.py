from fastapi import APIRouter
from app.data.mock_data import PLATFORMS, BANK, COMMISSIONS, DASHBOARD_TREND, PLATFORM_SHARE, NOTIFICATIONS, SETTLEMENTS

router = APIRouter()


@router.get("/summary")
def summary():
    total_gmv = sum(p["gmv"] for p in PLATFORMS)
    total_pending = sum(p["pending"] for p in PLATFORMS)
    total_orders = sum(p["orders"] for p in PLATFORMS)
    total_returns = sum(p["returns"] for p in PLATFORMS)
    connected = sum(1 for p in PLATFORMS if p["status"] == "connected")
    commission_overcharges = sum(c["over"] for c in COMMISSIONS if c["flag"])
    bank_mismatches = sum(1 for b in BANK if b["ms"] == "unmatched")
    total_net = sum(s["net"] for s in SETTLEMENTS if s["status"] == "paid")
    pending_net = sum(s["net"] for s in SETTLEMENTS if s["status"] == "pending")
    return {
        "total_gmv": total_gmv,
        "total_pending": total_pending,
        "total_orders": total_orders,
        "total_returns": total_returns,
        "connected_platforms": connected,
        "total_platforms": len(PLATFORMS),
        "commission_overcharges": commission_overcharges,
        "bank_mismatches": bank_mismatches,
        "total_net": total_net,
        "pending_net": pending_net,
        "platforms": PLATFORMS,
        "settlement_trend": DASHBOARD_TREND,
        "platform_share": PLATFORM_SHARE,
        "alerts": [
            {
                "type": "warn",
                "title": "Commission Overcharge Detected",
                "sub": "3 SKUs overcharged ₹" + str(commission_overcharges) + " across Amazon & Flipkart",
                "action": "Review Now",
            },
            {
                "type": "error",
                "title": "Bank Reconciliation Mismatch",
                "sub": str(bank_mismatches) + " unmatched bank credits totalling ₹57,220",
                "action": "Reconcile",
            },
        ],
    }


@router.get("/notifications")
def notifications():
    return {"items": NOTIFICATIONS}
