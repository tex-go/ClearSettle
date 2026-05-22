"""
Flipkart P&L Report API.

Prefix: /flipkart

Endpoints:
  POST   /flipkart/upload                    — upload + parse Excel (multipart)
  GET    /flipkart/reports                   — list reports for company
  GET    /flipkart/reports/{id}              — report metadata
  DELETE /flipkart/reports/{id}             — delete report + all data
  GET    /flipkart/reports/{id}/summary      — dashboard KPI cards
  GET    /flipkart/reports/{id}/skus         — SKU P&L table (paginated, sortable)
  GET    /flipkart/reports/{id}/orders       — order table (paginated, filterable)
  GET    /flipkart/reports/{id}/reconciliation — recon issues
  GET    /flipkart/reports/{id}/insights     — automated insights
  GET    /flipkart/reports/{id}/charts       — chart data (fee breakdown, waterfall, SKU, category)
  PATCH  /flipkart/recon-issues/{issue_id}   — update issue status
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    HTTPException, Query, UploadFile, status,
)
from pydantic import BaseModel
from sqlalchemy import func, select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.db.database import AsyncSessionLocal
from app.db.models.flipkart_report import (
    FlipkartReport, FlipkartSummary, FlipkartSkuPL,
    FlipkartOrderPL, FlipkartReconIssue,
)
from app.services.flipkart.parser import parse_flipkart_excel
from app.services.flipkart.analyzer import (
    enrich_summary, compute_sku_analytics,
    build_fee_breakdown, build_revenue_waterfall,
    build_sku_chart_data, build_category_breakdown,
    build_return_analysis,
)
from app.services.flipkart.reconciliation import run_reconciliation, compute_recon_summary
from app.services.flipkart.insights import generate_insights

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "/tmp/flipkart_uploads"


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _company_id(user) -> UUID:
    if hasattr(user, "companies") and user.companies:
        return user.companies[0].id
    raise HTTPException(status_code=422, detail="No company associated with this account.")


def _assert_report_owner(report: FlipkartReport, company_id: UUID) -> None:
    if report.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")


# ── Decimal serialisation helpers ─────────────────────────────────────────────

def _f(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _summary_to_dict(s: FlipkartSummary) -> Dict[str, Any]:
    return {
        "gross_sales":            _f(s.gross_sales),
        "returns":                _f(s.returns),
        "cancellations":          _f(s.cancellations),
        "net_sales":              _f(s.net_sales),
        "commission":             _f(s.commission),
        "shipping_charges":       _f(s.shipping_charges),
        "reverse_shipping":       _f(s.reverse_shipping),
        "collection_fees":        _f(s.collection_fees),
        "fixed_fees":             _f(s.fixed_fees),
        "gst_on_fees":            _f(s.gst_on_fees),
        "tcs":                    _f(s.tcs),
        "tds":                    _f(s.tds),
        "other_fees":             _f(s.other_fees),
        "total_fees":             _f(s.total_fees),
        "net_earnings":           _f(s.net_earnings),
        "amount_settled":         _f(s.amount_settled),
        "amount_pending":         _f(s.amount_pending),
        "total_orders":           s.total_orders,
        "total_returned_orders":  s.total_returned_orders,
        "total_cancelled_orders": s.total_cancelled_orders,
        "return_rate_pct":        _f(s.return_rate_pct),
        "cancellation_rate_pct":  _f(s.cancellation_rate_pct),
        "profit_margin_pct":      _f(s.profit_margin_pct),
    }


def _sku_to_dict(r: FlipkartSkuPL) -> Dict[str, Any]:
    return {
        "id":                     str(r.id),
        "sku_code":               r.sku_code,
        "product_title":          r.product_title,
        "category":               r.category,
        "selling_price":          _f(r.selling_price),
        "mrp":                    _f(r.mrp),
        "total_orders":           r.total_orders,
        "qty_sold":               _f(r.qty_sold),
        "gross_sales":            _f(r.gross_sales),
        "returns_qty":            _f(r.returns_qty),
        "returns_value":          _f(r.returns_value),
        "cancellations_qty":      _f(r.cancellations_qty),
        "cancellations_value":    _f(r.cancellations_value),
        "net_sales":              _f(r.net_sales),
        "commission":             _f(r.commission),
        "shipping_charges":       _f(r.shipping_charges),
        "reverse_shipping":       _f(r.reverse_shipping),
        "other_fees":             _f(r.other_fees),
        "total_fees":             _f(r.total_fees),
        "net_earnings":           _f(r.net_earnings),
        "margin_pct":             _f(r.margin_pct),
        "return_rate_pct":        _f(r.return_rate_pct),
        "cancellation_rate_pct":  _f(r.cancellation_rate_pct),
        "is_loss_making":         r.is_loss_making,
        "high_return_rate":       r.high_return_rate,
    }


def _order_to_dict(r: FlipkartOrderPL) -> Dict[str, Any]:
    return {
        "id":                  str(r.id),
        "order_id":            r.order_id,
        "order_date":          r.order_date.isoformat() if r.order_date else None,
        "sku_code":            r.sku_code,
        "product_title":       r.product_title,
        "category":            r.category,
        "selling_price":       _f(r.selling_price),
        "quantity":            _f(r.quantity),
        "gross_amount":        _f(r.gross_amount),
        "commission":          _f(r.commission),
        "shipping_charges":    _f(r.shipping_charges),
        "reverse_shipping":    _f(r.reverse_shipping),
        "other_fees":          _f(r.other_fees),
        "net_earnings":        _f(r.net_earnings),
        "status":              r.status,
        "settlement_status":   r.settlement_status,
        "settlement_amount":   _f(r.settlement_amount),
        "settlement_date":     r.settlement_date.isoformat() if r.settlement_date else None,
        "expected_settlement": _f(r.expected_settlement),
        "settlement_variance": _f(r.settlement_variance),
    }


def _issue_to_dict(r: FlipkartReconIssue) -> Dict[str, Any]:
    return {
        "id":               str(r.id),
        "issue_type":       r.issue_type,
        "severity":         r.severity,
        "order_id":         r.order_id,
        "sku_code":         r.sku_code,
        "expected_amount":  _f(r.expected_amount),
        "actual_amount":    _f(r.actual_amount),
        "variance":         _f(r.variance),
        "description":      r.description,
        "status":           r.status,
        "created_at":       r.created_at.isoformat(),
    }


# ── Background ingestion task ─────────────────────────────────────────────────

async def _ingest_report(report_id: UUID, file_bytes: bytes) -> None:
    """Parse, analyze, reconcile, and store all derived data."""
    if AsyncSessionLocal is None:
        return

    async with AsyncSessionLocal() as db:
        report = await db.get(FlipkartReport, report_id)
        if not report:
            return

        try:
            report.status = "processing"
            await db.commit()

            # ── Parse ─────────────────────────────────────────────────────
            parsed = parse_flipkart_excel(file_bytes)

            if parsed["errors"] and not parsed["sku_rows"] and not parsed["order_rows"] and not parsed["summary"]:
                report.status = "failed"
                report.error_message = "; ".join(parsed["errors"][:3])
                await db.commit()
                return

            # ── Analyze (enrich summary) ──────────────────────────────────
            enriched_summary = enrich_summary(
                parsed["summary"],
                parsed["sku_rows"],
                parsed["order_rows"],
            )
            enriched_skus = compute_sku_analytics(parsed["sku_rows"])

            # ── Reconciliation ────────────────────────────────────────────
            recon_issues_raw = run_reconciliation(parsed["order_rows"])

            # ── Insights ──────────────────────────────────────────────────
            # (stored in the response, not the DB — generated on demand)

            company_id = report.company_id

            # ── Persist summary ───────────────────────────────────────────
            def _dec(v) -> Optional[Decimal]:
                if v is None:
                    return None
                try:
                    return Decimal(str(v))
                except Exception:
                    return None

            summary_orm = FlipkartSummary(
                id             = uuid.uuid4(),
                report_id      = report_id,
                company_id     = company_id,
                gross_sales           = _dec(enriched_summary.get("gross_sales")),
                returns               = _dec(enriched_summary.get("returns")),
                cancellations         = _dec(enriched_summary.get("cancellations")),
                net_sales             = _dec(enriched_summary.get("net_sales")),
                commission            = _dec(enriched_summary.get("commission")),
                shipping_charges      = _dec(enriched_summary.get("shipping_charges")),
                reverse_shipping      = _dec(enriched_summary.get("reverse_shipping")),
                collection_fees       = _dec(enriched_summary.get("collection_fees")),
                fixed_fees            = _dec(enriched_summary.get("fixed_fees")),
                gst_on_fees           = _dec(enriched_summary.get("gst_on_fees")),
                tcs                   = _dec(enriched_summary.get("tcs")),
                tds                   = _dec(enriched_summary.get("tds")),
                other_fees            = _dec(enriched_summary.get("other_fees")),
                total_fees            = _dec(enriched_summary.get("total_fees")),
                net_earnings          = _dec(enriched_summary.get("net_earnings")),
                amount_settled        = _dec(enriched_summary.get("amount_settled")),
                amount_pending        = _dec(enriched_summary.get("amount_pending")),
                total_orders          = enriched_summary.get("total_orders"),
                total_returned_orders = enriched_summary.get("total_returned_orders"),
                total_cancelled_orders= enriched_summary.get("total_cancelled_orders"),
                return_rate_pct       = _dec(enriched_summary.get("return_rate_pct")),
                cancellation_rate_pct = _dec(enriched_summary.get("cancellation_rate_pct")),
                profit_margin_pct     = _dec(enriched_summary.get("profit_margin_pct")),
            )
            db.add(summary_orm)

            # ── Persist SKU rows (bulk) ───────────────────────────────────
            for r in enriched_skus:
                db.add(FlipkartSkuPL(
                    id=uuid.uuid4(), report_id=report_id, company_id=company_id,
                    sku_code=r.get("sku_code"),
                    product_title=r.get("product_title"),
                    category=r.get("category"),
                    selling_price=_dec(r.get("selling_price")),
                    mrp=_dec(r.get("mrp")),
                    total_orders=r.get("total_orders"),
                    qty_sold=_dec(r.get("qty_sold")),
                    gross_sales=_dec(r.get("gross_sales")),
                    returns_qty=_dec(r.get("returns_qty")),
                    returns_value=_dec(r.get("returns_value")),
                    cancellations_qty=_dec(r.get("cancellations_qty")),
                    cancellations_value=_dec(r.get("cancellations_value")),
                    net_sales=_dec(r.get("net_sales")),
                    commission=_dec(r.get("commission")),
                    shipping_charges=_dec(r.get("shipping_charges")),
                    reverse_shipping=_dec(r.get("reverse_shipping")),
                    other_fees=_dec(r.get("other_fees")),
                    total_fees=_dec(r.get("total_fees")),
                    net_earnings=_dec(r.get("net_earnings")),
                    margin_pct=_dec(r.get("margin_pct")),
                    return_rate_pct=_dec(r.get("return_rate_pct")),
                    cancellation_rate_pct=_dec(r.get("cancellation_rate_pct")),
                    is_loss_making=bool(r.get("is_loss_making")),
                    high_return_rate=bool(r.get("high_return_rate")),
                ))

            # ── Persist order rows (bulk) ─────────────────────────────────
            from datetime import date as _date
            for r in parsed["order_rows"]:
                def _pd(s):
                    if not s:
                        return None
                    try:
                        from datetime import datetime as _dt
                        return _dt.strptime(s[:10], "%Y-%m-%d").date()
                    except Exception:
                        return None

                db.add(FlipkartOrderPL(
                    id=uuid.uuid4(), report_id=report_id, company_id=company_id,
                    order_id=r.get("order_id"),
                    order_date=_pd(r.get("order_date")),
                    sku_code=r.get("sku_code"),
                    product_title=r.get("product_title"),
                    category=r.get("category"),
                    selling_price=_dec(r.get("selling_price")),
                    quantity=_dec(r.get("quantity")),
                    gross_amount=_dec(r.get("gross_amount")),
                    commission=_dec(r.get("commission")),
                    shipping_charges=_dec(r.get("shipping_charges")),
                    reverse_shipping=_dec(r.get("reverse_shipping")),
                    other_fees=_dec(r.get("other_fees")),
                    net_earnings=_dec(r.get("net_earnings")),
                    status=r.get("status"),
                    settlement_status=r.get("settlement_status"),
                    settlement_amount=_dec(r.get("settlement_amount")),
                    settlement_date=_pd(r.get("settlement_date")),
                    expected_settlement=_dec(r.get("expected_settlement")),
                    settlement_variance=_dec(r.get("settlement_variance")),
                ))

            # ── Persist recon issues (bulk) ───────────────────────────────
            for iss in recon_issues_raw:
                db.add(FlipkartReconIssue(
                    id=uuid.uuid4(), report_id=report_id, company_id=company_id,
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    order_id=iss.get("order_id"),
                    sku_code=iss.get("sku_code"),
                    expected_amount=_dec(iss.get("expected_amount")),
                    actual_amount=_dec(iss.get("actual_amount")),
                    variance=_dec(iss.get("variance")),
                    description=iss["description"],
                ))

            # ── Update report metadata ────────────────────────────────────
            report.status          = "done"
            report.sheets_parsed   = ", ".join(parsed["sheets_found"])
            report.row_count_summary = len(parsed["summary"])
            report.row_count_sku   = len(parsed["sku_rows"])
            report.row_count_orders= len(parsed["order_rows"])
            report.processed_at    = datetime.utcnow()

            await db.commit()
            logger.info("Flipkart report %s ingested: %d SKUs, %d orders, %d issues",
                        report_id, len(enriched_skus), len(parsed["order_rows"]), len(recon_issues_raw))

        except Exception as exc:
            logger.exception("Ingestion failed for report %s", report_id)
            try:
                report.status = "failed"
                report.error_message = str(exc)[:500]
                await db.commit()
            except Exception:
                pass


# ── Upload endpoint ───────────────────────────────────────────────────────────

@router.post("/upload", status_code=202)
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Upload a Flipkart P&L Excel file. Processing happens asynchronously."""
    company_id = _company_id(user)

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 50 MB.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4()}.xlsx"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as fh:
        fh.write(file_bytes)

    report = FlipkartReport(
        id            = uuid.uuid4(),
        company_id    = company_id,
        filename      = stored_name,
        original_name = file.filename,
        file_size_bytes = len(file_bytes),
        status        = "pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    background_tasks.add_task(_ingest_report, report.id, file_bytes)

    return {
        "id":            str(report.id),
        "original_name": report.original_name,
        "status":        report.status,
        "message":       "Report uploaded. Processing started.",
    }


# ── List reports ──────────────────────────────────────────────────────────────

@router.get("/reports")
async def list_reports(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    result = await db.execute(
        select(FlipkartReport)
        .where(FlipkartReport.company_id == company_id)
        .order_by(desc(FlipkartReport.uploaded_at))
        .limit(50)
    )
    reports = result.scalars().all()

    return {
        "items": [
            {
                "id":               str(r.id),
                "original_name":    r.original_name,
                "status":           r.status,
                "error_message":    r.error_message,
                "report_period":    r.report_period,
                "sheets_parsed":    r.sheets_parsed,
                "row_count_sku":    r.row_count_sku,
                "row_count_orders": r.row_count_orders,
                "file_size_bytes":  r.file_size_bytes,
                "uploaded_at":      r.uploaded_at.isoformat(),
                "processed_at":     r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in reports
        ]
    }


# ── Report detail ─────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}")
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(FlipkartReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_report_owner(report, company_id)

    return {
        "id":               str(report.id),
        "original_name":    report.original_name,
        "status":           report.status,
        "error_message":    report.error_message,
        "report_period":    report.report_period,
        "sheets_parsed":    report.sheets_parsed,
        "row_count_sku":    report.row_count_sku,
        "row_count_orders": report.row_count_orders,
        "file_size_bytes":  report.file_size_bytes,
        "uploaded_at":      report.uploaded_at.isoformat(),
        "processed_at":     report.processed_at.isoformat() if report.processed_at else None,
    }


# ── Delete report ─────────────────────────────────────────────────────────────

@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(FlipkartReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_report_owner(report, company_id)
    await db.delete(report)
    await db.commit()


# ── Summary KPIs ──────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/summary")
async def get_summary(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(FlipkartReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_report_owner(report, company_id)

    if report.status != "done":
        return {"status": report.status, "error_message": report.error_message}

    res = await db.execute(
        select(FlipkartSummary).where(FlipkartSummary.report_id == report_id)
    )
    summary = res.scalar_one_or_none()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not yet available.")

    return {
        "report_id": str(report_id),
        "status":    "done",
        **_summary_to_dict(summary),
    }


# ── SKU P&L table ─────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/skus")
async def get_skus(
    report_id: UUID,
    sort_by:   str = Query("net_earnings", description="Sort field"),
    sort_dir:  str = Query("desc", description="asc | desc"),
    filter_loss: bool = Query(False, description="Show only loss-making SKUs"),
    filter_high_return: bool = Query(False, description="Show only high-return-rate SKUs"),
    category: Optional[str] = Query(None),
    page:  int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(FlipkartReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_report_owner(report, company_id)

    # Build query
    q = select(FlipkartSkuPL).where(FlipkartSkuPL.report_id == report_id)
    if filter_loss:
        q = q.where(FlipkartSkuPL.is_loss_making.is_(True))
    if filter_high_return:
        q = q.where(FlipkartSkuPL.high_return_rate.is_(True))
    if category:
        q = q.where(FlipkartSkuPL.category == category)

    # Sort
    sortable = {
        "net_earnings": FlipkartSkuPL.net_earnings,
        "gross_sales":  FlipkartSkuPL.gross_sales,
        "margin_pct":   FlipkartSkuPL.margin_pct,
        "return_rate_pct": FlipkartSkuPL.return_rate_pct,
        "total_orders": FlipkartSkuPL.total_orders,
        "sku_code":     FlipkartSkuPL.sku_code,
    }
    sort_col = sortable.get(sort_by, FlipkartSkuPL.net_earnings)
    q = q.order_by(desc(sort_col) if sort_dir == "desc" else asc(sort_col))

    # Count
    count_res = await db.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = count_res.scalar_one()

    # Paginate
    q = q.offset((page - 1) * limit).limit(limit)
    res = await db.execute(q)
    rows = res.scalars().all()

    return {
        "total":    total,
        "page":     page,
        "limit":    limit,
        "pages":    (total + limit - 1) // limit,
        "items":    [_sku_to_dict(r) for r in rows],
    }


# ── Orders table ──────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/orders")
async def get_orders(
    report_id:  UUID,
    status:     Optional[str] = Query(None),
    sett_status: Optional[str] = Query(None, alias="settlement_status"),
    sku_code:   Optional[str] = Query(None),
    page:  int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(FlipkartReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_report_owner(report, company_id)

    q = select(FlipkartOrderPL).where(FlipkartOrderPL.report_id == report_id)
    if status:
        q = q.where(FlipkartOrderPL.status == status)
    if sett_status:
        q = q.where(FlipkartOrderPL.settlement_status == sett_status)
    if sku_code:
        q = q.where(FlipkartOrderPL.sku_code == sku_code)

    q = q.order_by(desc(FlipkartOrderPL.order_date))

    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar_one()

    q = q.offset((page - 1) * limit).limit(limit)
    res = await db.execute(q)
    rows = res.scalars().all()

    return {
        "total":  total,
        "page":   page,
        "limit":  limit,
        "pages":  (total + limit - 1) // limit,
        "items":  [_order_to_dict(r) for r in rows],
    }


# ── Reconciliation issues ─────────────────────────────────────────────────────

@router.get("/reports/{report_id}/reconciliation")
async def get_reconciliation(
    report_id:   UUID,
    issue_type:  Optional[str] = Query(None),
    severity:    Optional[str] = Query(None),
    iss_status:  Optional[str] = Query(None, alias="status"),
    page:  int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(FlipkartReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_report_owner(report, company_id)

    q = select(FlipkartReconIssue).where(FlipkartReconIssue.report_id == report_id)
    if issue_type:
        q = q.where(FlipkartReconIssue.issue_type == issue_type)
    if severity:
        q = q.where(FlipkartReconIssue.severity == severity)
    if iss_status:
        q = q.where(FlipkartReconIssue.status == iss_status)

    q = q.order_by(FlipkartReconIssue.severity, desc(FlipkartReconIssue.variance))

    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar_one()

    q = q.offset((page - 1) * limit).limit(limit)
    res = await db.execute(q)
    issues = res.scalars().all()

    # Build summary
    all_issues_res = await db.execute(
        select(FlipkartReconIssue).where(FlipkartReconIssue.report_id == report_id)
    )
    all_issues = all_issues_res.scalars().all()

    orders_res = await db.execute(
        select(FlipkartOrderPL).where(FlipkartOrderPL.report_id == report_id)
    )
    all_orders = orders_res.scalars().all()

    type_counts: Dict[str, int] = {}
    type_amounts: Dict[str, float] = {}
    for iss in all_issues:
        t = iss.issue_type
        type_counts[t]  = type_counts.get(t, 0) + 1
        v = float(iss.variance or iss.expected_amount or 0)
        type_amounts[t] = type_amounts.get(t, 0.0) + abs(v)

    return {
        "total":           total,
        "page":            page,
        "limit":           limit,
        "items":           [_issue_to_dict(r) for r in issues],
        "summary": {
            "total_issues":          len(all_issues),
            "critical_issues":       sum(1 for i in all_issues if i.severity == "critical"),
            "warning_issues":        sum(1 for i in all_issues if i.severity == "warning"),
            "open_issues":           sum(1 for i in all_issues if i.status == "open"),
            "total_variance_amount": round(sum(abs(float(i.variance or 0)) for i in all_issues), 2),
            "issues_by_type": [
                {"type": t, "count": type_counts[t], "amount": round(type_amounts[t], 2)}
                for t in sorted(type_counts, key=lambda k: type_amounts[k], reverse=True)
            ],
        },
    }


# ── Insights ──────────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/insights")
async def get_insights(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(FlipkartReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_report_owner(report, company_id)

    if report.status != "done":
        return {"insights": [], "status": report.status}

    # Load summary
    sum_res = await db.execute(
        select(FlipkartSummary).where(FlipkartSummary.report_id == report_id)
    )
    summary_orm = sum_res.scalar_one_or_none()
    summary_dict = _summary_to_dict(summary_orm) if summary_orm else {}

    # Load SKU rows
    sku_res = await db.execute(
        select(FlipkartSkuPL).where(FlipkartSkuPL.report_id == report_id)
    )
    sku_rows = [_sku_to_dict(r) for r in sku_res.scalars().all()]

    # Load recon issues
    iss_res = await db.execute(
        select(FlipkartReconIssue).where(FlipkartReconIssue.report_id == report_id)
    )
    recon_issues = [_issue_to_dict(r) for r in iss_res.scalars().all()]

    insights = generate_insights(summary_dict, sku_rows, recon_issues)
    return {"insights": insights, "count": len(insights)}


# ── Charts ────────────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/charts")
async def get_charts(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(FlipkartReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_report_owner(report, company_id)

    if report.status != "done":
        return {"status": report.status}

    sum_res = await db.execute(
        select(FlipkartSummary).where(FlipkartSummary.report_id == report_id)
    )
    summary_orm = sum_res.scalar_one_or_none()
    summary_dict = _summary_to_dict(summary_orm) if summary_orm else {}

    sku_res = await db.execute(
        select(FlipkartSkuPL).where(FlipkartSkuPL.report_id == report_id)
    )
    sku_rows = [_sku_to_dict(r) for r in sku_res.scalars().all()]

    return {
        "fee_breakdown":     build_fee_breakdown(summary_dict),
        "revenue_waterfall": build_revenue_waterfall(summary_dict),
        "sku_charts":        build_sku_chart_data(sku_rows, top_n=15),
        "category_breakdown":build_category_breakdown(sku_rows),
        "return_analysis":   build_return_analysis(sku_rows, summary_dict),
    }


# ── Patch recon issue status ──────────────────────────────────────────────────

class IssueStatusUpdate(BaseModel):
    status: str


@router.patch("/recon-issues/{issue_id}")
async def patch_issue_status(
    issue_id: UUID,
    body: IssueStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    issue = await db.get(FlipkartReconIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    if issue.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    allowed = {"open", "resolved", "waived", "disputed"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {allowed}")

    issue.status = body.status
    await db.commit()
    return _issue_to_dict(issue)


# ── Company-level summary stats ───────────────────────────────────────────────

@router.get("/summary")
async def get_company_summary(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Aggregate stats across all reports for the company."""
    company_id = _company_id(user)

    reports_res = await db.execute(
        select(FlipkartReport)
        .where(
            FlipkartReport.company_id == company_id,
            FlipkartReport.status == "done",
        )
    )
    reports = reports_res.scalars().all()

    sums_res = await db.execute(
        select(FlipkartSummary).where(FlipkartSummary.company_id == company_id)
    )
    sums = sums_res.scalars().all()

    total_gross    = sum(float(s.gross_sales or 0) for s in sums)
    total_earnings = sum(float(s.net_earnings or 0) for s in sums)
    total_orders   = sum((s.total_orders or 0) for s in sums)

    issues_res = await db.execute(
        select(func.count())
        .where(
            FlipkartReconIssue.company_id == company_id,
            FlipkartReconIssue.status == "open",
        )
    )
    open_issues = issues_res.scalar_one()

    return {
        "total_reports":     len(reports),
        "total_gross_sales": round(total_gross, 2),
        "total_earnings":    round(total_earnings, 2),
        "total_orders":      total_orders,
        "open_recon_issues": open_issues,
    }
