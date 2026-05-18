"""
GST/TCS engine API — India-specific tax accounting from settlement data.

All DB-backed endpoints fall back to mock data when DATABASE_URL is not set,
preserving the demo experience.

Prefix: /gst

Endpoints
---------
GET  /gst/                              — overall TCS/ITC summary (mock fallback)
GET  /gst/monthly                       — list monthly tax summaries (paginated)
GET  /gst/monthly/{period}              — single period detail (e.g. "2026-04")
GET  /gst/ledger                        — paginated tax ledger entries
POST /gst/process/{settlement_id}       — extract tax entries from one settlement
POST /gst/process-batch                 — process settlements for a period
GET  /gst/tcs                           — TCS deduction summary (GSTR-2A data)
GET  /gst/report                        — CSV download of monthly summaries
POST /gst/generate-report               — (legacy compat) stub kept for frontend
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, get_db_optional
from app.core.rbac import require_db_permission
from app.data.mock_data import GST

logger = logging.getLogger(__name__)
router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_db_user(user) -> bool:
    return hasattr(user, "companies")


def _company_id(user) -> UUID:
    if not _is_db_user(user) or not user.companies:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No company associated with this account.",
        )
    return user.companies[0].id


def _s(v) -> float:
    """Safe Decimal → float conversion."""
    return float(v or 0)


# ── mock fallback ─────────────────────────────────────────────────────────────

def _mock_summary() -> dict:
    total_tcs = sum(g["tcs"] for g in GST)
    total_itc = sum(g["tds"] for g in GST)   # tds = GST on fees (ITC) in mock
    unreconciled = sum(1 for g in GST if not g["ok"])
    return {
        "items": GST,
        "summary": {
            "total_tcs":     total_tcs,
            "total_itc":     total_itc,
            "total_tds":     total_itc,        # legacy field kept
            "unreconciled":  unreconciled,
            "claimable":     total_tcs + total_itc,
        },
    }


# ── GET /gst/ ─────────────────────────────────────────────────────────────────

@router.get("/")
async def get_gst_overview(
    platform: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Overall GST/TCS summary grouped by platform.

    Returns per-platform taxable sales, TCS deducted, ITC claimable, and
    reconciliation status.  Falls back to demo data when no DB is configured.
    """
    if db is None or not _is_db_user(user):
        return _mock_summary()

    from app.db.models.monthly_tax_summary import MonthlyTaxSummary
    from sqlalchemy import select, func

    company_id = _company_id(user)

    q = select(
        MonthlyTaxSummary.platform,
        func.coalesce(func.sum(MonthlyTaxSummary.gross_sales),   0).label("gross_sales"),
        func.coalesce(func.sum(MonthlyTaxSummary.net_sales),     0).label("net_sales"),
        func.coalesce(func.sum(MonthlyTaxSummary.tcs_deducted),  0).label("tcs_deducted"),
        func.coalesce(func.sum(MonthlyTaxSummary.gst_on_fees),   0).label("itc_claimable"),
        func.coalesce(func.sum(MonthlyTaxSummary.refund_amount), 0).label("refund_amount"),
        func.count(MonthlyTaxSummary.id).label("periods"),
        func.coalesce(func.sum(MonthlyTaxSummary.settlements_processed), 0).label("settlements"),
    ).where(MonthlyTaxSummary.company_id == company_id)

    if platform:
        q = q.where(MonthlyTaxSummary.platform == platform)
    q = q.group_by(MonthlyTaxSummary.platform)

    res = await db.execute(q)
    rows = res.fetchall()

    items = []
    for r in rows:
        tcs = _s(r.tcs_deducted)
        itc = _s(r.itc_claimable)
        items.append({
            "plat":        r.platform,
            "taxable":     _s(r.gross_sales),
            "net_sales":   _s(r.net_sales),
            "tcs":         tcs,
            "itc":         itc,
            "refunds":     _s(r.refund_amount),
            "periods":     r.periods,
            "settlements": int(r.settlements),
            "claimable":   round(tcs + itc, 2),
            "ok":          True,
        })

    total_tcs = sum(i["tcs"] for i in items)
    total_itc = sum(i["itc"] for i in items)
    return {
        "items": items,
        "summary": {
            "total_tcs":    round(total_tcs, 2),
            "total_itc":    round(total_itc, 2),
            "total_tds":    round(total_itc, 2),     # legacy compat
            "unreconciled": 0,
            "claimable":    round(total_tcs + total_itc, 2),
        },
    }


# ── GET /gst/monthly ─────────────────────────────────────────────────────────

@router.get("/monthly")
async def list_monthly_summaries(
    platform:  str = Query("amazon"),
    year:      Optional[int] = Query(None, description="Filter by year (e.g. 2026)"),
    limit:     int = Query(12, ge=1, le=60),
    offset:    int = Query(0, ge=0),
    user=Depends(require_db_permission("reports:read")),
    db: AsyncSession = Depends(get_db),
):
    """List monthly GST/TCS summaries, newest first."""
    from app.db.models.monthly_tax_summary import MonthlyTaxSummary

    if db is None:
        raise HTTPException(status_code=503, detail="Database required for tax data.")

    company_id = _company_id(user)

    q = select(MonthlyTaxSummary).where(
        MonthlyTaxSummary.company_id == company_id,
        MonthlyTaxSummary.platform   == platform,
    )
    if year:
        q = q.where(MonthlyTaxSummary.period.like(f"{year}-%"))

    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar_one()

    rows_res = await db.execute(
        q.order_by(MonthlyTaxSummary.period.desc()).offset(offset).limit(limit)
    )
    summaries = rows_res.scalars().all()

    return {
        "total":    total,
        "platform": platform,
        "items":    [_summary_out(s) for s in summaries],
    }


# ── GET /gst/monthly/{period} ────────────────────────────────────────────────

@router.get("/monthly/{period}")
async def get_monthly_summary(
    period:   str,
    platform: str = Query("amazon"),
    user=Depends(require_db_permission("reports:read")),
    db: AsyncSession = Depends(get_db),
):
    """Return detailed summary for a specific period (format: YYYY-MM)."""
    from app.db.models.monthly_tax_summary import MonthlyTaxSummary

    if db is None:
        raise HTTPException(status_code=503, detail="Database required for tax data.")

    company_id = _company_id(user)

    res = await db.execute(
        select(MonthlyTaxSummary).where(
            MonthlyTaxSummary.company_id == company_id,
            MonthlyTaxSummary.platform   == platform,
            MonthlyTaxSummary.period     == period,
        )
    )
    summary = res.scalar_one_or_none()
    if not summary:
        raise HTTPException(status_code=404, detail=f"No tax summary for period '{period}'.")

    return _summary_out(summary)


# ── GET /gst/ledger ──────────────────────────────────────────────────────────

@router.get("/ledger")
async def list_ledger_entries(
    platform:   str           = Query("amazon"),
    period:     Optional[str] = Query(None, description="Filter by period (YYYY-MM)"),
    entry_type: Optional[str] = Query(None),
    settlement_id: Optional[UUID] = Query(None),
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(require_db_permission("reports:read")),
    db: AsyncSession = Depends(get_db),
):
    """Paginated tax ledger entries for audit and reconciliation."""
    from app.db.models.tax_ledger_entry import TaxLedgerEntry

    if db is None:
        raise HTTPException(status_code=503, detail="Database required for tax data.")

    company_id = _company_id(user)

    q = select(TaxLedgerEntry).where(
        TaxLedgerEntry.company_id == company_id,
        TaxLedgerEntry.platform   == platform,
    )
    if period:
        q = q.where(TaxLedgerEntry.period == period)
    if entry_type:
        q = q.where(TaxLedgerEntry.entry_type == entry_type)
    if settlement_id:
        q = q.where(TaxLedgerEntry.settlement_id == settlement_id)

    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar_one()

    rows_res = await db.execute(
        q.order_by(TaxLedgerEntry.created_at.desc()).offset(offset).limit(limit)
    )
    entries = rows_res.scalars().all()

    # Aggregates for the current filter
    agg_res = await db.execute(
        select(
            TaxLedgerEntry.entry_type,
            func.coalesce(func.sum(TaxLedgerEntry.tax_amount), 0).label("tax"),
            func.count(TaxLedgerEntry.id).label("cnt"),
        )
        .where(
            TaxLedgerEntry.company_id == company_id,
            TaxLedgerEntry.platform   == platform,
            *(
                [TaxLedgerEntry.period == period] if period else []
            ),
        )
        .group_by(TaxLedgerEntry.entry_type)
    )
    by_type = {r.entry_type: {"tax": _s(r.tax), "count": r.cnt} for r in agg_res}

    return {
        "total":   total,
        "by_type": by_type,
        "items":   [_ledger_out(e) for e in entries],
    }


# ── POST /gst/process/{settlement_id} ────────────────────────────────────────

@router.post("/process/{settlement_id}")
async def process_settlement(
    settlement_id: UUID,
    platform:    str = Query("amazon"),
    supply_type: str = Query("inter_state", description="inter_state (IGST) or intra_state (CGST+SGST)"),
    rebuild_summary: bool = Query(True, description="Rebuild the monthly summary after processing"),
    user=Depends(require_db_permission("reconciliation:run")),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract GST/TCS ledger entries from a single settlement.

    Re-running wipes and replaces existing entries — idempotent.
    """
    from app.services.tax import engine as tax_engine
    from app.services.tax import summary as tax_summary

    if db is None:
        raise HTTPException(status_code=503, detail="Database required.")

    company_id = _company_id(user)

    result = await tax_engine.process_settlement(
        db, settlement_id, company_id, supply_type=supply_type
    )

    if result.error_message:
        raise HTTPException(status_code=400, detail=result.error_message)

    summary = None
    if rebuild_summary and result.period != "unknown":
        summary = await tax_summary.build_monthly_summary(
            db, company_id, platform, result.period
        )

    await db.commit()

    return {
        "settlement_id":      str(settlement_id),
        "period":             result.period,
        "platform":           result.platform,
        "entries_created":    result.entries_created,
        "tcs_total":          float(result.tcs_total),
        "gst_on_fees_total":  float(result.gst_on_fees_total),
        "gross_sales":        float(result.gross_sales),
        "refund_amount":      float(result.refund_amount),
        "fees_processed":     result.fees_processed,
        "transactions_processed": result.transactions_processed,
        "summary_rebuilt":    summary is not None,
    }


# ── POST /gst/process-batch ──────────────────────────────────────────────────

@router.post("/process-batch")
async def process_batch(
    platform:    str = Query("amazon"),
    period:      str = Query(..., description="Period to process (YYYY-MM)"),
    supply_type: str = Query("inter_state"),
    user=Depends(require_db_permission("reconciliation:run")),
    db: AsyncSession = Depends(get_db),
):
    """
    Process all settlements for a calendar month and rebuild the monthly summary.

    Idempotent — safe to call multiple times for the same period.
    """
    from app.services.tax import engine as tax_engine
    from app.services.tax import summary as tax_summary

    if db is None:
        raise HTTPException(status_code=503, detail="Database required.")

    company_id = _company_id(user)

    results = await tax_engine.process_all_for_period(
        db, company_id, platform, period, supply_type=supply_type
    )

    # Rebuild the monthly summary for the period
    monthly = None
    if results:
        monthly = await tax_summary.build_monthly_summary(
            db, company_id, platform, period
        )

    await db.commit()

    succeeded = [r for r in results if not r.error_message]
    failed    = [r for r in results if r.error_message]

    return {
        "period":               period,
        "platform":             platform,
        "settlements_found":    len(results),
        "succeeded":            len(succeeded),
        "failed":               len(failed),
        "total_entries":        sum(r.entries_created for r in succeeded),
        "total_tcs":            float(sum(r.tcs_total for r in succeeded)),
        "total_gst_on_fees":    float(sum(r.gst_on_fees_total for r in succeeded)),
        "errors": [
            {"settlement_id": str(r.settlement_id), "error": r.error_message}
            for r in failed
        ],
        "monthly_summary": _summary_out(monthly) if monthly else None,
    }


# ── GET /gst/tcs ─────────────────────────────────────────────────────────────

@router.get("/tcs")
async def get_tcs_summary(
    platform: str = Query("amazon"),
    year:     Optional[int] = Query(None),
    user=Depends(require_db_permission("reports:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    TCS deduction summary for GSTR-2A reconciliation.

    Groups TCS by period so the seller can compare against Form 26AS data
    downloaded from the Income Tax portal.
    """
    from app.db.models.monthly_tax_summary import MonthlyTaxSummary

    if db is None:
        raise HTTPException(status_code=503, detail="Database required.")

    company_id = _company_id(user)

    q = select(
        MonthlyTaxSummary.period,
        MonthlyTaxSummary.tcs_deducted,
        MonthlyTaxSummary.tcs_igst,
        MonthlyTaxSummary.tcs_cgst,
        MonthlyTaxSummary.tcs_sgst,
        MonthlyTaxSummary.net_sales,
        MonthlyTaxSummary.is_finalized,
        MonthlyTaxSummary.settlements_processed,
    ).where(
        MonthlyTaxSummary.company_id == company_id,
        MonthlyTaxSummary.platform   == platform,
    )
    if year:
        q = q.where(MonthlyTaxSummary.period.like(f"{year}-%"))

    res = await db.execute(q.order_by(MonthlyTaxSummary.period.desc()))
    rows = res.fetchall()

    items = [
        {
            "period":               r.period,
            "tcs_deducted":         _s(r.tcs_deducted),
            "tcs_igst":             _s(r.tcs_igst),
            "tcs_cgst":             _s(r.tcs_cgst),
            "tcs_sgst":             _s(r.tcs_sgst),
            "net_sales":            _s(r.net_sales),
            "is_finalized":         r.is_finalized,
            "settlements_processed": r.settlements_processed,
        }
        for r in rows
    ]

    total_tcs = sum(i["tcs_deducted"] for i in items)
    return {
        "platform":    platform,
        "year":        year,
        "total_tcs":   round(total_tcs, 2),
        "total_igst":  round(sum(i["tcs_igst"] for i in items), 2),
        "total_cgst":  round(sum(i["tcs_cgst"] for i in items), 2),
        "total_sgst":  round(sum(i["tcs_sgst"] for i in items), 2),
        "periods":     len(items),
        "items":       items,
    }


# ── GET /gst/report ──────────────────────────────────────────────────────────

@router.get("/report")
async def download_report(
    platform: str = Query("amazon"),
    year:     Optional[int] = Query(None),
    fmt:      str = Query("csv", description="Output format: csv | json"),
    user=Depends(require_db_permission("reports:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Download monthly GST/TCS summary as CSV or JSON.

    The CSV is structured for direct import into a CA's Excel template or
    any GSTR-9 preparation software.
    """
    from app.db.models.monthly_tax_summary import MonthlyTaxSummary
    from app.services.tax.summary import generate_summary_csv

    if db is None:
        raise HTTPException(status_code=503, detail="Database required.")

    company_id = _company_id(user)

    q = select(MonthlyTaxSummary).where(
        MonthlyTaxSummary.company_id == company_id,
        MonthlyTaxSummary.platform   == platform,
    )
    if year:
        q = q.where(MonthlyTaxSummary.period.like(f"{year}-%"))

    res = await db.execute(q.order_by(MonthlyTaxSummary.period.asc()))
    summaries = res.scalars().all()

    if fmt == "json":
        return {"platform": platform, "items": [_summary_out(s) for s in summaries]}

    csv_content = generate_summary_csv(summaries)
    filename = f"gst_summary_{platform}_{year or 'all'}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── POST /gst/generate-report (legacy compat) ────────────────────────────────

@router.post("/generate-report")
def generate_report(user=Depends(get_current_user)):
    """Legacy stub — use GET /gst/report for actual CSV download."""
    return {
        "message": "Use GET /gst/report?platform=amazon for CSV download.",
        "status": "ok",
    }


# ── Serialisers ───────────────────────────────────────────────────────────────

def _summary_out(s) -> dict:
    return {
        "id":                    str(s.id),
        "period":                s.period,
        "platform":              s.platform,
        "gross_sales":           _s(s.gross_sales),
        "refund_amount":         _s(s.refund_amount),
        "net_sales":             _s(s.net_sales),
        "tcs_deducted":          _s(s.tcs_deducted),
        "tcs_igst":              _s(s.tcs_igst),
        "tcs_cgst":              _s(s.tcs_cgst),
        "tcs_sgst":              _s(s.tcs_sgst),
        "total_fees":            _s(s.total_fees),
        "gst_on_fees":           _s(s.gst_on_fees),
        "igst_on_fees":          _s(s.igst_on_fees),
        "cgst_on_fees":          _s(s.cgst_on_fees),
        "sgst_on_fees":          _s(s.sgst_on_fees),
        "gst_on_refunds":        _s(s.gst_on_refunds),
        "settlements_processed": s.settlements_processed or 0,
        "transactions_count":    s.transactions_count or 0,
        "fees_count":            s.fees_count or 0,
        "net_tcs_credit":        _s(s.net_tcs_credit),
        "itc_claimable":         _s(s.itc_claimable),
        "is_finalized":          s.is_finalized,
        "finalized_at":          s.finalized_at.isoformat() if s.finalized_at else None,
        "created_at":            s.created_at.isoformat() if s.created_at else None,
        "updated_at":            s.updated_at.isoformat() if hasattr(s, "updated_at") and s.updated_at else None,
    }


def _ledger_out(e) -> dict:
    return {
        "id":             str(e.id),
        "period":         e.period,
        "entry_type":     e.entry_type,
        "fee_type":       e.fee_type,
        "order_id":       e.order_id,
        "transaction_id": str(e.transaction_id) if e.transaction_id else None,
        "fee_id":         str(e.fee_id) if e.fee_id else None,
        "taxable_amount": _s(e.taxable_amount),
        "tax_rate_pct":   _s(e.tax_rate_pct),
        "tax_amount":     _s(e.tax_amount),
        "igst_amount":    _s(e.igst_amount),
        "cgst_amount":    _s(e.cgst_amount),
        "sgst_amount":    _s(e.sgst_amount),
        "supply_type":    e.supply_type,
        "is_reversal":    e.is_reversal,
        "created_at":     e.created_at.isoformat() if e.created_at else None,
    }
