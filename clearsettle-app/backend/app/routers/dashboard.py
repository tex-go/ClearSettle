"""
Dashboard APIs — summary KPIs and notifications.

GET /dashboard/summary       — main dashboard cards (real DB or empty)
GET /dashboard/notifications — live alert feed derived from real DB data
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import DASHBOARD_TREND, PLATFORM_SHARE, SETTLEMENTS
from app.db.models.discrepancy_event import DiscrepancyEvent
from app.db.models.flipkart_report import (
    FlipkartReport, FlipkartReconIssue, FlipkartSkuPL, FlipkartSummary,
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
        return {
            "cache_ttl_seconds": 0,
            "settlements": {"total": 0, "closed_count": 0, "open_count": 0, "processing_count": 0, "total_gross": 0.0, "total_fees": 0.0, "total_net_paid": 0.0, "pending_amount": 0.0, "total_orders": 0},
            "payouts": {"transferred": 0.0, "pending": 0.0, "failed": 0.0},
            "reconciliation": {"clean": 0, "warning": 0, "critical": 0, "error": 0, "total_runs": 0, "unresolved_discrepancies": 0, "total_variance": 0.0},
            "revenue_trend": [],
            "platform_share": [],
        }

    cid = _company_id(user)
    result = await analytics_queries.get_dashboard_summary(db, cid, platform=platform)

    # If legacy settlements table is empty, try ingestion_ledger first (new ETL path)
    if result["settlements"]["total_gross"] == 0:
        ledger_result = await analytics_queries.get_ingestion_ledger_kpis(
            db, cid, platform=platform
        )
        if ledger_result:
            return ledger_result

        # Last resort: Flipkart P&L legacy tables
        fk_result = await analytics_queries.get_flipkart_dashboard_summary(db, cid)
        if fk_result:
            return fk_result

    return result


# ── Notification helpers ───────────────────────────────────────────────────────

def _relative_time(dt: datetime) -> str:
    if dt is None:
        return "recently"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    secs = int(diff.total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        m = secs // 60
        return f"{m} minute{'s' if m > 1 else ''} ago"
    if secs < 86400:
        h = secs // 3600
        return f"{h} hour{'s' if h > 1 else ''} ago"
    d = secs // 86400
    if d == 1:
        return "yesterday"
    if d < 30:
        return f"{d} days ago"
    if d < 60:
        return "last month"
    return dt.strftime("%b %d, %Y")


def _inr(amount) -> str:
    try:
        n = abs(float(amount))
        if n >= 1e7:
            return f"₹{n/1e7:.1f} Cr"
        if n >= 1e5:
            return f"₹{n/1e5:.1f}L"
        if n >= 1e3:
            return f"₹{n/1e3:.0f}K"
        return f"₹{n:.0f}"
    except Exception:
        return "₹0"


_RECON_ISSUE_TITLES = {
    "commission_overcharge":    ("Commission Overcharge Detected",  "error"),
    "fee_overcharge":           ("Platform Fee Overcharge",         "error"),
    "missing_settlement":       ("Missing Settlement Amount",        "error"),
    "settlement_variance":      ("Settlement Variance Found",        "warn"),
    "return_deduction_mismatch":("Return Deduction Mismatch",        "warn"),
    "tcs_mismatch":             ("TCS Amount Mismatch",              "warn"),
    "duplicate_deduction":      ("Duplicate Deduction Detected",    "error"),
    "unexpected_fee":           ("Unexpected Fee Charged",           "warn"),
    "penalty_overcharge":       ("Penalty Amount Disputed",          "warn"),
}

_DISC_TYPE_TITLES = {
    "OVERCHARGE_REFERRAL_FEE": ("Commission Overcharge",      "error"),
    "OVERCHARGE_FBA_FEE":      ("FBA Fee Overcharge",         "error"),
    "PAYOUT_AMOUNT_MISMATCH":  ("Payout Amount Mismatch",     "warn"),
    "MISSING_PAYOUT":          ("Missing Payout Detected",    "error"),
    "DUPLICATE_DEDUCTION":     ("Duplicate Deduction",        "error"),
    "PENALTY_MISMATCH":        ("Penalty Mismatch",           "warn"),
    "UNEXPECTED_FEE":          ("Unexpected Fee",             "warn"),
}


async def _build_notifications(db: AsyncSession, company_id) -> list[dict]:
    items: list[tuple[datetime, dict]] = []   # (sort_dt, notification)
    nid = 0

    def _next_id() -> int:
        nonlocal nid
        nid += 1
        return nid

    # ── 1. FlipkartReconIssue — open critical + warning issues ────────────────
    recon_rows = (await db.execute(
        select(FlipkartReconIssue)
        .where(
            FlipkartReconIssue.company_id == company_id,
            FlipkartReconIssue.status == "open",
        )
        .order_by(FlipkartReconIssue.created_at.desc())
        .limit(10)
    )).scalars().all()

    for r in recon_rows:
        title_map = _RECON_ISSUE_TITLES.get(r.issue_type, (None, None))
        title = title_map[0] or r.issue_type.replace("_", " ").title()
        ntype = title_map[1] if r.severity == "critical" else "warn"
        sub = r.description or ""
        if r.variance and abs(float(r.variance)) > 0:
            sub = f"{sub} — {_inr(r.variance)} variance"
        if r.sku_code:
            sub = f"SKU {r.sku_code}: {sub}"
        items.append((r.created_at, {
            "id": _next_id(), "type": ntype,
            "title": title, "sub": sub.strip(" —"),
            "time": _relative_time(r.created_at), "action": "View Reconciliation",
        }))

    # ── 2. FlipkartSkuPL — high return rate SKUs ──────────────────────────────
    high_return_skus = (await db.execute(
        select(FlipkartSkuPL)
        .join(FlipkartReport, FlipkartSkuPL.report_id == FlipkartReport.id)
        .where(
            FlipkartSkuPL.company_id == company_id,
            FlipkartSkuPL.high_return_rate == True,
            FlipkartReport.status == "done",
        )
        .order_by(FlipkartSkuPL.return_rate_pct.desc().nullslast())
        .limit(3)
    )).scalars().all()

    for s in high_return_skus:
        rate = f"{float(s.return_rate_pct):.1f}%" if s.return_rate_pct else "high"
        name = s.product_title[:40] if s.product_title else s.sku_code or "Unknown SKU"
        items.append((datetime.now(timezone.utc), {
            "id": _next_id(), "type": "warn",
            "title": "High Return Rate Detected",
            "sub": f"{name} — {rate} return rate on Flipkart",
            "time": "from latest report", "action": "View SKU Analysis",
        }))

    # ── 3. FlipkartSkuPL — loss-making SKUs ──────────────────────────────────
    loss_skus = (await db.execute(
        select(FlipkartSkuPL)
        .join(FlipkartReport, FlipkartSkuPL.report_id == FlipkartReport.id)
        .where(
            FlipkartSkuPL.company_id == company_id,
            FlipkartSkuPL.is_loss_making == True,
            FlipkartReport.status == "done",
        )
        .order_by(FlipkartSkuPL.net_earnings.asc().nullslast())
        .limit(2)
    )).scalars().all()

    for s in loss_skus:
        name = s.product_title[:40] if s.product_title else s.sku_code or "Unknown SKU"
        loss_str = f" — net loss {_inr(s.net_earnings)}" if s.net_earnings else ""
        items.append((datetime.now(timezone.utc), {
            "id": _next_id(), "type": "warn",
            "title": "Loss-Making SKU Identified",
            "sub": f"{name}{loss_str}",
            "time": "from latest report", "action": "View SKU Analysis",
        }))

    # ── 4. FlipkartReport — recently processed / failed ───────────────────────
    recent_reports = (await db.execute(
        select(FlipkartReport)
        .where(
            FlipkartReport.company_id == company_id,
            FlipkartReport.status.in_(["done", "failed"]),
        )
        .order_by(FlipkartReport.processed_at.desc().nullslast())
        .limit(5)
    )).scalars().all()

    for rep in recent_reports:
        ts = rep.processed_at or rep.uploaded_at
        if rep.status == "done":
            items.append((ts, {
                "id": _next_id(), "type": "success",
                "title": "Report Processed Successfully",
                "sub": f"{rep.original_name} — {rep.report_period or 'analysis complete'}",
                "time": _relative_time(ts), "action": "View Analysis",
            }))
        elif rep.status == "failed":
            items.append((ts, {
                "id": _next_id(), "type": "error",
                "title": "Report Processing Failed",
                "sub": f"{rep.original_name} — {rep.error_message or 'check file format'}",
                "time": _relative_time(ts), "action": "Re-upload",
            }))

    # ── 5. FlipkartSummary — pending settlement amount ────────────────────────
    summaries = (await db.execute(
        select(FlipkartSummary)
        .join(FlipkartReport, FlipkartSummary.report_id == FlipkartReport.id)
        .where(
            FlipkartSummary.company_id == company_id,
            FlipkartReport.status == "done",
            FlipkartSummary.amount_pending > 0,
        )
        .order_by(FlipkartReport.processed_at.desc().nullslast())
        .limit(1)
    )).scalars().all()

    for sm in summaries:
        items.append((datetime.now(timezone.utc), {
            "id": _next_id(), "type": "info",
            "title": "Settlement Amount Pending",
            "sub": f"{_inr(sm.amount_pending)} pending from Flipkart — expected in next cycle",
            "time": "current period", "action": "View Settlement",
        }))

    # ── 6. DiscrepancyEvent — unresolved critical (Amazon + others) ───────────
    disc_rows = (await db.execute(
        select(DiscrepancyEvent)
        .where(
            DiscrepancyEvent.company_id == company_id,
            DiscrepancyEvent.is_resolved == False,
        )
        .order_by(DiscrepancyEvent.created_at.desc())
        .limit(5)
    )).scalars().all()

    for d in disc_rows:
        title_map = _DISC_TYPE_TITLES.get(d.discrepancy_type, (None, None))
        title = title_map[0] or d.discrepancy_type.replace("_", " ").title()
        ntype = title_map[1] if title_map[1] else ("error" if d.severity == "critical" else "warn")
        platform = (d.platform or "Platform").title()
        sub = d.description or ""
        if d.variance_amount and abs(float(d.variance_amount)) > 0:
            sub = f"{platform}: {sub} — {_inr(d.variance_amount)} variance"
        items.append((d.created_at, {
            "id": _next_id(), "type": ntype,
            "title": title, "sub": sub.strip(),
            "time": _relative_time(d.created_at), "action": "View Disputes",
        }))

    # ── Sort by recency, cap at 20 ─────────────────────────────────────────────
    items.sort(key=lambda x: x[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return [n for _, n in items[:20]]


# ── GET /dashboard/notifications ──────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    if db is None or not _is_db_user(user) or not user.companies:
        return {"items": []}

    try:
        company_id = user.companies[0].id
        notifications = await _build_notifications(db, company_id)
        return {"items": notifications}
    except Exception:
        return {"items": []}
