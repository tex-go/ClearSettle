from fastapi import APIRouter, Query
from app.data.mock_data import RULES

router = APIRouter()


@router.get("/rules")
def get_rules():
    auto_count = sum(1 for r in RULES if r["auto"])
    return {"items": RULES, "auto_raise_count": auto_count}


@router.get("/rules/{rule_id}")
def get_rule(rule_id: int):
    item = next((r for r in RULES if r["id"] == rule_id), None)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Rule not found")
    return item


@router.get("/calculator")
def calculator(
    gmv: float = Query(5000000),
    years: int = Query(1),
    platform: str = Query("multi"),
    model: str = Query("s15"),
):
    rates = {"amazon": 0.028, "flipkart": 0.022, "meesho": 0.008, "multi": 0.035}
    rate = rates.get(platform, 0.035)
    total_gmv = gmv * years
    raw_overcharge = total_gmv * rate
    platform_dispute = raw_overcharge * 0.25
    legal_route = raw_overcharge * 0.45
    gst_recovery = total_gmv * 0.01 * 0.6
    total_recoverable = platform_dispute + legal_route + gst_recovery
    model_rates = {"s15": 0.15, "s20": 0.20, "s25": 0.25}
    if model in model_rates:
        cs_earnings = total_recoverable * model_rates[model]
    else:
        cs_earnings = 1499 * 12 * years
    return {
        "total_gmv": round(total_gmv),
        "raw_overcharge": round(raw_overcharge),
        "platform_dispute": round(platform_dispute),
        "legal_route": round(legal_route),
        "gst_recovery": round(gst_recovery),
        "total_recoverable": round(total_recoverable),
        "clearsettle_earnings": round(cs_earnings),
    }
