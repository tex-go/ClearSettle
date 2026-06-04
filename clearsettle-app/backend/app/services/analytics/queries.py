"""
Analytics query service — aggregate SQL powering the dashboard and analytics APIs.

All public functions accept an open AsyncSession and company_id: UUID plus
optional keyword-only filters. They return plain dicts ready for JSON
serialisation.  No ORM object is returned; callers never touch the ORM layer.

Recommended cache TTLs (implement at the HTTP or Redis layer):
  get_dashboard_summary       300 s  (changes when settlements are ingested)
  get_revenue_trends          300 s
  get_fee_breakdown           600 s  (fee data rarely changes after ingestion)
  get_payout_trends           300 s
  get_refund_trends           600 s
  get_marketplace_breakdown   600 s
  get_reconciliation_health   300 s
  get_profitability_metrics   600 s
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.discrepancy_event import DiscrepancyEvent
from app.db.models.fee import Fee
from app.db.models.ingestion import IngestionLedger
from app.db.models.payout_event import PayoutEvent
from app.db.models.reconciliation_result import ReconciliationResult
from app.db.models.settlement import Settlement
from app.db.models.settlement_transaction import SettlementTransaction

# ── Constants ──────────────────────────────────────────────────────────────────

_REFERRAL_TYPES = frozenset({"ReferralFee", "Commission"})
_FBA_TYPES      = frozenset({"FBAPerUnitFulfillmentFee", "FBAWeightBasedFee"})
_CLOSING_TYPES  = frozenset({"VariableClosingFee", "PerItemFee"})
_SHIPPING_TYPES = frozenset({"Shipping", "ShippingCharge", "ShippingHBFee", "ReturnShipping"})
_TCS_TYPES      = frozenset({"MarketplaceFacilitatorTax-Principal", "MarketplaceFacilitatorTax-Shipping"})
_SERVICE_TYPES  = frozenset({"ServiceFee"})

_PLATFORM_LABELS: dict[str, str] = {
    "amazon": "Amazon", "flipkart": "Flipkart", "meesho": "Meesho",
    "myntra": "Myntra", "nykaa": "Nykaa", "ajio": "AJIO",
    "snapdeal": "Snapdeal", "jiomart": "JioMart",
}

_VALID_GRANULARITIES = {"day", "week", "month"}
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ── Private helpers ────────────────────────────────────────────────────────────

def _trunc(granularity: str) -> str:
    return granularity if granularity in _VALID_GRANULARITIES else "month"


def _date_trunc(granularity: str, col):
    """date_trunc with granularity as a SQL literal (not a bind param).

    asyncpg turns string arguments into bind params, causing PostgreSQL to
    reject GROUP BY / ORDER BY clauses that reference the same expression
    from SELECT (different param slots → not recognised as equal). Embedding
    the granularity as a literal_column fixes the grouping error.
    """
    return func.date_trunc(literal_column(f"'{granularity}'"), col)


def _bucket_label(dt: datetime, granularity: str) -> str:
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    if granularity == "week":
        iso = dt.isocalendar()
        return f"W{iso[1]:02d} {dt.year}"
    return f"{_MONTHS[dt.month - 1]} {dt.year}"


def _fee_category(fee_type: str) -> str:
    if fee_type in _REFERRAL_TYPES: return "referral_fees"
    if fee_type in _FBA_TYPES:      return "fba_fees"
    if fee_type in _CLOSING_TYPES:  return "closing_fees"
    if fee_type in _SHIPPING_TYPES: return "shipping_fees"
    if fee_type in _TCS_TYPES:      return "tcs_taxes"
    if fee_type in _SERVICE_TYPES:  return "service_fees"
    return "other_fees"


def _dt_from(d: Optional[date]) -> Optional[datetime]:
    return datetime(d.year, d.month, d.day, 0, 0, 0) if d else None


def _dt_to(d: Optional[date]) -> Optional[datetime]:
    return datetime(d.year, d.month, d.day, 23, 59, 59) if d else None


def _detect_anomalies(
    series: list[dict],
    metric: str,
    z_threshold: float = 2.0,
    min_std_ratio: float = 0.05,
) -> list[dict]:
    """Flag time-series points that deviate beyond z_threshold standard deviations."""
    values = [float(p.get(metric) or 0) for p in series]
    if len(values) < 3:
        return []
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance)
    if mean == 0 or std < abs(mean) * min_std_ratio:
        return []
    anomalies = []
    for point, value in zip(series, values):
        z = abs(value - mean) / std
        if z > z_threshold:
            anomalies.append({
                "date":      point.get("date"),
                "label":     point.get("label"),
                "metric":    metric,
                "value":     round(value, 2),
                "mean":      round(mean, 2),
                "z_score":   round(z, 2),
                "direction": "spike" if value > mean else "dip",
            })
    return anomalies


# ── 1. Dashboard summary ───────────────────────────────────────────────────────

async def get_dashboard_summary(
    db: AsyncSession,
    company_id: UUID,
    *,
    platform: Optional[str] = None,
) -> dict:
    """
    Five lightweight aggregate queries that power the main dashboard cards:
    settlement health, fee totals, payout status, reconciliation overview,
    30-day daily revenue trend, and platform share pie.
    """
    # ── 1a. Settlement aggregate by status ────────────────────────────────────
    settle_q = (
        select(
            Settlement.status,
            func.count(Settlement.id).label("cnt"),
            func.coalesce(func.sum(Settlement.total_amount), 0).label("gross"),
            func.coalesce(func.sum(Settlement.fund_transfer_amount), 0).label("net"),
            func.coalesce(func.sum(Settlement.fees_total), 0).label("fees"),
            func.coalesce(func.sum(Settlement.transactions_count), 0).label("orders"),
        )
        .where(Settlement.company_id == company_id)
        .group_by(Settlement.status)
    )
    if platform:
        settle_q = settle_q.where(Settlement.platform == platform)

    settle_rows = (await db.execute(settle_q)).all()
    by_status: dict[str, dict] = {}
    for row in settle_rows:
        by_status[row.status] = {
            "count":  row.cnt,
            "gross":  float(row.gross or 0),
            "net":    float(row.net or 0),
            "fees":   float(row.fees or 0),
            "orders": int(row.orders or 0),
        }

    closed     = by_status.get("closed",     {"count": 0, "gross": 0.0, "net": 0.0, "fees": 0.0, "orders": 0})
    open_s     = by_status.get("open",       {"count": 0, "gross": 0.0, "net": 0.0, "fees": 0.0, "orders": 0})
    processing = by_status.get("processing", {"count": 0, "gross": 0.0, "net": 0.0, "fees": 0.0, "orders": 0})
    total_gross = sum(v["gross"] for v in by_status.values())
    total_fees  = sum(v["fees"]  for v in by_status.values())
    total_orders = sum(v["orders"] for v in by_status.values())

    # ── 1b. Payout totals by status ───────────────────────────────────────────
    payout_q = (
        select(
            PayoutEvent.status,
            func.coalesce(func.sum(PayoutEvent.amount), 0).label("total"),
        )
        .where(PayoutEvent.company_id == company_id)
        .group_by(PayoutEvent.status)
    )
    if platform:
        payout_q = payout_q.where(PayoutEvent.platform == platform)

    payout_summary: dict[str, float] = {"transferred": 0.0, "pending": 0.0, "failed": 0.0}
    for row in (await db.execute(payout_q)).all():
        if row.status in payout_summary:
            payout_summary[row.status] = float(row.total or 0)

    # ── 1c. Reconciliation health ──────────────────────────────────────────────
    recon_q = (
        select(
            ReconciliationResult.status,
            func.count(ReconciliationResult.id).label("cnt"),
        )
        .where(ReconciliationResult.company_id == company_id)
        .group_by(ReconciliationResult.status)
    )
    if platform:
        recon_q = recon_q.where(ReconciliationResult.platform == platform)

    recon_by_status: dict[str, int] = {"clean": 0, "warning": 0, "critical": 0, "error": 0}
    for row in (await db.execute(recon_q)).all():
        if row.status in recon_by_status:
            recon_by_status[row.status] = row.cnt

    unresolv_q = select(
        func.count(DiscrepancyEvent.id).label("cnt"),
        func.coalesce(func.sum(func.abs(DiscrepancyEvent.variance_amount)), 0).label("variance"),
    ).where(
        DiscrepancyEvent.company_id == company_id,
        DiscrepancyEvent.is_resolved == False,  # noqa: E712
    )
    if platform:
        unresolv_q = unresolv_q.where(DiscrepancyEvent.platform == platform)
    unresolv_row = (await db.execute(unresolv_q)).one()

    # ── 1d. 30-day daily revenue trend ────────────────────────────────────────
    cutoff = datetime.utcnow() - timedelta(days=30)
    trend_q = (
        select(
            _date_trunc("day", Settlement.period_end).label("day"),
            func.coalesce(func.sum(Settlement.total_amount), 0).label("gross"),
            func.coalesce(func.sum(Settlement.fund_transfer_amount), 0).label("net"),
        )
        .where(
            Settlement.company_id == company_id,
            Settlement.period_end >= cutoff,
        )
        .group_by(_date_trunc("day", Settlement.period_end))
        .order_by(_date_trunc("day", Settlement.period_end))
    )
    if platform:
        trend_q = trend_q.where(Settlement.platform == platform)

    revenue_trend = [
        {
            "date":  row.day.strftime("%Y-%m-%d"),
            "gross": float(row.gross or 0),
            "net":   float(row.net or 0),
        }
        for row in (await db.execute(trend_q)).all()
    ]

    # ── 1e. Platform share (all-time, by gross revenue) ───────────────────────
    share_q = (
        select(
            Settlement.platform,
            func.coalesce(func.sum(Settlement.total_amount), 0).label("gross"),
            func.count(Settlement.id).label("cnt"),
        )
        .where(Settlement.company_id == company_id)
        .group_by(Settlement.platform)
    )
    share_rows = (await db.execute(share_q)).all()
    total_plat_gross = sum(float(r.gross or 0) for r in share_rows)
    platform_share = sorted(
        [
            {
                "platform":  r.platform,
                "label":     _PLATFORM_LABELS.get(r.platform, r.platform.title()),
                "gross":     float(r.gross or 0),
                "count":     r.cnt,
                "share_pct": round(float(r.gross or 0) / total_plat_gross * 100, 1)
                             if total_plat_gross > 0 else 0.0,
            }
            for r in share_rows
        ],
        key=lambda x: -x["gross"],
    )

    return {
        "cache_ttl_seconds": 300,
        "settlements": {
            "total":            sum(v["count"] for v in by_status.values()),
            "closed_count":     closed["count"],
            "open_count":       open_s["count"],
            "processing_count": processing["count"],
            "total_gross":      total_gross,
            "total_fees":       total_fees,
            "total_net_paid":   closed["net"],
            "pending_amount":   open_s["net"] + processing["net"],
            "total_orders":     total_orders,
        },
        "payouts": payout_summary,
        "reconciliation": {
            **recon_by_status,
            "total_runs":               sum(recon_by_status.values()),
            "unresolved_discrepancies": int(unresolv_row.cnt or 0),
            "total_variance":           float(unresolv_row.variance or 0),
        },
        "revenue_trend":  revenue_trend,
        "platform_share": platform_share,
    }


# ── 1b. Dashboard KPIs directly from ingestion_ledger ─────────────────────────

_SALE_TX    = frozenset({"sale", "order", "sold", "my_share", "forward"})
_RETURN_TX  = frozenset({"return", "returned", "refund", "rto"})
_FEE_TX     = frozenset({"fee", "commission", "fixed_fee", "shipping_fee",
                          "reverse_shipping", "collection_fee", "marketplace_fee"})
_TAX_TX     = frozenset({"tax", "tds", "tcs", "gst", "tax_tds", "tax_tcs"})
_PAYOUT_TX  = frozenset({"payout", "settlement", "transfer", "bank_settlement",
                          "net_settlement", "neft", "remittance"})


async def get_ingestion_ledger_kpis(
    db: AsyncSession,
    company_id: UUID,
    *,
    platform: Optional[str] = None,
) -> dict:
    """
    Compute dashboard KPIs directly from ingestion_ledger.

    This is the fallback used when the legacy settlements table is empty
    (e.g. before manual reconciliation runs or on a fresh database).
    Returns the same shape as get_dashboard_summary() so callers can swap
    between the two without changing downstream code.
    """
    q = select(IngestionLedger).where(IngestionLedger.company_id == company_id)
    if platform:
        q = q.where(IngestionLedger.platform == platform)
    rows = (await db.execute(q)).scalars().all()

    if not rows:
        return None

    gross      = 0.0
    returns    = 0.0
    fees       = 0.0
    taxes      = 0.0
    payout     = 0.0
    order_ids: set = set()
    platforms: dict = {}
    dates: list = []

    for r in rows:
        amt = float(r.amount or 0)
        tx  = (r.transaction_type or "").lower()
        plat = (r.platform or "unknown").lower()
        platforms[plat] = platforms.get(plat, 0) + max(amt, 0)
        if r.order_id:
            order_ids.add(r.order_id)
        if r.transaction_date:
            dates.append(r.transaction_date[:10])  # ISO date

        if tx in _SALE_TX:
            gross += amt
        elif tx in _RETURN_TX:
            returns += amt
        elif tx in _FEE_TX:
            fees += amt
        elif tx in _TAX_TX:
            taxes += amt
        elif tx in _PAYOUT_TX:
            payout += amt

    net_sales      = gross + returns
    net_settlement = payout if payout != 0 else net_sales + fees + taxes
    total_fees     = abs(fees) + abs(taxes)
    total_orders   = len(order_ids)

    # Build a 6-month revenue trend from ingestion_ledger dates
    from collections import defaultdict
    monthly: dict = defaultdict(float)
    for d in dates:
        try:
            ym = d[:7]  # YYYY-MM
            monthly[ym] += 0  # will re-aggregate below
        except Exception:
            pass

    # Re-aggregate by month
    monthly_gross: dict = defaultdict(float)
    monthly_net:   dict = defaultdict(float)
    for r in rows:
        tx  = (r.transaction_type or "").lower()
        amt = float(r.amount or 0)
        d   = r.transaction_date or r.settlement_date
        if not d:
            continue
        ym = d[:7]
        if tx in _SALE_TX:
            monthly_gross[ym] += amt
        elif tx in _PAYOUT_TX:
            monthly_net[ym] += amt

    revenue_trend = [
        {"date": f"{ym}-01", "label": ym, "gross": round(g, 2),
         "net": round(monthly_net.get(ym, g * 0.85), 2)}
        for ym, g in sorted(monthly_gross.items())[-6:]
    ]

    # Platform share
    total_plat = sum(platforms.values()) or 1
    platform_share = sorted(
        [
            {
                "platform":  p,
                "label":     _PLATFORM_LABELS.get(p, p.title()),
                "gross":     round(v, 2),
                "count":     0,
                "share_pct": round(v / total_plat * 100, 1),
            }
            for p, v in platforms.items()
        ],
        key=lambda x: -x["gross"],
    )

    return {
        "cache_ttl_seconds": 60,
        "data_source": "ingestion_ledger",
        "settlements": {
            "total":            1,
            "closed_count":     1 if payout > 0 else 0,
            "open_count":       0 if payout > 0 else 1,
            "processing_count": 0,
            "total_gross":      round(gross, 2),
            "total_fees":       round(-total_fees, 2),
            "total_net_paid":   round(net_settlement, 2),
            "pending_amount":   0.0,
            "total_orders":     total_orders,
        },
        "payouts": {
            "transferred": round(net_settlement, 2) if payout > 0 else 0.0,
            "pending":     round(net_settlement, 2) if payout <= 0 else 0.0,
            "failed":      0.0,
        },
        "reconciliation": {
            "clean": 0, "warning": 0, "critical": 0, "error": 0,
            "total_runs": 0, "unresolved_discrepancies": 0, "total_variance": 0.0,
        },
        "revenue_trend":  revenue_trend,
        "platform_share": platform_share,
    }


# ── 2. Revenue trends ──────────────────────────────────────────────────────────

async def get_revenue_trends(
    db: AsyncSession,
    company_id: UUID,
    *,
    date_from:   Optional[date] = None,
    date_to:     Optional[date] = None,
    granularity: str = "month",
    platform:    Optional[str] = None,
) -> dict:
    """
    Time-series of gross revenue, total fees, and net payout grouped by
    granularity bucket (day / week / month), optionally filtered by platform.
    Each bucket also includes a by_platform breakdown.
    """
    g = _trunc(granularity)
    q = (
        select(
            _date_trunc(g, Settlement.period_end).label("bucket"),
            Settlement.platform,
            func.coalesce(func.sum(Settlement.total_amount), 0).label("gross"),
            func.coalesce(func.sum(Settlement.fees_total), 0).label("fees"),
            func.coalesce(func.sum(Settlement.fund_transfer_amount), 0).label("net"),
            func.count(Settlement.id).label("settlement_count"),
            func.coalesce(func.sum(Settlement.transactions_count), 0).label("orders"),
        )
        .where(Settlement.company_id == company_id)
        .group_by(_date_trunc(g, Settlement.period_end), Settlement.platform)
        .order_by(_date_trunc(g, Settlement.period_end))
    )
    if platform:
        q = q.where(Settlement.platform == platform)
    if date_from:
        q = q.where(Settlement.period_end >= _dt_from(date_from))
    if date_to:
        q = q.where(Settlement.period_end <= _dt_to(date_to))

    buckets: dict[str, dict] = {}
    for row in (await db.execute(q)).all():
        key = row.bucket.isoformat()
        if key not in buckets:
            buckets[key] = {
                "date":             key,
                "label":            _bucket_label(row.bucket, g),
                "gross_revenue":    0.0,
                "total_fees":       0.0,
                "net_payout":       0.0,
                "settlement_count": 0,
                "orders":           0,
                "by_platform":      {},
            }
        b = buckets[key]
        b["gross_revenue"]    += float(row.gross or 0)
        b["total_fees"]       += float(row.fees or 0)
        b["net_payout"]       += float(row.net or 0)
        b["settlement_count"] += row.settlement_count
        b["orders"]           += int(row.orders or 0)
        b["by_platform"][row.platform] = {
            "gross": float(row.gross or 0),
            "fees":  float(row.fees or 0),
            "net":   float(row.net or 0),
            "count": row.settlement_count,
        }

    series = list(buckets.values())
    total_gross = sum(p["gross_revenue"] for p in series)
    total_fees  = sum(p["total_fees"]    for p in series)
    total_net   = sum(p["net_payout"]    for p in series)

    return {
        "granularity":        g,
        "date_from":          date_from.isoformat() if date_from else None,
        "date_to":            date_to.isoformat()   if date_to   else None,
        "platform":           platform,
        "cache_ttl_seconds":  300,
        "series":             series,
        "summary": {
            "total_gross":        total_gross,
            "total_fees":         total_fees,
            "total_net":          total_net,
            "total_settlements":  sum(p["settlement_count"] for p in series),
            "total_orders":       sum(p["orders"] for p in series),
            "avg_fee_rate_pct":   round(abs(total_fees) / total_gross * 100, 2)
                                  if total_gross > 0 else 0.0,
        },
        "anomalies": _detect_anomalies(series, "gross_revenue"),
    }


# ── 3. Fee breakdown ───────────────────────────────────────────────────────────

async def get_fee_breakdown(
    db: AsyncSession,
    company_id: UUID,
    *,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
    platform:  Optional[str] = None,
) -> dict:
    """
    Fee breakdown by fee_type and category for the period.
    Two queries: one on fees table (by type), one on settlements (gross revenue).
    """
    q = (
        select(
            Fee.fee_type,
            func.coalesce(func.sum(Fee.amount), 0).label("total_amount"),
            func.count(Fee.id).label("count"),
        )
        .where(Fee.company_id == company_id)
        .group_by(Fee.fee_type)
    )
    if platform:
        q = q.where(Fee.platform == platform)
    if date_from or date_to:
        q = q.join(Settlement, Fee.settlement_id == Settlement.id)
        if date_from:
            q = q.where(Settlement.period_end >= _dt_from(date_from))
        if date_to:
            q = q.where(Settlement.period_end <= _dt_to(date_to))

    categories: dict[str, float] = {
        "referral_fees": 0.0, "fba_fees": 0.0, "closing_fees": 0.0,
        "shipping_fees": 0.0, "tcs_taxes": 0.0, "service_fees": 0.0,
        "other_fees":    0.0,
    }
    fee_type_agg: dict[str, dict] = {}
    total_fees = 0.0

    for row in (await db.execute(q)).all():
        amt = float(row.total_amount or 0)
        cat = _fee_category(row.fee_type)
        categories[cat] += amt
        total_fees      += amt
        if row.fee_type not in fee_type_agg:
            fee_type_agg[row.fee_type] = {"fee_type": row.fee_type, "total_amount": 0.0, "count": 0}
        fee_type_agg[row.fee_type]["total_amount"] += amt
        fee_type_agg[row.fee_type]["count"]        += row.count

    fee_items = sorted(fee_type_agg.values(), key=lambda x: x["total_amount"])

    rev_q = select(
        func.coalesce(func.sum(Settlement.total_amount), 0).label("gross")
    ).where(Settlement.company_id == company_id)
    if platform:
        rev_q = rev_q.where(Settlement.platform == platform)
    if date_from:
        rev_q = rev_q.where(Settlement.period_end >= _dt_from(date_from))
    if date_to:
        rev_q = rev_q.where(Settlement.period_end <= _dt_to(date_to))

    total_gross = float((await db.execute(rev_q)).scalar_one() or 0)

    return {
        "date_from":         date_from.isoformat() if date_from else None,
        "date_to":           date_to.isoformat()   if date_to   else None,
        "platform":          platform,
        "cache_ttl_seconds": 600,
        "categories":        categories,
        "fee_items":         fee_items,
        "summary": {
            "total_fees":          total_fees,
            "total_gross_revenue": total_gross,
            "fee_rate_pct":        round(abs(total_fees) / total_gross * 100, 2)
                                   if total_gross > 0 else 0.0,
        },
    }


# ── 4. Payout trends ───────────────────────────────────────────────────────────

async def get_payout_trends(
    db: AsyncSession,
    company_id: UUID,
    *,
    date_from:   Optional[date] = None,
    date_to:     Optional[date] = None,
    granularity: str = "month",
    platform:    Optional[str] = None,
) -> dict:
    """Payout time-series bucketed by settlement period_end (transfer date often NULL)."""
    g = _trunc(granularity)
    q = (
        select(
            _date_trunc(g, Settlement.period_end).label("bucket"),
            PayoutEvent.status,
            func.coalesce(func.sum(PayoutEvent.amount), 0).label("total"),
            func.count(PayoutEvent.id).label("cnt"),
        )
        .join(Settlement, PayoutEvent.settlement_id == Settlement.id)
        .where(PayoutEvent.company_id == company_id)
        .group_by(_date_trunc(g, Settlement.period_end), PayoutEvent.status)
        .order_by(_date_trunc(g, Settlement.period_end))
    )
    if platform:
        q = q.where(PayoutEvent.platform == platform)
    if date_from:
        q = q.where(Settlement.period_end >= _dt_from(date_from))
    if date_to:
        q = q.where(Settlement.period_end <= _dt_to(date_to))

    buckets: dict[str, dict] = {}
    for row in (await db.execute(q)).all():
        key = row.bucket.isoformat()
        if key not in buckets:
            buckets[key] = {
                "date":        key,
                "label":       _bucket_label(row.bucket, g),
                "transferred": 0.0,
                "pending":     0.0,
                "failed":      0.0,
                "total":       0.0,
            }
        amt = float(row.total or 0)
        if row.status in buckets[key]:
            buckets[key][row.status] += amt
        buckets[key]["total"] += amt

    series = list(buckets.values())
    return {
        "granularity":        g,
        "platform":           platform,
        "cache_ttl_seconds":  300,
        "series":             series,
        "summary": {
            "total_transferred": sum(p["transferred"] for p in series),
            "total_pending":     sum(p["pending"]     for p in series),
            "total_failed":      sum(p["failed"]      for p in series),
        },
        "anomalies": _detect_anomalies(series, "transferred"),
    }


# ── 5. Refund trends ───────────────────────────────────────────────────────────

async def get_refund_trends(
    db: AsyncSession,
    company_id: UUID,
    *,
    date_from:   Optional[date] = None,
    date_to:     Optional[date] = None,
    granularity: str = "month",
    platform:    Optional[str] = None,
) -> dict:
    """Refund transaction time-series with return rate vs shipment total."""
    g = _trunc(granularity)
    refund_q = (
        select(
            _date_trunc(g, SettlementTransaction.posted_date).label("bucket"),
            func.count(SettlementTransaction.id).label("refund_count"),
            func.coalesce(
                func.sum(func.abs(SettlementTransaction.total_amount)), 0
            ).label("refund_amount"),
            func.coalesce(func.sum(SettlementTransaction.quantity), 0).label("refund_qty"),
        )
        .where(
            SettlementTransaction.company_id == company_id,
            SettlementTransaction.transaction_type == "refund",
            SettlementTransaction.posted_date.isnot(None),
        )
        .group_by(_date_trunc(g, SettlementTransaction.posted_date))
        .order_by(_date_trunc(g, SettlementTransaction.posted_date))
    )
    if platform:
        refund_q = refund_q.where(SettlementTransaction.platform == platform)
    if date_from:
        refund_q = refund_q.where(SettlementTransaction.posted_date >= _dt_from(date_from))
    if date_to:
        refund_q = refund_q.where(SettlementTransaction.posted_date <= _dt_to(date_to))

    buckets: dict[str, dict] = {}
    for row in (await db.execute(refund_q)).all():
        if row.bucket is None:
            continue
        key = row.bucket.isoformat()
        buckets[key] = {
            "date":          key,
            "label":         _bucket_label(row.bucket, g),
            "refund_count":  row.refund_count,
            "refund_amount": float(row.refund_amount or 0),
            "refund_qty":    int(row.refund_qty or 0),
        }

    # Total shipment principal for refund rate calculation
    ship_q = select(
        func.coalesce(func.sum(SettlementTransaction.principal_amount), 0).label("total")
    ).where(
        SettlementTransaction.company_id == company_id,
        SettlementTransaction.transaction_type == "shipment",
    )
    if platform:
        ship_q = ship_q.where(SettlementTransaction.platform == platform)
    if date_from:
        ship_q = ship_q.where(SettlementTransaction.posted_date >= _dt_from(date_from))
    if date_to:
        ship_q = ship_q.where(SettlementTransaction.posted_date <= _dt_to(date_to))

    total_shipment = float((await db.execute(ship_q)).scalar_one() or 0)
    series = list(buckets.values())
    total_refund = sum(p["refund_amount"] for p in series)

    return {
        "granularity":        g,
        "platform":           platform,
        "cache_ttl_seconds":  600,
        "series":             series,
        "summary": {
            "total_refund_count":  sum(p["refund_count"] for p in series),
            "total_refund_amount": total_refund,
            "total_refund_qty":    sum(p["refund_qty"]   for p in series),
            "refund_rate_pct":     round(total_refund / total_shipment * 100, 2)
                                   if total_shipment > 0 else 0.0,
        },
        "anomalies": _detect_anomalies(series, "refund_amount"),
    }


# ── 6. Marketplace breakdown ───────────────────────────────────────────────────

async def get_marketplace_breakdown(
    db: AsyncSession,
    company_id: UUID,
    *,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
) -> dict:
    """
    Per-platform KPIs: GMV, fees, net payout, order count, fee rate, market share,
    AOV, and return rate. Two queries: settlements GROUP BY platform, then
    refund transactions GROUP BY platform.
    """
    settle_q = (
        select(
            Settlement.platform,
            func.count(Settlement.id).label("settlement_count"),
            func.coalesce(func.sum(Settlement.total_amount), 0).label("gross"),
            func.coalesce(func.sum(Settlement.fees_total), 0).label("fees"),
            func.coalesce(func.sum(Settlement.fund_transfer_amount), 0).label("net"),
            func.coalesce(func.sum(Settlement.transactions_count), 0).label("orders"),
        )
        .where(Settlement.company_id == company_id)
        .group_by(Settlement.platform)
    )
    if date_from:
        settle_q = settle_q.where(Settlement.period_end >= _dt_from(date_from))
    if date_to:
        settle_q = settle_q.where(Settlement.period_end <= _dt_to(date_to))

    settle_rows = (await db.execute(settle_q)).all()
    total_gross = sum(float(r.gross or 0) for r in settle_rows)

    platforms: list[dict] = []
    for row in settle_rows:
        gross  = float(row.gross or 0)
        fees   = float(row.fees or 0)
        net    = float(row.net or 0)
        orders = int(row.orders or 0)
        platforms.append({
            "platform":         row.platform,
            "label":            _PLATFORM_LABELS.get(row.platform, row.platform.title()),
            "settlement_count": row.settlement_count,
            "gross_revenue":    gross,
            "total_fees":       fees,
            "net_payout":       net,
            "orders":           orders,
            "fee_rate_pct":     round(abs(fees) / gross * 100, 2) if gross > 0 else 0.0,
            "share_pct":        round(gross / total_gross * 100, 1) if total_gross > 0 else 0.0,
            "avg_order_value":  round(gross / orders, 2) if orders > 0 else 0.0,
            # Refund fields populated below
            "refund_count":     0,
            "refund_amount":    0.0,
            "refund_rate_pct":  0.0,
        })

    # Refund rates per platform
    refund_q = (
        select(
            SettlementTransaction.platform,
            func.count(SettlementTransaction.id).label("refund_count"),
            func.coalesce(
                func.sum(func.abs(SettlementTransaction.total_amount)), 0
            ).label("refund_amount"),
        )
        .where(
            SettlementTransaction.company_id == company_id,
            SettlementTransaction.transaction_type == "refund",
        )
        .group_by(SettlementTransaction.platform)
    )
    refund_by_plat = {
        row.platform: {"count": row.refund_count, "amount": float(row.refund_amount or 0)}
        for row in (await db.execute(refund_q)).all()
    }

    for p in platforms:
        ref = refund_by_plat.get(p["platform"], {"count": 0, "amount": 0.0})
        p["refund_count"]    = ref["count"]
        p["refund_amount"]   = ref["amount"]
        p["refund_rate_pct"] = (
            round(ref["count"] / p["orders"] * 100, 1) if p["orders"] > 0 else 0.0
        )

    platforms.sort(key=lambda x: -x["gross_revenue"])

    return {
        "date_from":         date_from.isoformat() if date_from else None,
        "date_to":           date_to.isoformat()   if date_to   else None,
        "cache_ttl_seconds": 600,
        "platforms":         platforms,
        "summary": {
            "total_gross":   total_gross,
            "total_fees":    sum(p["total_fees"]  for p in platforms),
            "total_net":     sum(p["net_payout"]  for p in platforms),
            "total_orders":  sum(p["orders"]      for p in platforms),
            "platform_count": len(platforms),
        },
    }


# ── 7. Reconciliation health ───────────────────────────────────────────────────

async def get_reconciliation_health(
    db: AsyncSession,
    company_id: UUID,
    *,
    platform: Optional[str] = None,
    days:     int = 90,
) -> dict:
    """
    Reconciliation health KPIs: health score, runs by status, unresolved
    discrepancy breakdown by type and severity.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    run_q = (
        select(
            ReconciliationResult.status,
            func.count(ReconciliationResult.id).label("cnt"),
            func.coalesce(func.sum(ReconciliationResult.total_variance_amount), 0).label("variance"),
            func.coalesce(func.sum(ReconciliationResult.total_discrepancies), 0).label("disc"),
        )
        .where(
            ReconciliationResult.company_id == company_id,
            ReconciliationResult.created_at >= cutoff,
        )
        .group_by(ReconciliationResult.status)
    )
    if platform:
        run_q = run_q.where(ReconciliationResult.platform == platform)

    by_status: dict[str, int] = {"clean": 0, "warning": 0, "critical": 0, "error": 0}
    total_variance     = 0.0
    total_discrepancies = 0
    for row in (await db.execute(run_q)).all():
        if row.status in by_status:
            by_status[row.status] = row.cnt
        total_variance      += float(row.variance or 0)
        total_discrepancies += int(row.disc or 0)

    disc_q = (
        select(
            DiscrepancyEvent.discrepancy_type,
            DiscrepancyEvent.severity,
            func.count(DiscrepancyEvent.id).label("cnt"),
            func.coalesce(func.sum(func.abs(DiscrepancyEvent.variance_amount)), 0).label("variance"),
        )
        .where(
            DiscrepancyEvent.company_id == company_id,
            DiscrepancyEvent.is_resolved == False,  # noqa: E712
        )
        .group_by(DiscrepancyEvent.discrepancy_type, DiscrepancyEvent.severity)
    )
    if platform:
        disc_q = disc_q.where(DiscrepancyEvent.platform == platform)

    discrepancy_breakdown = sorted(
        [
            {
                "type":           row.discrepancy_type,
                "severity":       row.severity,
                "count":          row.cnt,
                "total_variance": float(row.variance or 0),
            }
            for row in (await db.execute(disc_q)).all()
        ],
        key=lambda x: -x["total_variance"],
    )

    unresolv_row = (await db.execute(
        select(
            func.count(DiscrepancyEvent.id),
            func.coalesce(func.sum(func.abs(DiscrepancyEvent.variance_amount)), 0),
        ).where(
            DiscrepancyEvent.company_id == company_id,
            DiscrepancyEvent.is_resolved == False,  # noqa: E712
        )
    )).one()

    total_runs   = sum(by_status.values())
    health_score = round(by_status["clean"] / total_runs * 100, 1) if total_runs > 0 else 100.0

    return {
        "platform":              platform,
        "days":                  days,
        "cache_ttl_seconds":     300,
        "health_score_pct":      health_score,
        "by_status":             by_status,
        "total_runs":            total_runs,
        "total_variance":        total_variance,
        "total_discrepancies":   total_discrepancies,
        "unresolved_count":      int(unresolv_row[0] or 0),
        "unresolved_variance":   float(unresolv_row[1] or 0),
        "discrepancy_breakdown": discrepancy_breakdown,
    }


# ── 8. Profitability metrics ───────────────────────────────────────────────────

async def get_profitability_metrics(
    db: AsyncSession,
    company_id: UUID,
    *,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
    platform:  Optional[str] = None,
    limit:     int = 25,
) -> dict:
    """
    SKU-level profitability derived from settlement_transactions + fees.
    No COGS data — reports gross margin proxy (revenue minus platform fees).
    """
    q = (
        select(
            SettlementTransaction.sku,
            func.count(SettlementTransaction.id).label("order_count"),
            func.coalesce(func.sum(SettlementTransaction.principal_amount), 0).label("gross"),
            func.coalesce(func.sum(SettlementTransaction.fees_total), 0).label("fees"),
            func.coalesce(func.sum(SettlementTransaction.net_amount), 0).label("net"),
            func.coalesce(func.sum(SettlementTransaction.quantity), 0).label("qty"),
        )
        .where(
            SettlementTransaction.company_id == company_id,
            SettlementTransaction.transaction_type == "shipment",
            SettlementTransaction.sku.isnot(None),
        )
        .group_by(SettlementTransaction.sku)
    )
    if platform:
        q = q.where(SettlementTransaction.platform == platform)
    if date_from:
        q = q.where(SettlementTransaction.posted_date >= _dt_from(date_from))
    if date_to:
        q = q.where(SettlementTransaction.posted_date <= _dt_to(date_to))

    skus: list[dict] = []
    for row in (await db.execute(q)).all():
        gross  = float(row.gross or 0)
        fees   = float(row.fees  or 0)
        net    = float(row.net   or 0)
        orders = int(row.order_count or 0)
        skus.append({
            "sku":             row.sku,
            "order_count":     orders,
            "gross_revenue":   gross,
            "fees_total":      fees,
            "net_revenue":     net,
            "qty":             int(row.qty or 0),
            "fee_rate_pct":    round(abs(fees) / gross * 100, 2)   if gross > 0  else 0.0,
            "net_margin_pct":  round(net / gross * 100, 2)         if gross > 0  else 0.0,
            "avg_order_value": round(gross / orders, 2)            if orders > 0 else 0.0,
        })

    skus.sort(key=lambda x: -x["net_revenue"])
    all_skus   = skus
    top_skus   = skus[:limit]

    total_gross = sum(s["gross_revenue"] for s in all_skus)
    total_fees  = sum(s["fees_total"]    for s in all_skus)
    total_net   = sum(s["net_revenue"]   for s in all_skus)

    return {
        "date_from":         date_from.isoformat() if date_from else None,
        "date_to":           date_to.isoformat()   if date_to   else None,
        "platform":          platform,
        "cache_ttl_seconds": 600,
        "items":             top_skus,
        "summary": {
            "total_skus":          len(all_skus),
            "total_gross_revenue": total_gross,
            "total_fees":          total_fees,
            "total_net_revenue":   total_net,
            "avg_fee_rate_pct":    round(abs(total_fees) / total_gross * 100, 2)
                                   if total_gross > 0 else 0.0,
            "loss_making_skus":    sum(1 for s in all_skus if s["net_revenue"] < 0),
        },
    }


# ── 9. Flipkart P&L–based dashboard summary ────────────────────────────────────

async def get_flipkart_dashboard_summary(
    db: AsyncSession,
    company_id: UUID,
) -> dict | None:
    """
    Build a dashboard-shaped summary from uploaded Flipkart P&L data when the
    legacy settlements / payout_events tables have no data for this company.
    Returns None if no processed Flipkart reports exist.
    """
    from app.db.models.flipkart_report import FlipkartReport, FlipkartSummary, FlipkartReconIssue

    # Check if any processed report exists
    report_count = (await db.execute(
        select(func.count(FlipkartReport.id)).where(
            FlipkartReport.company_id == company_id,
            FlipkartReport.status == "done",
        )
    )).scalar_one()
    if not report_count:
        return None

    # Aggregate across all summaries
    sum_row = (await db.execute(
        select(
            func.coalesce(func.sum(FlipkartSummary.gross_sales),    0).label("gross"),
            func.coalesce(func.sum(FlipkartSummary.total_fees),     0).label("fees"),
            func.coalesce(func.sum(FlipkartSummary.net_earnings),   0).label("net"),
            func.coalesce(func.sum(FlipkartSummary.amount_settled), 0).label("settled"),
            func.coalesce(func.sum(FlipkartSummary.amount_pending), 0).label("pending"),
            func.coalesce(func.sum(FlipkartSummary.total_orders),   0).label("orders"),
        ).where(FlipkartSummary.company_id == company_id)
    )).one()

    total_gross = float(sum_row.gross   or 0)
    total_fees  = float(sum_row.fees    or 0)
    settled     = float(sum_row.settled or 0)
    pending     = float(sum_row.pending or 0)
    orders      = int(sum_row.orders    or 0)

    # Recon issues (money leak)
    iss_row = (await db.execute(
        select(
            func.count(FlipkartReconIssue.id).label("cnt"),
            func.coalesce(func.sum(func.abs(FlipkartReconIssue.variance)), 0).label("variance"),
        ).where(
            FlipkartReconIssue.company_id == company_id,
            FlipkartReconIssue.status == "open",
        )
    )).one()
    unresolved = int(iss_row.cnt      or 0)
    variance   = float(iss_row.variance or 0)

    # Revenue trend by report upload month
    trend_rows = (await db.execute(
        select(
            func.date_trunc(literal_column("'month'"), FlipkartReport.uploaded_at).label("month"),
            func.coalesce(func.sum(FlipkartSummary.gross_sales),  0).label("gross"),
            func.coalesce(func.sum(FlipkartSummary.net_earnings), 0).label("net"),
        )
        .join(FlipkartSummary, FlipkartSummary.report_id == FlipkartReport.id)
        .where(FlipkartReport.company_id == company_id, FlipkartReport.status == "done")
        .group_by(func.date_trunc(literal_column("'month'"), FlipkartReport.uploaded_at))
        .order_by(func.date_trunc(literal_column("'month'"), FlipkartReport.uploaded_at))
    )).all()

    revenue_trend = [
        {
            "date":  row.month.strftime("%Y-%m-%d"),
            "gross": float(row.gross or 0),
            "net":   float(row.net   or 0),
        }
        for row in trend_rows if row.month
    ]

    return {
        "cache_ttl_seconds": 300,
        "source": "flipkart_pl",
        "settlements": {
            "total":            report_count,
            "closed_count":     report_count,
            "open_count":       0,
            "processing_count": 0,
            "total_gross":      total_gross,
            "total_fees":       total_fees,
            "total_net_paid":   settled,
            "pending_amount":   pending,
            "total_orders":     orders,
        },
        "payouts": {
            "transferred": settled,
            "pending":     pending,
            "failed":      0.0,
        },
        "reconciliation": {
            "clean":                  max(0, report_count - (1 if unresolved > 0 else 0)),
            "warning":                1 if unresolved > 0 else 0,
            "critical":               0,
            "error":                  0,
            "total_runs":             report_count,
            "unresolved_discrepancies": unresolved,
            "total_variance":         variance,
        },
        "revenue_trend":  revenue_trend,
        "platform_share": [
            {
                "platform":  "flipkart",
                "label":     "Flipkart",
                "gross":     total_gross,
                "count":     orders,
                "share_pct": 100.0,
            }
        ] if total_gross > 0 else [],
    }


# ── 10. Flipkart P&L–based returns ─────────────────────────────────────────────

async def get_flipkart_returns(
    db: AsyncSession,
    company_id: UUID,
) -> dict | None:
    """
    Build returns-page data from uploaded Flipkart P&L SKU-level data.
    Returns None if no processed Flipkart reports exist.
    """
    from app.db.models.flipkart_report import FlipkartReport, FlipkartSkuPL

    report_count = (await db.execute(
        select(func.count(FlipkartReport.id)).where(
            FlipkartReport.company_id == company_id,
            FlipkartReport.status == "done",
        )
    )).scalar_one()
    if not report_count:
        return None

    # SKUs with return/cancellation data
    sku_rows = (await db.execute(
        select(FlipkartSkuPL).where(
            FlipkartSkuPL.company_id == company_id,
            FlipkartSkuPL.returns_value > 0,
        ).order_by(FlipkartSkuPL.returns_value.desc()).limit(200)
    )).scalars().all()

    cancel_rows = (await db.execute(
        select(FlipkartSkuPL).where(
            FlipkartSkuPL.company_id == company_id,
            FlipkartSkuPL.cancellations_value > 0,
        ).order_by(FlipkartSkuPL.cancellations_value.desc()).limit(100)
    )).scalars().all()

    items = []
    idx = 1
    for r in sku_rows:
        items.append({
            "id":     f"RET-{idx:03d}",
            "plat":   "Flipkart",
            "icon":   "🛍️",
            "oid":    "",
            "sku":    r.sku_code or "",
            "prod":   r.product_title or r.sku_code or "Product",
            "reason": "Product Return",
            "qty":    int(float(r.returns_qty or 0)),
            "base":   float(r.returns_value or 0),
            "ship":   0.0,
            "total":  float(r.returns_value or 0),
            "date":   "",
            "status": "processed",
        })
        idx += 1

    for r in cancel_rows:
        items.append({
            "id":     f"CAN-{idx:03d}",
            "plat":   "Flipkart",
            "icon":   "🛍️",
            "oid":    "",
            "sku":    r.sku_code or "",
            "prod":   r.product_title or r.sku_code or "Product",
            "reason": "Cancellation",
            "qty":    int(float(r.cancellations_qty or 0)),
            "base":   float(r.cancellations_value or 0),
            "ship":   0.0,
            "total":  float(r.cancellations_value or 0),
            "date":   "",
            "status": "processed",
        })
        idx += 1

    total_deducted = sum(i["total"] for i in items)
    by_reason = {}
    for i in items:
        by_reason[i["reason"]] = by_reason.get(i["reason"], 0) + 1

    return {
        "items": items,
        "summary": {
            "total_count":    len(items),
            "total_deducted": total_deducted,
            "disputed_count": 0,
            "by_reason":      by_reason,
        },
    }
