"""
Forecast engine: projects future cash flow from historical patterns.

Algorithm:
  1. Pull last N months of actuals via aggregator
  2. Compute average inflow/outflow per period bucket
  3. Apply a linear trend adjustment if enough data exists
  4. Generate projection points with confidence that decays over time
  5. Tag each point with shortage_risk based on cumulative balance
"""
from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.forecast.aggregator import aggregate_settlements, get_current_balance

logger = logging.getLogger(__name__)

_HORIZON_DAYS = {
    "7d":  7,
    "30d": 30,
    "90d": 90,
    "1y":  365,
}

_PERIOD_TYPE_FOR_HORIZON = {
    "7d":  "daily",
    "30d": "daily",
    "90d": "weekly",
    "1y":  "monthly",
}

_SHORTAGE_THRESHOLDS = {
    "critical": 0,
    "high":     10_000,
    "medium":   50_000,
    "low":      200_000,
}


def _shortage_risk(cumulative: float) -> str:
    if cumulative <= _SHORTAGE_THRESHOLDS["critical"]:
        return "critical"
    if cumulative <= _SHORTAGE_THRESHOLDS["high"]:
        return "high"
    if cumulative <= _SHORTAGE_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def _period_label(d: date, period_type: str) -> str:
    if period_type == "daily":
        return d.strftime("%a %d %b")
    if period_type == "weekly":
        return f"Wk {d.strftime('%d %b')}"
    return d.strftime("%b %Y")


def _generate_dates(start: date, horizon_days: int, period_type: str) -> list[date]:
    dates = []
    cur = start
    end = start + timedelta(days=horizon_days)
    step = {
        "daily":   timedelta(days=1),
        "weekly":  timedelta(weeks=1),
        "monthly": timedelta(days=30),
    }[period_type]
    while cur <= end:
        dates.append(cur)
        cur += step
    return dates


async def generate_projections(
    db: AsyncSession,
    company_id: UUID,
    *,
    horizon: str = "30d",
    currency: str = "INR",
) -> dict[str, Any]:
    period_type = _PERIOD_TYPE_FOR_HORIZON.get(horizon, "daily")
    horizon_days = _HORIZON_DAYS.get(horizon, 30)

    # Pull 6 months of historical data to compute averages
    today = date.today()
    hist_start = date(today.year - 1, today.month, 1) if today.month == 1 else \
                 date(today.year if today.month > 6 else today.year - 1,
                      (today.month - 6) % 12 or 12, 1)
    hist_end = today

    actuals = await aggregate_settlements(
        db, company_id,
        start_date=hist_start,
        end_date=hist_end,
        period_type=period_type,
    )

    if actuals:
        avg_inflow  = sum(a["inflows"]  for a in actuals) / len(actuals)
        avg_outflow = sum(a["outflows"] for a in actuals) / len(actuals)
        # Simple trend: compare first half vs second half
        mid = len(actuals) // 2
        if mid > 0:
            first_half_avg = sum(a["inflows"] for a in actuals[:mid]) / mid
            second_half_avg = sum(a["inflows"] for a in actuals[mid:]) / max(len(actuals) - mid, 1)
            trend = (second_half_avg - first_half_avg) / max(first_half_avg, 1)
        else:
            trend = 0.0
    else:
        avg_inflow  = 0.0
        avg_outflow = 0.0
        trend = 0.0

    current_balance = await get_current_balance(db, company_id)

    # Project forward
    projection_dates = _generate_dates(today + timedelta(days=1), horizon_days, period_type)
    points = []
    cumulative = current_balance
    total_inflow = 0.0
    total_outflow = 0.0

    for i, d in enumerate(projection_dates):
        # Confidence degrades with distance
        confidence = max(0.3, 1.0 - (i / len(projection_dates)) * 0.7)
        # Trend adjustment — moderate
        trend_factor = 1.0 + trend * min(i / 30, 1.0) * 0.5
        proj_inflow  = avg_inflow  * trend_factor
        proj_outflow = avg_outflow
        net = proj_inflow - proj_outflow
        cumulative += net
        total_inflow  += proj_inflow
        total_outflow += proj_outflow

        points.append({
            "date":              d.isoformat(),
            "label":             _period_label(d, period_type),
            "projected_inflow":  round(proj_inflow, 2),
            "projected_outflow": round(proj_outflow, 2),
            "net":               round(net, 2),
            "cumulative_balance": round(cumulative, 2),
            "confidence":        round(confidence, 2),
            "shortage_risk":     _shortage_risk(cumulative),
        })

    return {
        "horizon":                horizon,
        "period_type":            period_type,
        "current_balance":        round(current_balance, 2),
        "currency":               currency,
        "points":                 points,
        "total_projected_inflow": round(total_inflow, 2),
        "total_projected_outflow": round(total_outflow, 2),
        "net_projection":         round(total_inflow - total_outflow, 2),
        "generated_at":           today.isoformat(),
    }
