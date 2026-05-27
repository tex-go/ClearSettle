"""
Cash Flow Forecast API

Prefix: /forecast

GET  /forecast/summary          — KPI summary (current month, last month, YTD)
GET  /forecast/snapshots        — stored period aggregates (paginated)
GET  /forecast/projections      — forward-looking projection
GET  /forecast/insights         — AI-generated insights
POST /forecast/generate         — trigger snapshot generation for a date range
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.services.forecast import aggregator, forecast_engine, snapshot_store, insight_engine
from app.schemas.forecast import (
    ForecastSummary,
    GenerateSnapshotRequest,
    InsightsResponse,
    ProjectionResponse,
    SnapshotOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["forecast"])


def _company_id(user) -> UUID:
    cid = getattr(user, "company_id", None)
    if not cid:
        raise HTTPException(status_code=400, detail="User has no associated company")
    return cid


# ── Summary KPIs ──────────────────────────────────────────────────────────────

@router.get("/summary", response_model=ForecastSummary)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    today = date.today()

    # Current month
    cur_start = today.replace(day=1)
    cur_data   = await aggregator.aggregate_settlements(
        db, company_id, start_date=cur_start, end_date=today, period_type="monthly"
    )
    cm = cur_data[0] if cur_data else {}

    # Last month
    first_of_last = (cur_start - timedelta(days=1)).replace(day=1)
    last_end      = cur_start - timedelta(days=1)
    lm_data = await aggregator.aggregate_settlements(
        db, company_id, start_date=first_of_last, end_date=last_end, period_type="monthly"
    )
    lm = lm_data[0] if lm_data else {}

    # YTD
    ytd_start = today.replace(month=1, day=1)
    ytd_data  = await aggregator.aggregate_settlements(
        db, company_id, start_date=ytd_start, end_date=today, period_type="monthly"
    )
    ytd_inflow  = sum(b.get("inflows", 0) for b in ytd_data)
    ytd_outflow = sum(b.get("outflows", 0) for b in ytd_data)

    # Platform breakdown (YTD)
    platform_map: dict[str, float] = {}
    for b in ytd_data:
        for p, v in (b.get("platform_breakdown") or {}).items():
            platform_map[p] = platform_map.get(p, 0.0) + v

    # Average monthly (last 6 months)
    six_start = (cur_start - timedelta(days=180))
    six_data  = await aggregator.aggregate_settlements(
        db, company_id, start_date=six_start, end_date=today, period_type="monthly"
    )
    avg_in  = sum(b.get("inflows", 0) for b in six_data) / max(len(six_data), 1)
    avg_out = sum(b.get("outflows", 0) for b in six_data) / max(len(six_data), 1)

    return {
        "current_month_inflow":  cm.get("inflows", 0.0),
        "current_month_outflow": cm.get("outflows", 0.0),
        "current_month_net":     cm.get("net", 0.0),
        "last_month_inflow":     lm.get("inflows", 0.0),
        "last_month_outflow":    lm.get("outflows", 0.0),
        "last_month_net":        lm.get("net", 0.0),
        "ytd_inflow":            round(ytd_inflow, 2),
        "ytd_outflow":           round(ytd_outflow, 2),
        "ytd_net":               round(ytd_inflow - ytd_outflow, 2),
        "avg_monthly_inflow":    round(avg_in, 2),
        "avg_monthly_outflow":   round(avg_out, 2),
        "platform_breakdown":    platform_map,
        "currency":              "INR",
        "as_of":                 today.isoformat(),
    }


# ── Stored snapshots ──────────────────────────────────────────────────────────

@router.get("/snapshots", response_model=list[SnapshotOut])
async def get_snapshots(
    period_type: str = Query(default="monthly", description="daily/weekly/monthly/quarterly"),
    limit:       int = Query(default=24, ge=1, le=120),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    snaps = await snapshot_store.list_snapshots(
        db, company_id, period_type=period_type, limit=limit
    )
    return [snapshot_store.snapshot_to_dict(s) for s in snaps]


# ── Forward projections ───────────────────────────────────────────────────────

@router.get("/projections", response_model=ProjectionResponse)
async def get_projections(
    horizon: str = Query(default="30d", description="7d | 30d | 90d | 1y"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if horizon not in ("7d", "30d", "90d", "1y"):
        raise HTTPException(status_code=400, detail="horizon must be 7d, 30d, 90d, or 1y")
    company_id = _company_id(user)
    return await forecast_engine.generate_projections(db, company_id, horizon=horizon)


# ── AI Insights ───────────────────────────────────────────────────────────────

@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    horizon: str = Query(default="30d"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    settings=Depends(get_settings),
):
    company_id = _company_id(user)

    snaps = await snapshot_store.list_snapshots(
        db, company_id, period_type="monthly", limit=12
    )
    snap_dicts = [snapshot_store.snapshot_to_dict(s) for s in snaps]

    projection = await forecast_engine.generate_projections(
        db, company_id, horizon=horizon
    )

    result = await insight_engine.generate_insights(
        snap_dicts, projection,
        anthropic_api_key=settings.anthropic_api_key,
    )
    return result


# ── Generate / refresh snapshots ──────────────────────────────────────────────

@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_snapshots(
    payload: GenerateSnapshotRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Compute and store cash flow snapshots for the requested date range.
    Returns the number of snapshots created/updated.
    """
    company_id = _company_id(user)
    today = date.today()
    start = payload.start_date or today.replace(month=1, day=1)
    end   = payload.end_date   or today

    buckets = await aggregator.aggregate_settlements(
        db, company_id,
        start_date=start,
        end_date=end,
        period_type=payload.period_type,
    )

    # Compute running balance for opening/closing
    balance = await aggregator.get_current_balance(db, company_id, as_of=start)
    upserted = 0
    for b in sorted(buckets, key=lambda x: x["period_start"]):
        opening = balance
        closing  = opening + b.get("net", 0)
        snap_date = date.fromisoformat(b["period_start"])
        await snapshot_store.upsert_snapshot(
            db, company_id,
            snapshot_date=snap_date,
            period_type=payload.period_type,
            data={
                **b,
                "opening_balance": opening,
                "closing_balance": closing,
            },
        )
        balance = closing
        upserted += 1

    logger.info("generate_snapshots: %d snapshots upserted for company=%s", upserted, company_id)
    return {"snapshots_generated": upserted, "period_type": payload.period_type}
