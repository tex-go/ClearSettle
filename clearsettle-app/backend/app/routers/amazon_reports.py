"""
Amazon Settlement Report API.

Prefix: /amazon

Endpoints:
  POST   /amazon/upload                    — upload settlement file (multipart)
  POST   /amazon/reports/{id}/confirm      — trigger full ingestion
  GET    /amazon/reports                   — list reports for company
  GET    /amazon/reports/{id}              — report metadata
  DELETE /amazon/reports/{id}              — delete report + all data
  GET    /amazon/reports/{id}/summary      — KPI cards
  GET    /amazon/reports/{id}/orders       — order rows (paginated, filterable)
  GET    /amazon/reports/{id}/reconciliation — recon issues
  GET    /amazon/reports/{id}/insights     — automated insights
  GET    /amazon/reports/{id}/charts       — chart data
  PATCH  /amazon/recon-issues/{issue_id}   — update issue status
  GET    /amazon/docs-status               — which docs have been uploaded
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
    HTTPException, Query, UploadFile, status,
)
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.database import AsyncSessionLocal
from app.db.models.amazon_report import (
    AmazonReport, AmazonSummary, AmazonOrderRow, AmazonReconIssue,
)
from app.services.amazon.parser import parse_amazon_settlement
from app.services.amazon.analyzer import build_amazon_summary, compute_amazon_order_analytics
from app.services.amazon.reconciliation import run_amazon_reconciliation

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "/tmp/amazon_uploads"

_VALID_DOC_TYPES = {"settlement_report", "bank_statement"}
_DOC_LABELS = {
    "settlement_report": "Settlement Report",
    "bank_statement":    "Bank Statement",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _company_id(user) -> UUID:
    if hasattr(user, "companies") and user.companies:
        return user.companies[0].id
    raise HTTPException(status_code=422, detail="No company associated with this account.")


def _assert_owner(report: AmazonReport, company_id: UUID) -> None:
    if report.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")


def _f(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _summary_dict(s: AmazonSummary) -> Dict[str, Any]:
    return {
        "gross_sales":                   _f(s.gross_sales),
        "refunds":                        _f(s.refunds),
        "promotions":                     _f(s.promotions),
        "net_sales":                      _f(s.net_sales),
        "commission":                     _f(s.commission),
        "fba_fees":                       _f(s.fba_fees),
        "shipping_fees":                  _f(s.shipping_fees),
        "other_fees":                     _f(s.other_fees),
        "withheld_tax":                   _f(s.withheld_tax),
        "total_fees":                     _f(s.total_fees),
        "net_earnings":                   _f(s.net_earnings),
        "amount_deposited":               _f(s.amount_deposited),
        "settlement_variance":            _f(s.settlement_variance),
        "total_orders":                   s.total_orders,
        "total_refunded_orders":          s.total_refunded_orders,
        "total_units":                    s.total_units,
        "effective_commission_rate_pct":  _f(s.effective_commission_rate_pct),
        "return_rate_pct":                _f(s.return_rate_pct),
        "fee_rate_pct":                   _f(s.fee_rate_pct),
    }


def _order_dict(r: AmazonOrderRow) -> Dict[str, Any]:
    return {
        "id":                   str(r.id),
        "order_id":             r.order_id,
        "merchant_order_id":    r.merchant_order_id,
        "order_date":           r.order_date.isoformat() if r.order_date else None,
        "shipment_date":        r.shipment_date.isoformat() if r.shipment_date else None,
        "posted_date":          r.posted_date.isoformat() if r.posted_date else None,
        "sku":                  r.sku,
        "product_name":         r.product_name,
        "quantity":             r.quantity,
        "transaction_type":     r.transaction_type,
        "gross_amount":         _f(r.gross_amount),
        "commission":           _f(r.commission),
        "fba_fee":              _f(r.fba_fee),
        "shipping_fee":         _f(r.shipping_fee),
        "other_fees":           _f(r.other_fees),
        "withheld_tax":         _f(r.withheld_tax),
        "promotions":           _f(r.promotions),
        "net_amount":           _f(r.net_amount),
        "expected_net":         _f(r.expected_net),
        "settlement_variance":  _f(r.settlement_variance),
    }


def _issue_dict(r: AmazonReconIssue) -> Dict[str, Any]:
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
        report = await db.get(AmazonReport, report_id)
        if not report:
            return

        try:
            report.status = "processing"
            await db.commit()

            parsed = parse_amazon_settlement(file_bytes, filename=filename)

            if parsed["errors"] and not parsed["order_rows"]:
                report.status = "failed"
                report.error_message = "; ".join(parsed["errors"][:3])
                await db.commit()
                return

            meta        = parsed["meta"]
            enriched    = compute_amazon_order_analytics(parsed["order_rows"])
            summary_kpis = build_amazon_summary(meta, enriched)
            issues_raw  = run_amazon_reconciliation(enriched)

            company_id = report.company_id

            def _dec(v) -> Optional[Decimal]:
                if v is None:
                    return None
                try:
                    return Decimal(str(v))
                except Exception:
                    return None

            # Persist summary
            db.add(AmazonSummary(
                id=uuid.uuid4(),
                report_id=report_id,
                company_id=company_id,
                gross_sales=_dec(summary_kpis.get("gross_sales")),
                refunds=_dec(summary_kpis.get("refunds")),
                promotions=_dec(summary_kpis.get("promotions")),
                net_sales=_dec(summary_kpis.get("net_sales")),
                commission=_dec(summary_kpis.get("commission")),
                fba_fees=_dec(summary_kpis.get("fba_fees")),
                shipping_fees=_dec(summary_kpis.get("shipping_fees")),
                other_fees=_dec(summary_kpis.get("other_fees")),
                withheld_tax=_dec(summary_kpis.get("withheld_tax")),
                total_fees=_dec(summary_kpis.get("total_fees")),
                net_earnings=_dec(summary_kpis.get("net_earnings")),
                amount_deposited=_dec(summary_kpis.get("amount_deposited")),
                settlement_variance=_dec(summary_kpis.get("settlement_variance")),
                total_orders=summary_kpis.get("total_orders"),
                total_refunded_orders=summary_kpis.get("total_refunded_orders"),
                total_units=summary_kpis.get("total_units"),
                effective_commission_rate_pct=_dec(summary_kpis.get("effective_commission_rate_pct")),
                return_rate_pct=_dec(summary_kpis.get("return_rate_pct")),
                fee_rate_pct=_dec(summary_kpis.get("fee_rate_pct")),
            ))

            # Persist order rows
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
                db.add(AmazonOrderRow(
                    id=uuid.uuid4(),
                    report_id=report_id,
                    company_id=company_id,
                    order_id=r.get("order_id"),
                    merchant_order_id=r.get("merchant_order_id"),
                    order_date=_pd(r.get("order_date")),
                    shipment_date=_pd(r.get("shipment_date")),
                    posted_date=_pd(r.get("posted_date")),
                    sku=r.get("sku"),
                    product_name=r.get("product_name"),
                    quantity=r.get("quantity"),
                    transaction_type=r.get("transaction_type"),
                    gross_amount=_dec(r.get("gross_amount")),
                    commission=_dec(r.get("commission")),
                    fba_fee=_dec(r.get("fba_fee")),
                    shipping_fee=_dec(r.get("shipping_fee")),
                    other_fees=_dec(r.get("other_fees")),
                    withheld_tax=_dec(r.get("withheld_tax")),
                    promotions=_dec(r.get("promotions")),
                    net_amount=_dec(r.get("net_amount")),
                    expected_net=_dec(r.get("expected_net")),
                    settlement_variance=_dec(r.get("settlement_variance")),
                ))

            # Persist recon issues
            for iss in issues_raw:
                db.add(AmazonReconIssue(
                    id=uuid.uuid4(),
                    report_id=report_id,
                    company_id=company_id,
                    issue_type=iss["issue_type"],
                    severity=iss["severity"],
                    order_id=iss.get("order_id"),
                    sku=iss.get("sku"),
                    expected_amount=_dec(iss.get("expected_amount")),
                    actual_amount=_dec(iss.get("actual_amount")),
                    variance=_dec(iss.get("variance")),
                    description=iss["description"],
                ))

            # Update report metadata
            report.status = "done"
            report.settlement_id         = meta.get("settlement_id")
            report.settlement_start_date = meta.get("settlement_start_date")
            report.settlement_end_date   = meta.get("settlement_end_date")
            report.deposit_date          = meta.get("deposit_date")
            report.total_deposit_amount  = _dec(meta.get("total_amount"))
            report.row_count             = len(enriched)
            report.processed_at          = datetime.utcnow()

            await db.commit()
            logger.info(
                "Amazon report %s ingested: %d orders, %d issues",
                report_id, len(enriched), len(issues_raw),
            )

        except Exception as exc:
            logger.exception("Amazon ingestion failed for report %s", report_id)
            try:
                report.status = "failed"
                report.error_message = str(exc)[:500]
                await db.commit()
            except Exception:
                pass


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=202)
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    report_type: str = Form("settlement_report"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)

    if report_type not in _VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid report_type. Must be one of: {', '.join(_VALID_DOC_TYPES)}")

    fname_lower = (file.filename or "").lower()
    allowed_exts = (".txt", ".xlsx", ".xls", ".csv", ".tsv", ".zip")
    if not any(fname_lower.endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(allowed_exts)}")

    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 100 MB.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Duplicate detection
    try:
        existing = (await db.execute(
            select(AmazonReport)
            .where(
                AmazonReport.company_id == company_id,
                AmazonReport.file_hash == file_hash,
                AmazonReport.status != "failed",
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
    ext = os.path.splitext(fname_lower)[1] or ".txt"
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as fh:
        fh.write(file_bytes)

    # Non-settlement uploads (e.g. bank statement) — just store
    if report_type != "settlement_report":
        try:
            report = AmazonReport(
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
        parsed = parse_amazon_settlement(file_bytes, filename=file.filename or "")
        meta = parsed.get("meta", {})
        preview = {
            "settlement_id":         meta.get("settlement_id"),
            "settlement_start_date": str(meta.get("settlement_start_date") or ""),
            "settlement_end_date":   str(meta.get("settlement_end_date") or ""),
            "deposit_date":          str(meta.get("deposit_date") or ""),
            "estimated_orders":      len(parsed.get("order_rows", [])),
            "raw_row_count":         parsed.get("row_count", 0),
            "parse_errors":          parsed.get("errors", [])[:3],
        }
    except Exception as exc:
        preview = {"parse_errors": [str(exc)[:200]]}

    try:
        report = AmazonReport(
            id=uuid.uuid4(), company_id=company_id,
            filename=stored_name, original_name=file.filename,
            file_size_bytes=len(file_bytes), file_hash=file_hash,
            report_type="settlement_report", status="awaiting_confirmation",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Database error: {exc}")

    return {
        "id": str(report.id), "original_name": report.original_name,
        "file_size_bytes": len(file_bytes), "report_type": "settlement_report",
        "status": "awaiting_confirmation", "preview": preview,
        "message": "Settlement report uploaded. Call POST /confirm to begin full analysis.",
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
    report = await db.get(AmazonReport, report_id)
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
        select(AmazonReport)
        .where(AmazonReport.company_id == company_id)
        .order_by(desc(AmazonReport.uploaded_at))
        .limit(50)
    )).scalars().all()

    return {"reports": [
        {
            "id":                    str(r.id),
            "original_name":         r.original_name,
            "report_type":           r.report_type,
            "status":                r.status,
            "settlement_id":         r.settlement_id,
            "settlement_start_date": r.settlement_start_date.isoformat() if r.settlement_start_date else None,
            "settlement_end_date":   r.settlement_end_date.isoformat() if r.settlement_end_date else None,
            "deposit_date":          r.deposit_date.isoformat() if r.deposit_date else None,
            "total_deposit_amount":  _f(r.total_deposit_amount),
            "row_count":             r.row_count,
            "file_size_bytes":       r.file_size_bytes,
            "uploaded_at":           r.uploaded_at.isoformat(),
            "processed_at":          r.processed_at.isoformat() if r.processed_at else None,
            "error_message":         r.error_message,
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
    report = await db.get(AmazonReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)
    return {
        "id": str(report.id), "original_name": report.original_name,
        "report_type": report.report_type, "status": report.status,
        "settlement_id": report.settlement_id,
        "settlement_start_date": report.settlement_start_date.isoformat() if report.settlement_start_date else None,
        "settlement_end_date":   report.settlement_end_date.isoformat() if report.settlement_end_date else None,
        "deposit_date":          report.deposit_date.isoformat() if report.deposit_date else None,
        "total_deposit_amount":  _f(report.total_deposit_amount),
        "currency":              report.currency,
        "row_count":             report.row_count,
        "file_size_bytes":       report.file_size_bytes,
        "uploaded_at":           report.uploaded_at.isoformat(),
        "processed_at":          report.processed_at.isoformat() if report.processed_at else None,
        "error_message":         report.error_message,
    }


# ── Delete report ─────────────────────────────────────────────────────────────

@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(AmazonReport, report_id)
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
    report = await db.get(AmazonReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    summary = (await db.execute(
        select(AmazonSummary).where(AmazonSummary.report_id == report_id)
    )).scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not ready yet.")

    return {
        "report_id": str(report_id),
        "settlement_id": report.settlement_id,
        "settlement_start_date": report.settlement_start_date.isoformat() if report.settlement_start_date else None,
        "settlement_end_date":   report.settlement_end_date.isoformat() if report.settlement_end_date else None,
        "deposit_date":          report.deposit_date.isoformat() if report.deposit_date else None,
        "total_deposit_amount":  _f(report.total_deposit_amount),
        **_summary_dict(summary),
    }


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/orders")
async def get_orders(
    report_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    transaction_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(AmazonReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    q = select(AmazonOrderRow).where(AmazonOrderRow.report_id == report_id)
    if transaction_type:
        q = q.where(AmazonOrderRow.transaction_type.ilike(f"%{transaction_type}%"))
    if search:
        q = q.where(
            AmazonOrderRow.order_id.ilike(f"%{search}%") |
            AmazonOrderRow.sku.ilike(f"%{search}%")
        )

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(AmazonOrderRow.posted_date.desc().nullslast())
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
    report = await db.get(AmazonReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    q = select(AmazonReconIssue).where(AmazonReconIssue.report_id == report_id)
    if severity:
        q = q.where(AmazonReconIssue.severity == severity)
    if issue_type:
        q = q.where(AmazonReconIssue.issue_type == issue_type)

    issues = (await db.execute(q.order_by(AmazonReconIssue.created_at.desc()))).scalars().all()
    total_variance = sum(abs(float(i.variance or 0)) for i in issues)

    return {
        "total_issues":    len(issues),
        "total_variance":  total_variance,
        "issues":          [_issue_dict(i) for i in issues],
    }


# ── Insights ──────────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}/insights")
async def get_insights(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    report = await db.get(AmazonReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    summary = (await db.execute(
        select(AmazonSummary).where(AmazonSummary.report_id == report_id)
    )).scalar_one_or_none()

    if not summary:
        return {"insights": []}

    insights = []

    if summary.settlement_variance and abs(float(summary.settlement_variance)) > 100:
        sign = "more" if float(summary.settlement_variance) > 0 else "less"
        insights.append({
            "type": "warning" if abs(float(summary.settlement_variance)) > 500 else "info",
            "title": "Settlement Variance Detected",
            "description": f"You received ₹{abs(float(summary.settlement_variance)):,.2f} {sign} than calculated from order data. Review adjustment items.",
        })

    if summary.effective_commission_rate_pct and float(summary.effective_commission_rate_pct) > 20:
        insights.append({
            "type": "warning",
            "title": "High Commission Rate",
            "description": f"Effective commission rate is {float(summary.effective_commission_rate_pct):.1f}%. Review your category fee structure.",
        })

    if summary.return_rate_pct and float(summary.return_rate_pct) > 15:
        insights.append({
            "type": "warning",
            "title": "High Return Rate",
            "description": f"Return rate is {float(summary.return_rate_pct):.1f}%. Investigate return reasons to reduce costs.",
        })

    if summary.total_orders and summary.total_orders > 0:
        insights.append({
            "type": "success",
            "title": "Settlement Processed",
            "description": f"{summary.total_orders} orders processed with net earnings ₹{float(summary.net_earnings or 0):,.2f}.",
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
    report = await db.get(AmazonReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    _assert_owner(report, company_id)

    summary = (await db.execute(
        select(AmazonSummary).where(AmazonSummary.report_id == report_id)
    )).scalar_one_or_none()

    if not summary:
        return {"fee_breakdown": [], "waterfall": []}

    fee_breakdown = [
        {"name": "Commission",   "value": abs(_f(summary.commission) or 0)},
        {"name": "FBA Fees",     "value": abs(_f(summary.fba_fees) or 0)},
        {"name": "Shipping",     "value": abs(_f(summary.shipping_fees) or 0)},
        {"name": "Withheld Tax", "value": abs(_f(summary.withheld_tax) or 0)},
        {"name": "Other Fees",   "value": abs(_f(summary.other_fees) or 0)},
    ]
    fee_breakdown = [f for f in fee_breakdown if f["value"] > 0]

    gross  = _f(summary.gross_sales) or 0
    comm   = _f(summary.commission) or 0
    fba    = _f(summary.fba_fees) or 0
    ship   = _f(summary.shipping_fees) or 0
    tax    = _f(summary.withheld_tax) or 0
    other  = _f(summary.other_fees) or 0
    net    = _f(summary.net_earnings) or 0

    waterfall = [
        {"name": "Gross Sales",    "value": gross,       "type": "absolute"},
        {"name": "Refunds",        "value": _f(summary.refunds) or 0, "type": "decrease"},
        {"name": "Commission",     "value": abs(comm),   "type": "decrease"},
        {"name": "FBA Fees",       "value": abs(fba),    "type": "decrease"},
        {"name": "Shipping",       "value": abs(ship),   "type": "decrease"},
        {"name": "Tax Withheld",   "value": abs(tax),    "type": "decrease"},
        {"name": "Other Fees",     "value": abs(other),  "type": "decrease"},
        {"name": "Net Earnings",   "value": net,         "type": "absolute"},
    ]

    return {"fee_breakdown": fee_breakdown, "waterfall": waterfall}


# ── Patch recon issue ─────────────────────────────────────────────────────────

@router.patch("/recon-issues/{issue_id}")
async def patch_issue(
    issue_id: UUID,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    issue = await db.get(AmazonReconIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    if issue.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    allowed = {"status"}
    for k, v in body.items():
        if k in allowed:
            setattr(issue, k, v)
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
        select(AmazonReport.report_type, AmazonReport.status, AmazonReport.uploaded_at,
               AmazonReport.original_name, AmazonReport.id)
        .where(AmazonReport.company_id == company_id)
        .order_by(desc(AmazonReport.uploaded_at))
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
