"""
Dashboard APIs — summary KPIs and notifications.

GET /dashboard/summary      — main dashboard cards (real DB or mock fallback)
GET /dashboard/notifications — static alert feed (no real notification system yet)

The summary endpoint falls back to computed mock data when DATABASE_URL is not
set, preserving the demo experience.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import (
    DASHBOARD_TREND,
    NOTIFICATIONS,
    PLATFORM_SHARE,
    SETTLEMENTS,
)
from app.services.analytics import queries as analytics_queries

router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────────────────

def _is_db_user(user) -> bool:
    return hasattr(user, "companies")


def _company_id(user):
    from fastapi import HTTPException, status
    from uuid import UUID
    if not _is_db_user(user) or not user.companies:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No company associated with this account.",
        )
    return user.companies[0].id


# ── mock fallback ──────────────────────────────────────────────────────────────

def _mock_summary(platform: Optional[str] = None) -> dict:
    items = SETTLEMENTS
    if platform:
        items = [s for s in items if s["plat"].lower() == platform.lower()]

    paid    = [s for s in items if s["status"] == "paid"]
    pending = [s for s in items if s["status"] == "pending"]

    total_gross  = sum(s["base"] for s in items)
    total_fees   = sum(s["comm"] + s["logi"] + s["ret"] + s["tcs"] + s["pen"] for s in items)
    net_paid     = sum(s["net"]  for s in paid)
    pending_amt  = sum(s["net"]  for s in pending)
    total_orders = sum(s["orders"] for s in items)

    # 30-day trend: use DASHBOARD_TREND as daily mock (frontend can interpret)
    _MOCK_TREND_DATES = [
        "2025-12-01", "2026-01-01", "2026-02-01",
        "2026-03-01", "2026-04-01", "2026-05-01",
    ]
    revenue_trend = [
        {"date": d, "gross": float(t["amount"]), "net": round(float(t["amount"]) * 0.85, 0)}
        for d, t in zip(_MOCK_TREND_DATES, DASHBOARD_TREND)
    ]

    return {
        "cache_ttl_seconds": 0,
        "settlements": {
            "total":            len(items),
            "closed_count":     len(paid),
            "open_count":       len(pending),
            "processing_count": 0,
            "total_gross":      float(total_gross),
            "total_fees":       float(-total_fees),
            "total_net_paid":   float(net_paid),
            "pending_amount":   float(pending_amt),
            "total_orders":     total_orders,
        },
        "payouts": {
            "transferred": float(net_paid),
            "pending":     float(pending_amt),
            "failed":      0.0,
        },
        "reconciliation": {
            "clean": 0, "warning": 0, "critical": 0, "error": 0,
            "total_runs":               0,
            "unresolved_discrepancies": 0,
            "total_variance":           0.0,
        },
        "revenue_trend":  revenue_trend,
        "platform_share": PLATFORM_SHARE,
    }


# ── GET /dashboard/summary ─────────────────────────────────────────────────────

@router.get("/summary")
async def get_summary(
    platform: Optional[str] = Query(None, description="Filter by platform (amazon, flipkart, …)"),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Main dashboard KPI summary.

    Returns settlement health, payout status, reconciliation overview,
    a 30-day daily revenue trend, and platform market-share breakdown.
    Falls back to demo data when the database is not configured.
    """
    if db is None or not _is_db_user(user):
        return _mock_summary(platform)

    return await analytics_queries.get_dashboard_summary(
        db, _company_id(user), platform=platform
    )


# ── GET /dashboard/notifications ──────────────────────────────────────────────

@router.get("/notifications")
def get_notifications(user=Depends(get_current_user)):
    """
    Recent alert feed.

    Currently returns a curated static list.  A real notification system
    (push events from reconciliation engine + ingestion pipeline) is
    planned for a future session.
    """
    return {"items": NOTIFICATIONS}
