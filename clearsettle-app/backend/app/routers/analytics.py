"""
Analytics APIs — real DB-driven aggregations with mock-data fallback.

Prefix: /analytics

Endpoints
---------
GET /analytics/revenue          time-series: gross, fees, net by bucket
GET /analytics/fees             fee breakdown by category + fee_type
GET /analytics/payouts          payout time-series with status breakdown
GET /analytics/refunds          refund/return transaction trends
GET /analytics/marketplace      per-platform KPI comparison
GET /analytics/reconciliation   reconciliation health + discrepancy breakdown
GET /analytics/profitability    SKU-level profitability (no COGS)
GET /analytics/{sku}            single-SKU profitability (mock fallback only)

All endpoints accept ?platform=amazon to filter and fall back to demo data
when DATABASE_URL is not configured.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import (
    DASHBOARD_TREND,
    PROFIT,
    RETURNS,
    SETTLEMENTS,
)
from app.services.analytics import queries as analytics_queries

router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────────────────

def _is_db_user(user) -> bool:
    return hasattr(user, "companies")


def _company_id(user) -> UUID:
    if not _is_db_user(user) or not user.companies:
        raise HTTPException(status_code=422, detail="No company associated with this account.")
    return user.companies[0].id


# ── mock fallbacks ─────────────────────────────────────────────────────────────

_MOCK_DATES = [
    ("2025-12-01", "Dec 2025"), ("2026-01-01", "Jan 2026"),
    ("2026-02-01", "Feb 2026"), ("2026-03-01", "Mar 2026"),
    ("2026-04-01", "Apr 2026"), ("2026-05-01", "May 2026"),
]


def _mock_revenue_trends(platform: Optional[str], granularity: str) -> dict:
    series = [
        {
            "date":             d,
            "label":            label,
            "gross_revenue":    float(t["amount"]),
            "total_fees":       round(-float(t["amount"]) * 0.15, 0),
            "net_payout":       round(float(t["amount"]) * 0.85, 0),
            "settlement_count": 3 if i < 5 else 1,
            "orders":           int(float(t["amount"]) / 650),
            "by_platform":      {},
        }
        for i, ((d, label), t) in enumerate(zip(_MOCK_DATES, DASHBOARD_TREND))
    ]
    total_gross = sum(p["gross_revenue"] for p in series)
    total_fees  = sum(p["total_fees"]    for p in series)
    total_net   = sum(p["net_payout"]    for p in series)
    return {
        "granularity":        granularity,
        "date_from":          "2025-12-01",
        "date_to":            "2026-05-31",
        "platform":           platform,
        "cache_ttl_seconds":  0,
        "series":             series,
        "summary": {
            "total_gross":       total_gross,
            "total_fees":        total_fees,
            "total_net":         total_net,
            "total_settlements": sum(p["settlement_count"] for p in series),
            "total_orders":      sum(p["orders"] for p in series),
            "avg_fee_rate_pct":  round(abs(total_fees) / total_gross * 100, 2)
                                 if total_gross > 0 else 0.0,
        },
        "anomalies": [],
    }


def _mock_fee_breakdown(platform: Optional[str]) -> dict:
    items = SETTLEMENTS
    if platform:
        items = [s for s in items if s["plat"].lower() == platform.lower()]

    comm  = sum(s["comm"] for s in items)
    logi  = sum(s["logi"] for s in items)
    ret   = sum(s["ret"]  for s in items)
    tcs   = sum(s["tcs"]  for s in items)
    pen   = sum(s["pen"]  for s in items)
    total = comm + logi + ret + tcs + pen
    gross = sum(s["base"] for s in items)
    orders = sum(s["orders"] for s in items)

    return {
        "date_from": None, "date_to": None, "platform": platform,
        "cache_ttl_seconds": 0,
        "categories": {
            "referral_fees": float(-comm),
            "fba_fees":      float(-logi),
            "closing_fees":  0.0,
            "shipping_fees": 0.0,
            "tcs_taxes":     float(-tcs),
            "service_fees":  float(-pen),
            "other_fees":    0.0,
        },
        "fee_items": [
            {"fee_type": "ReferralFee",                        "total_amount": float(-comm), "count": orders},
            {"fee_type": "FBAPerUnitFulfillmentFee",           "total_amount": float(-logi), "count": orders},
            {"fee_type": "RefundTransaction",                  "total_amount": float(-ret),  "count": len(items)},
            {"fee_type": "MarketplaceFacilitatorTax-Principal","total_amount": float(-tcs),  "count": len(items)},
            {"fee_type": "ServiceFee",                         "total_amount": float(-pen),  "count": sum(1 for s in items if s["pen"] > 0)},
        ],
        "summary": {
            "total_fees":          float(-total),
            "total_gross_revenue": float(gross),
            "fee_rate_pct":        round(total / gross * 100, 2) if gross > 0 else 0.0,
        },
    }


def _mock_payout_trends(platform: Optional[str], granularity: str) -> dict:
    paid    = [s for s in SETTLEMENTS if s["status"] == "paid"]
    pending = [s for s in SETTLEMENTS if s["status"] == "pending"]
    if platform:
        paid    = [s for s in paid    if s["plat"].lower() == platform.lower()]
        pending = [s for s in pending if s["plat"].lower() == platform.lower()]

    series = [
        {
            "date": "2026-04-01", "label": "Apr 2026",
            "transferred": float(sum(s["net"] for s in paid)),
            "pending": 0.0, "failed": 0.0,
            "total": float(sum(s["net"] for s in paid)),
        },
        {
            "date": "2026-05-01", "label": "May 2026",
            "transferred": 0.0,
            "pending": float(sum(s["net"] for s in pending)),
            "failed": 0.0,
            "total": float(sum(s["net"] for s in pending)),
        },
    ]
    return {
        "granularity":        granularity,
        "platform":           platform,
        "cache_ttl_seconds":  0,
        "series":             series,
        "summary": {
            "total_transferred": sum(p["transferred"] for p in series),
            "total_pending":     sum(p["pending"]     for p in series),
            "total_failed":      0.0,
        },
        "anomalies": [],
    }


def _mock_refund_trends(platform: Optional[str], granularity: str) -> dict:
    items = RETURNS
    if platform:
        items = [r for r in items if r["plat"].lower() == platform.lower()]
    base_settlements = SETTLEMENTS
    if platform:
        base_settlements = [s for s in base_settlements if s["plat"].lower() == platform.lower()]

    total_refund = sum(r["total"] for r in items)
    total_gross  = sum(s["base"]  for s in base_settlements)
    series = [{
        "date":          "2026-05-01",
        "label":         "May 2026",
        "refund_count":  len(items),
        "refund_amount": float(total_refund),
        "refund_qty":    sum(r["qty"] for r in items),
    }]
    return {
        "granularity":        granularity,
        "platform":           platform,
        "cache_ttl_seconds":  0,
        "series":             series,
        "summary": {
            "total_refund_count":  len(items),
            "total_refund_amount": float(total_refund),
            "total_refund_qty":    sum(r["qty"] for r in items),
            "refund_rate_pct":     round(total_refund / total_gross * 100, 2) if total_gross > 0 else 0.0,
        },
        "anomalies": [],
    }


def _mock_marketplace_breakdown(platform: Optional[str]) -> dict:
    agg: dict[str, dict] = {}
    for s in SETTLEMENTS:
        plat = s["plat"].lower()
        if platform and plat != platform.lower():
            continue
        if plat not in agg:
            agg[plat] = {
                "platform": plat, "label": s["plat"],
                "settlement_count": 0, "gross_revenue": 0.0,
                "total_fees": 0.0, "net_payout": 0.0, "orders": 0,
                "refund_count": 0, "refund_amount": 0.0,
            }
        d = agg[plat]
        d["settlement_count"] += 1
        d["gross_revenue"]    += s["base"]
        d["total_fees"]       -= s["comm"] + s["logi"] + s["ret"] + s["tcs"] + s["pen"]
        d["net_payout"]       += s["net"]
        d["orders"]           += s["orders"]

    total_gross = sum(d["gross_revenue"] for d in agg.values())
    platforms = []
    for d in agg.values():
        gross  = d["gross_revenue"]
        orders = d["orders"]
        d["fee_rate_pct"]    = round(abs(d["total_fees"]) / gross * 100, 2) if gross > 0 else 0.0
        d["share_pct"]       = round(gross / total_gross * 100, 1) if total_gross > 0 else 0.0
        d["avg_order_value"] = round(gross / orders, 2) if orders > 0 else 0.0
        d["refund_rate_pct"] = 0.0
        platforms.append(d)

    platforms.sort(key=lambda x: -x["gross_revenue"])
    return {
        "date_from": None, "date_to": None,
        "cache_ttl_seconds": 0,
        "platforms": platforms,
        "summary": {
            "total_gross":    total_gross,
            "total_fees":     sum(d["total_fees"]  for d in platforms),
            "total_net":      sum(d["net_payout"]  for d in platforms),
            "total_orders":   sum(d["orders"]      for d in platforms),
            "platform_count": len(platforms),
        },
    }


def _mock_reconciliation_health(platform: Optional[str], days: int) -> dict:
    return {
        "platform":              platform,
        "days":                  days,
        "cache_ttl_seconds":     0,
        "health_score_pct":      100.0,
        "by_status":             {"clean": 0, "warning": 0, "critical": 0, "error": 0},
        "total_runs":            0,
        "total_variance":        0.0,
        "total_discrepancies":   0,
        "unresolved_count":      0,
        "unresolved_variance":   0.0,
        "discrepancy_breakdown": [],
    }


def _mock_profitability(platform: Optional[str], limit: int) -> dict:
    items = [
        {
            "sku":             p["sku"],
            "order_count":     100,
            "gross_revenue":   float(p["rev"]),
            "fees_total":      -float(p["fees"]),
            "net_revenue":     float(p["net"]),
            "qty":             100,
            "platforms":       [p["top"]],
            "fee_rate_pct":    round(float(p["fees"]) / float(p["rev"]) * 100, 2)
                               if p["rev"] > 0 else 0.0,
            "net_margin_pct":  round(float(p["net"])  / float(p["rev"]) * 100, 2)
                               if p["rev"] > 0 else 0.0,
            "avg_order_value": round(float(p["rev"]) / 100, 2),
        }
        for p in PROFIT
    ]
    if platform:
        items = [i for i in items if platform.lower() in [pl.lower() for pl in i["platforms"]]]
    items = items[:limit]

    total_gross = sum(i["gross_revenue"] for i in items)
    total_fees  = sum(i["fees_total"]    for i in items)
    total_net   = sum(i["net_revenue"]   for i in items)
    return {
        "date_from": None, "date_to": None, "platform": platform,
        "cache_ttl_seconds": 0,
        "items": items,
        "summary": {
            "total_skus":          len(items),
            "total_gross_revenue": total_gross,
            "total_fees":          total_fees,
            "total_net_revenue":   total_net,
            "avg_fee_rate_pct":    round(abs(total_fees) / total_gross * 100, 2)
                                   if total_gross > 0 else 0.0,
            "loss_making_skus":    sum(1 for i in items if i["net_revenue"] < 0),
        },
    }


# ── GET /analytics/revenue ─────────────────────────────────────────────────────

@router.get("/revenue")
async def get_revenue_analytics(
    platform:    Optional[str]  = Query(None),
    date_from:   Optional[date] = Query(None, description="Period start (YYYY-MM-DD)"),
    date_to:     Optional[date] = Query(None, description="Period end (YYYY-MM-DD)"),
    granularity: str            = Query("month", description="day | week | month"),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Revenue time-series: gross revenue, total fees, net payout per bucket.

    Each bucket includes a by_platform breakdown and a full summary.
    Anomaly detection flags buckets that deviate > 2 standard deviations
    from the series mean.
    """
    if db is None or not _is_db_user(user):
        return _mock_revenue_trends(platform, granularity)

    return await analytics_queries.get_revenue_trends(
        db, _company_id(user),
        date_from=date_from, date_to=date_to,
        granularity=granularity, platform=platform,
    )


# ── GET /analytics/fees ────────────────────────────────────────────────────────

@router.get("/fees")
async def get_fee_analytics(
    platform:  Optional[str]  = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Fee breakdown by category (referral, FBA, closing, shipping, TCS, service, other)
    and by individual fee_type. Includes aggregate fee rate vs gross revenue.
    """
    if db is None or not _is_db_user(user):
        return _mock_fee_breakdown(platform)

    return await analytics_queries.get_fee_breakdown(
        db, _company_id(user),
        date_from=date_from, date_to=date_to, platform=platform,
    )


# ── GET /analytics/payouts ─────────────────────────────────────────────────────

@router.get("/payouts")
async def get_payout_analytics(
    platform:    Optional[str]  = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    granularity: str            = Query("month"),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Payout time-series with transferred / pending / failed breakdown per bucket.
    Anomaly detection on the transferred series.
    """
    if db is None or not _is_db_user(user):
        return _mock_payout_trends(platform, granularity)

    return await analytics_queries.get_payout_trends(
        db, _company_id(user),
        date_from=date_from, date_to=date_to,
        granularity=granularity, platform=platform,
    )


# ── GET /analytics/refunds ─────────────────────────────────────────────────────

@router.get("/refunds")
async def get_refund_analytics(
    platform:    Optional[str]  = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    granularity: str            = Query("month"),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Return/refund transaction trends: count, amount, quantity per bucket.
    Includes overall refund rate (refund amount / shipment principal).
    """
    if db is None or not _is_db_user(user):
        return _mock_refund_trends(platform, granularity)

    return await analytics_queries.get_refund_trends(
        db, _company_id(user),
        date_from=date_from, date_to=date_to,
        granularity=granularity, platform=platform,
    )


# ── GET /analytics/marketplace ─────────────────────────────────────────────────

@router.get("/marketplace")
async def get_marketplace_analytics(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Per-platform KPI comparison: GMV, fees, net payout, order count, fee rate,
    market share %, average order value, and return rate.
    """
    if db is None or not _is_db_user(user):
        return _mock_marketplace_breakdown(None)

    return await analytics_queries.get_marketplace_breakdown(
        db, _company_id(user),
        date_from=date_from, date_to=date_to,
    )


# ── GET /analytics/reconciliation ─────────────────────────────────────────────

@router.get("/reconciliation")
async def get_reconciliation_analytics(
    platform: Optional[str] = Query(None),
    days:     int           = Query(90, ge=1, le=365, description="Look-back window in days"),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Reconciliation health summary: health score %, runs by status, unresolved
    discrepancy count and variance, and breakdown by discrepancy type + severity.
    """
    if db is None or not _is_db_user(user):
        return _mock_reconciliation_health(platform, days)

    return await analytics_queries.get_reconciliation_health(
        db, _company_id(user), platform=platform, days=days,
    )


# ── GET /analytics/profitability ───────────────────────────────────────────────

@router.get("/profitability")
async def get_profitability_analytics(
    platform:  Optional[str]  = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    limit:     int            = Query(25, ge=1, le=100),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    SKU-level profitability proxy derived from settlement_transactions + fees.
    Columns: gross revenue, platform fees deducted, net revenue, fee rate %,
    net margin %, and avg order value. Sorted by net revenue descending.

    Note: COGS is not available in the DB — net margin here is
    (revenue − platform fees) / revenue, not true P&L margin.
    """
    if db is None or not _is_db_user(user):
        return _mock_profitability(platform, limit)

    return await analytics_queries.get_profitability_metrics(
        db, _company_id(user),
        date_from=date_from, date_to=date_to,
        platform=platform, limit=limit,
    )


# ── GET /analytics/{sku} ───────────────────────────────────────────────────────

@router.get("/{sku}")
def get_sku_analytics(sku: str, user=Depends(get_current_user)):
    """
    Single-SKU profitability from the mock dataset.

    Real SKU lookup from settlement_transactions is available via
    GET /analytics/profitability?sku=... (planned extension).
    """
    item = next((p for p in PROFIT if p["sku"] == sku), None)
    if not item:
        raise HTTPException(status_code=404, detail="SKU not found.")
    return item
