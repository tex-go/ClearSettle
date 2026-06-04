"""
Meesho Payment Report API.

Prefix: /meesho

Endpoints:
  POST   /meesho/upload                    — upload payment report (multipart)
  POST   /meesho/reports/{id}/confirm      — trigger full ingestion
  GET    /meesho/reports                   — list reports for company
  GET    /meesho/reports/{id}              — report metadata
  DELETE /meesho/reports/{id}              — delete report + all data
  GET    /meesho/reports/{id}/summary      — KPI cards
  GET    /meesho/reports/{id}/orders       — order rows (paginated, filterable)
  GET    /meesho/reports/{id}/reconciliation — recon issues
  GET    /meesho/reports/{id}/insights     — automated insights
  GET    /meesho/reports/{id}/charts       — chart data
  PATCH  /meesho/recon-issues/{issue_id}   — update issue status
  GET    /meesho/docs-status               — which docs have been uploaded
"""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    HTTPException, Query, UploadFile,
)
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.database import AsyncSessionLocal
from app.db.models.meesho_report import (
    MeeshoReport, MeeshoSummary, MeeshoOrderRow, MeeshoReconIssue,
)
from app.services.meesho.parser import parse_meesho_report
from app.services.meesho.analyzer import build_meesho_summary, compute_meesho_order_analytics
from app.services.meesho.reconciliation import run_meesho_reconciliation

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "/tmp/meesho_uploads"

_VALID_DOC_TYPES = {"payment_report", "gst_report"}
_DOC_LABELS = {
    "payment_report": "Payment Report",
    "gst_report":     "GST Report",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _company_id(user) -> UUID:
    if hasattr(user, "companies") and user.companies:
        return user.companies[0].id
    raise HTTPException(status_code=422, detail="No company associated with this account.")


def _assert_owner(report: MeeshoReport, company_id: UUID) -> None:
    if report.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")


def _f(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _summary_dict(s: MeeshoSummary) -> Dict[str, Any]:
    return {
        "gross_sales":              _f(s.gross_sales),
        "customer_paid_total":      _f(s.customer_paid_total),
        "returns_value":            _f(s.returns_value),
        "cancellations_value":      _f(s.cancellations_value),
        "net_sales":                _f(s.net_sales),
        "commission":               _f(s.commission),
        "shipping_charges":         _f(s.shipping_charges),
        "reverse_shipping":         _f(s.reverse_shipping),
        "gst_on_commission":        _f(s.gst_on_commission),
        "tcs":                      _f(s.tcs),
        "other_deductions":         _f(s.other_deductions),
        "total_deductions":         _f(s.total_deductions),
        "net_earnings":             _f(s.net_earnings),
        "amount_paid":              _f(s.amount_paid),
        "amount_pending":           _f(s.amount_pending),
        "total_orders":             s.total_orders,
        "delivered_orders":         s.delivered_orders,
        "returned_orders":          s.returned_orders,
        "cancelled_orders":         s.cancelled_orders,
        "pending_orders":           s.pending_orders,
        "return_rate_pct":          _f(s.return_rate_pct),
        "cancellation_rate_pct":    _f(s.cancellation_rate_pct),
        "effective_commission_pct": _f(s.effective_commission_pct),
    }


def _order_dict(r: MeeshoOrderRow) -> Dict[str, Any]:
    return {
        "id":               str(r.id),
        "order_id":         r.order_id,
        "sub_order_id":     r.sub_order_id,
        "order_date":       r.order_date.isoformat() if r.order_date else None,
        "payment_date":     r.payment_date.isoformat() if r.payment_date else None,
        "product_name":     r.product_name,
        "sku":              r.sku,
        "category":         r.category,
        "quantity":         r.quantity,
        "selling_price":    _f(r.selling_price),
        "mrp":              _f(r.mrp),
        "customer_paid":    _f(r.customer_paid),
        "order_amount":     _f(r.order_amount),
        "commission_rate":  _f(r.commission_rate),
        "commission":       _f(r.commission),
        "shipping_charges": _f(r.shipping_charges),
        "reverse_shipping": _f(r.reverse_shipping),
        "gst_on_commission":_f(r.gst_on_commission),
        "tcs":              _f(r.tcs),
        "other_deductions": _f(r.other_deductions),
        "net_payment":      _f(r.net_payment),
        "expected_net":     _f(r.expected_net),
        "payment_variance": _f(r.payment_variance),
        "order_status":     r.order_status,
        "payment_status":   r.payment_status,
    }


def _issue_dict(r: MeeshoReconIssue) -> Dict[str, Any]:
    return {
        "id":               str(r.id),
        "issue_type":       r.issue_type,
        "severity":         r.severity,
        "order_id":         r.order_id,
        "sku":              r.sku,
        "expected_amount":  _f(r.expected_amount),
        "actual_amount":    _f(r.actual_amount),
        "variance":         _f(r.variance),
        "description":      r.description,
        "status":           r.status,
        "created_at":       r.created_at.isoformat(),
    }


# ── Background ingestion ──────────────────────────────────────────────────────

async def _ingest_report(report_id: UUID, file_bytes: bytes, filename: str) -> None:
    if AsyncSessionLocal is None:
        return

    async with AsyncSessionLocal() as db:
        report = await db.get(MeeshoReport, report_id)
        if not report:
            return

        try:
            report.status = "processing"
            await db.commit()

            parsed   = parse_meesho_report(file_bytes, filename=filename)

            if parsed["errors"] and not parsed["order_rows"]:
                report.status = "failed"
                report.error_message = "; ".join(parsed["errors"][:3])
                await db.commit()
                return

            enriched     = compute_meesho_order_analytics(parsed["order_rows"])
            summary_kpis = build_meesho_summary(enriched)
            issues_raw   = run_meesho_reconciliation(enriched)

            company_id = report.company_id

            def _dec(v) -> Optional[Decimal]:
                if v is None:
                    return None
                try:
                    return Decimal(str(v))
                except Exception:
                    return None

            db.add(MeeshoSummary(
                id=uuid.uuid4(), report_id=report_id, company_id=company_id,
                gross_sales=_dec(summary_kpis.get("gross_sales")),
                customer_paid_total=_dec(summary_kpis.get("customer_paid_total")),
                returns_value=_dec(summary_kpis.get("returns_value")),
                cancellations_value=_dec(summary_kpis.get("cancellations_value")),
                net_sales=_dec(summary_kpis.get("net_sales")),
                commission=_dec(summary_kpis.get("commission")),
                shipping_charges=_dec(summary_kpis.get("shipping_charges")),
                reverse_shipping=_dec(summary_kpis.get("reverse_shipping")),
                gst_on_commission=_dec(summary_kpis.get("gst_on_commission")),
                tcs=_dec(summary_kpis.get("tcs")),
                other_deductions=_dec(summary_kpis.get("other_deductions")),
                total_deductions=_dec(summary_kpis.get("total_deductions")),
                net_earnings=_dec(summary_kpis.get("net_earnings")),
                amount_paid=_dec(summary_kpis.get("amount_paid")),
                amount_pending=_dec(summary_kpis.get("amount_pending")),
                total_orders=summary_kpis.get("total_orders"),
                delivered_orders=summary_kpis.get("delivered_orders"),
                returned_orders=summary_kpis.get("returned_orders"),
                cancelled_orders=summary_kpis.get("cancelled_orders"),
                pending_orders=summary_kpis.get("pending_orders"),
                return_rate_pct=_dec(summary_kpis.get("return_rate_pct")),
                cancellation_rate_pct=_dec(summary_kpis.get("cancellation_rate_pct")),
                effective_commission_pct=_dec(summary_kpis.get("effective_commission_pct")),
            ))

            from datetime import date as _date
            def _pd(v):
                if v is None:
                    return None
                if isinstance(v, _date):
                    return v
                try:
                    from datetime import datetime as _dt
                    return _dt.strptime(str(v)[:10], "%Y-%m-%d").date()
                except Exception:
                    return None

            for r in enriched:
                db.add(MeeshoOrderRow(
                    id=uuid.uuid4(), report_id=report_id, company_id=company_id,
                    order_id=r.get("order_id"),
                    sub_order_id=r.get("sub_order_id"),
                    order_date=_pd(r.get("order_date")),
                    payment_date=_pd(r.get("payment_date")),
                    product_name=r.get("product_name"),
                    sku=r.get("sku"),
                    category=r.get("category"),
                    quantity=r.get("quantity"),
                    mrp=_dec(r.get("mrp")),
                    customer_paid=_dec(r.get("customer_paid")),
                    commission_rate=_dec(r.get("commission_rate")),
                    commission=_dec(r.get("commission")),
                    shipping_charges=_dec(r.get("shipping_charges")),
                    reverse_shipping=_dec(r.get("reverse_shipping")),
                    gst_on_commission=_dec(r.get("gst_on_commission")),
                    tcs=_dec(r.get("tcs")),
                    net_payment=_dec(r.get("net_payment")),
                    expected_net=_dec(r.get("expected_net")),
                    payment_variance=_dec(r.get("payment_variance")),
                    order_status=r.get("order_status"),
                    payment_status=r.get("payment_status"),
                ))

            for iss in issues_raw:
                db.add(MeeshoReconIssue(
                    id=uuid.uuid4(), report_id=report_id, company_id=company_id,
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    order_id=iss.get("order_id"),
                    sku=iss.get("sku"),
                    expected_amount=_dec(iss.get("expected_amount")),
                    actual_amount=_dec(iss.get("actual_amount")),
                    variance=_dec(iss.get("variance")),
                    description=iss["description"],
                ))

            report.status         = "done"
            report.report_period  = parsed.get("report_period")
            report.row_count      = len(enriched)
            report.processed_at   = datetime.utcnow()

            await db.commit()
            logger.info(
                "Meesho report %s ingested: %d orders, %d issues",
                report_id, len(enriched), len(issues_raw),
            )

        except Exception as exc:
            logger.exception("Meesho ingestion failed for report %s", report_id)
            try:
                report.status = "failed"
                report.error_message = str(exc)[:500]
                await db.commit()
            except Exception:
                pass


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=301,
             deprecated=True,
             summary="[DEPRECATED] Use POST /ingestion/upload instead")
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    report_type: str = Form("payment_report"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)

    if report_type not in _VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid report_type. Must be one of: {', '.join(_VALID_DOC_TYPES)}")

    fname_lower = (file.filename or "").lower()
    allowed_exts = (".xlsx", ".xls", ".csv")
    if not any(fname_lower.endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(allowed_exts)}")

    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 50 MB.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    try:
        existing = (await db.execute(
            select(MeeshoReport)
            .where(
                MeeshoReport.company_id == company_id,
                MeeshoReport.file_hash == file_hash,
                MeeshoReport.status != "failed",
            )
            .limit(1)
        )).scalar_one_or_none()
    except Exception:
        existing = None

    if existing:
        return {
            "id": str(existing.id), "original_name": existing.original_name,
            "file_size_bytes": existing.file_size_bytes, "report_type": existing.report_type,
            "status": existing.status, "duplicate": True,
            "message": "This file was already uploaded. Returning existing report.",
        }

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = ".csv" if fname_lower.endswith(".csv") else ".xlsx"
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as fh:
        fh.write(file_bytes)

    # Non-payment uploads: store only
    if report_type != "payment_report":
        try:
            report = MeeshoReport(
                id=uuid.uuid4(), company_id=company_id,
                filename=stored_name, original_name=file.filename,
                file_size_bytes=len(file_bytes), file_hash=file_hash,
                report_type=report_type, status="uploaded",
            )
            db.add(report)
            await db.commit()
            await db.refresh(report)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Database error: {exc}")
        return {
            "id": str(report.id), "original_name": report.original_name,
            "file_size_bytes": len(file_bytes), "report_type": report_type,
            "status": "uploaded", "message": f"{_DOC_LABELS[report_type]} uploaded successfully.",
        }

    # Quick preview parse
    preview: Dict[str, Any] = {}
    try:
        parsed = parse_meesho_report(file_bytes, filename=file.filename or "")
        preview = {
            "estimated_orders":  len(parsed.get("order_rows", [])),
            "report_period":     parsed.get("report_period"),
            "parse_errors":      parsed.get("errors", [])[:3],
        }
    except Exception as exc:
        preview = {"parse_errors": [str(exc)[:200]]}

    try:
        report = MeeshoReport(
            id=uuid.uuid4(), company_id=company_id,
            filename=stored_name, original_name=file.filename,
            file_size_bytes=len(file_bytes), file_hash=file_hash,
            report_type="payment_report", status="awaiting_confirmation",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Database error: {exc}")

    return {
        "id": str(report.id), "original_name": report.original_name,
        "file_size_bytes": len(file_bytes), "report_type": "payment_report",
        "status": "awaiting_confirmation", "preview": preview,
        "message": "Payment report uploaded. Call POST /confirm to begin full analysis.",
    }


# ── Confirm ───────────────────────────────────────────────────────────────────

@router.post("/reports/{report_id}/confirm", status_code=202)
async def confirm_report(
    report_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(MeeshoReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    if report.status not in ("awaiting_confirmation", "failed"):
        return {"id": str(report.id), "status": report.status, "message": "Already processed or processing."}

    stored_path = os.path.join(UPLOAD_DIR, report.filename)
    if not os.path.exists(stored_path):
        raise HTTPException(status_code=404, detail="Uploaded file not found on disk. Please re-upload.")

    with open(stored_path, "rb") as fh:
        file_bytes = fh.read()

    background_tasks.add_task(_ingest_report, report.id, file_bytes, report.original_name or "")
    return {"id": str(report.id), "status": "processing", "message": "Ingestion started."}


# ── List reports ──────────────────────────────────────────────────────────────

@router.get("/reports")
async def list_reports(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    rows = (await db.execute(
        select(MeeshoReport)
        .where(MeeshoReport.company_id == company_id)
        .order_by(desc(MeeshoReport.uploaded_at))
        .limit(50)
    )).scalars().all()

    return {"reports": [
        {
            "id": str(r.id), "original_name": r.original_name,
            "report_type": r.report_type, "status": r.status,
            "report_period": r.report_period, "row_count": r.row_count,
            "file_size_bytes": r.file_size_bytes,
            "uploaded_at": r.uploaded_at.isoformat(),
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            "error_message": r.error_message,
        }
        for r in rows
    ]}


# ── Report detail ─────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}")
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(MeeshoReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)
    return {
        "id": str(report.id), "original_name": report.original_name,
        "report_type": report.report_type, "status": report.status,
        "report_period": report.report_period, "row_count": report.row_count,
        "file_size_bytes": report.file_size_bytes,
        "uploaded_at": report.uploaded_at.isoformat(),
        "processed_at": report.processed_at.isoformat() if report.processed_at else None,
        "error_message": report.error_message,
    }


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(MeeshoReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)
    await db.delete(report)
    await db.commit()


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/summary")
async def get_summary(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(MeeshoReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    summary = (await db.execute(
        select(MeeshoSummary).where(MeeshoSummary.report_id == report_id)
    )).scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not ready yet.")

    return {"report_id": str(report_id), "report_period": report.report_period, **_summary_dict(summary)}


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/orders")
async def get_orders(
    report_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    order_status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(MeeshoReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    q = select(MeeshoOrderRow).where(MeeshoOrderRow.report_id == report_id)
    if order_status:
        q = q.where(MeeshoOrderRow.order_status.ilike(f"%{order_status}%"))
    if payment_status:
        q = q.where(MeeshoOrderRow.payment_status.ilike(f"%{payment_status}%"))
    if search:
        q = q.where(
            MeeshoOrderRow.order_id.ilike(f"%{search}%") |
            MeeshoOrderRow.sku.ilike(f"%{search}%")
        )

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(MeeshoOrderRow.order_date.desc().nullslast())
                              .offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {
        "total": total, "page": page, "page_size": page_size,
        "orders": [_order_dict(r) for r in rows],
    }


# ── Reconciliation ────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/reconciliation")
async def get_reconciliation(
    report_id: UUID,
    severity: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(MeeshoReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    q = select(MeeshoReconIssue).where(MeeshoReconIssue.report_id == report_id)
    if severity:
        q = q.where(MeeshoReconIssue.severity == severity)
    if issue_type:
        q = q.where(MeeshoReconIssue.issue_type == issue_type)

    issues = (await db.execute(q.order_by(MeeshoReconIssue.created_at.desc()))).scalars().all()
    total_variance = sum(abs(float(i.variance or 0)) for i in issues)

    return {
        "total_issues":   len(issues),
        "total_variance": total_variance,
        "issues":         [_issue_dict(i) for i in issues],
    }


# ── Insights ──────────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/insights")
async def get_insights(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(MeeshoReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    summary = (await db.execute(
        select(MeeshoSummary).where(MeeshoSummary.report_id == report_id)
    )).scalar_one_or_none()

    if not summary:
        return {"insights": []}

    insights = []

    if summary.return_rate_pct and float(summary.return_rate_pct) > 20:
        insights.append({
            "type": "error",
            "title": "High Return Rate",
            "description": f"Return rate is {float(summary.return_rate_pct):.1f}%. Investigate product quality and listing accuracy.",
        })
    elif summary.return_rate_pct and float(summary.return_rate_pct) > 10:
        insights.append({
            "type": "warning",
            "title": "Elevated Return Rate",
            "description": f"Return rate is {float(summary.return_rate_pct):.1f}%. Review return reasons.",
        })

    if summary.effective_commission_pct and float(summary.effective_commission_pct) > 15:
        insights.append({
            "type": "warning",
            "title": "High Commission Rate",
            "description": f"Effective commission is {float(summary.effective_commission_pct):.1f}%. Consider product category optimisation.",
        })

    if summary.amount_pending and float(summary.amount_pending) > 0:
        insights.append({
            "type": "info",
            "title": "Pending Payments",
            "description": f"₹{float(summary.amount_pending):,.2f} is pending settlement from Meesho.",
        })

    if summary.total_orders and summary.total_orders > 0:
        insights.append({
            "type": "success",
            "title": "Report Analysed",
            "description": f"{summary.total_orders} orders processed. Net earnings ₹{float(summary.net_earnings or 0):,.2f}.",
        })

    return {"insights": insights}


# ── Charts ────────────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/charts")
async def get_charts(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(MeeshoReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    summary = (await db.execute(
        select(MeeshoSummary).where(MeeshoSummary.report_id == report_id)
    )).scalar_one_or_none()

    if not summary:
        return {"fee_breakdown": [], "waterfall": [], "order_status": []}

    fee_breakdown = [
        {"name": "Commission",      "value": abs(_f(summary.commission) or 0)},
        {"name": "Shipping",        "value": abs(_f(summary.shipping_charges) or 0)},
        {"name": "Reverse Shipping","value": abs(_f(summary.reverse_shipping) or 0)},
        {"name": "GST on Commission","value": abs(_f(summary.gst_on_commission) or 0)},
        {"name": "TCS",             "value": abs(_f(summary.tcs) or 0)},
    ]
    fee_breakdown = [f for f in fee_breakdown if f["value"] > 0]

    cp   = _f(summary.customer_paid_total) or 0
    comm = _f(summary.commission) or 0
    ship = _f(summary.shipping_charges) or 0
    rev  = _f(summary.reverse_shipping) or 0
    gst  = _f(summary.gst_on_commission) or 0
    tcs  = _f(summary.tcs) or 0
    net  = _f(summary.net_earnings) or 0
    ret  = _f(summary.returns_value) or 0

    waterfall = [
        {"name": "Customer Paid",   "value": cp,       "type": "absolute"},
        {"name": "Returns",         "value": abs(ret), "type": "decrease"},
        {"name": "Commission",      "value": abs(comm),"type": "decrease"},
        {"name": "Shipping",        "value": abs(ship),"type": "decrease"},
        {"name": "Reverse Shipping","value": abs(rev), "type": "decrease"},
        {"name": "GST+TCS",         "value": abs(gst) + abs(tcs), "type": "decrease"},
        {"name": "Net Earnings",    "value": net,      "type": "absolute"},
    ]

    order_status = []
    for label, val in [
        ("Delivered", summary.delivered_orders),
        ("Returned",  summary.returned_orders),
        ("Cancelled", summary.cancelled_orders),
        ("Pending",   summary.pending_orders),
    ]:
        if val:
            order_status.append({"name": label, "value": val})

    return {"fee_breakdown": fee_breakdown, "waterfall": waterfall, "order_status": order_status}


# ── Patch recon issue ─────────────────────────────────────────────────────────

@router.patch("/recon-issues/{issue_id}")
async def patch_issue(
    issue_id: UUID,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    issue = await db.get(MeeshoReconIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    if issue.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if "status" in body:
        issue.status = body["status"]
    await db.commit()
    return _issue_dict(issue)


# ── Docs status ───────────────────────────────────────────────────────────────

@router.get("/docs-status")
async def docs_status(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    rows = (await db.execute(
        select(MeeshoReport.report_type, MeeshoReport.status, MeeshoReport.uploaded_at,
               MeeshoReport.original_name, MeeshoReport.id)
        .where(MeeshoReport.company_id == company_id)
        .order_by(desc(MeeshoReport.uploaded_at))
    )).all()

    docs: Dict[str, Any] = {}
    for rt, st, ua, name, rid in rows:
        if rt not in docs:
            docs[rt] = {
                "report_type": rt, "status": st,
                "uploaded_at": ua.isoformat() if ua else None,
                "original_name": name, "report_id": str(rid),
            }
    return {"docs": docs}
