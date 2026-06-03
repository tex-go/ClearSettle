"""
Intelligent Report Ingestion Engine — API Router.

Prefix: /ingestion

Endpoints:
  POST   /ingestion/upload                      — upload any marketplace report (auto-detect)
  GET    /ingestion/files                       — list uploaded files with detection status
  GET    /ingestion/files/{id}                  — single file metadata
  GET    /ingestion/files/{id}/detection        — detection result + confidence + signals
  GET    /ingestion/files/{id}/logs             — processing audit trail
  GET    /ingestion/files/{id}/ledger           — normalized ledger records (paginated)
  GET    /ingestion/files/{id}/summary          — financial KPI summary
  GET    /ingestion/files/{id}/reconciliation   — discrepancy list computed from ledger
  GET    /ingestion/files/{id}/export           — download ledger as CSV
  POST   /ingestion/files/{id}/reprocess        — re-run pipeline (e.g. after schema update)
  POST   /ingestion/files/{id}/manual-review    — admin override: set platform/type/parser
  GET    /ingestion/schema-drifts               — list files with schema drift alerts
  DELETE /ingestion/files/{id}                  — delete file + all derived data
"""
from __future__ import annotations

import csv
import hashlib
import io
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
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.database import AsyncSessionLocal
from app.db.models.ingestion import (
    UploadedFile, ReportDetectionResult,
    ReportProcessingLog, IngestionLedger,
)
from app.services.intelligence.pipeline import IntelligencePipeline

logger = logging.getLogger(__name__)
router = APIRouter()

# Mount a persistent volume at UPLOAD_DIR in production (e.g. /data/uploads or S3-fuse).
# Defaults to /tmp only for local dev — /tmp is ephemeral in containers.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/ingestion_uploads")
MAX_FILE_MB = 100


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _company_id(user) -> UUID:
    if hasattr(user, "companies") and user.companies:
        return user.companies[0].id
    raise HTTPException(status_code=422, detail="No company associated with this account.")


def _assert_owner(record: UploadedFile, company_id: UUID) -> None:
    if record.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")


# ── Serialisers ───────────────────────────────────────────────────────────────

def _file_to_dict(f: UploadedFile, detection: ReportDetectionResult | None = None) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id":                str(f.id),
        "original_file_name": f.original_file_name,
        "file_size_bytes":   f.file_size_bytes,
        "mime_type":         f.mime_type,
        "upload_source":     f.upload_source,
        "upload_status":     f.upload_status,
        "error_message":     f.error_message,
        "uploaded_at":       f.uploaded_at.isoformat(),
        "processed_at":      f.processed_at.isoformat() if f.processed_at else None,
    }
    if detection:
        d["detection"] = {
            "detected_platform":    detection.detected_platform,
            "detected_report_type": detection.detected_report_type,
            "schema_version":       detection.schema_version,
            "confidence_score":     float(detection.confidence_score or 0),
            "parser_name":          detection.parser_name,
            "needs_manual_review":  detection.needs_manual_review,
        }
    return d


def _detection_to_dict(d: ReportDetectionResult) -> Dict[str, Any]:
    return {
        "id":                    str(d.id),
        "uploaded_file_id":      str(d.uploaded_file_id),
        "detected_platform":     d.detected_platform,
        "detected_report_type":  d.detected_report_type,
        "schema_version":        d.schema_version,
        "confidence_score":      float(d.confidence_score or 0),
        "parser_name":           d.parser_name,
        "needs_manual_review":   d.needs_manual_review,
        "detection_metadata":    d.detection_metadata or {},
        "reviewed_by":           str(d.reviewed_by) if d.reviewed_by else None,
        "reviewed_at":           d.reviewed_at.isoformat() if d.reviewed_at else None,
        "created_at":            d.created_at.isoformat(),
    }


def _log_to_dict(l: ReportProcessingLog) -> Dict[str, Any]:
    return {
        "level":      l.level,
        "stage":      l.stage,
        "message":    l.message,
        "context":    l.context or {},
        "created_at": l.created_at.isoformat(),
    }


def _ledger_to_dict(r: IngestionLedger) -> Dict[str, Any]:
    return {
        "id":               str(r.id),
        "platform":         r.platform,
        "report_type":      r.report_type,
        "order_id":         r.order_id,
        "shipment_id":      r.shipment_id,
        "settlement_id":    r.settlement_id,
        "sku":              r.sku,
        "product_title":    r.product_title,
        "category":         r.category,
        "transaction_type": r.transaction_type,
        "fee_type":         r.fee_type,
        "amount":           float(r.amount) if r.amount is not None else None,
        "tax_amount":       float(r.tax_amount) if r.tax_amount is not None else None,
        "currency":         r.currency,
        "transaction_date": r.transaction_date,
        "settlement_date":  r.settlement_date,
        "return_status":    r.return_status,
        "payout_status":    r.payout_status,
        "source_row_number": r.source_row_number,
    }


# ── Background ingestion task ─────────────────────────────────────────────────

async def _run_ingestion(
    uploaded_file_id: UUID,
    file_bytes: bytes,
    file_name: str,
    company_id: UUID,
    user_id: UUID,
    platform_hint: Optional[str] = None,
    report_type_hint: Optional[str] = None,
) -> None:
    """Full ingestion pipeline: detect → parse → persist."""
    if AsyncSessionLocal is None:
        return

    async with AsyncSessionLocal() as db:
        record = await db.get(UploadedFile, uploaded_file_id)
        if not record:
            return

        try:
            logger.info(
                "[INFO] Upload received file=%s bytes=%d company=%s",
                file_name, len(file_bytes), company_id,
            )
            record.upload_status = "detecting"
            await db.commit()
            logger.info("[INFO] File saved file_id=%s", uploaded_file_id)

            # ── Run pipeline ──────────────────────────────────────────────────
            logger.info("[INFO] Pipeline started file_id=%s", uploaded_file_id)
            from app.services.pipeline.router import run_ingestion_pipeline
            pipeline_result, parse_result = run_ingestion_pipeline(
                file_bytes, file_name, uploaded_file_id,
                platform_hint=platform_hint,
                report_type_hint=report_type_hint,
            )

            logger.info(
                "[INFO] Platform detected platform=%s confidence=%.2f needs_review=%s",
                pipeline_result.platform, pipeline_result.confidence_score,
                pipeline_result.needs_manual_review,
            )
            logger.info(
                "[INFO] Parser selected parser=%s schema=%s report_type=%s",
                pipeline_result.parser_name, pipeline_result.schema_version,
                pipeline_result.report_type,
            )
            if parse_result:
                logger.info(
                    "[INFO] Records parsed count=%d recon_issues=%d",
                    parse_result.record_count, len(parse_result.recon_issues),
                )
            else:
                logger.warning("[WARNING] Parser returned no records file_id=%s", uploaded_file_id)

            # ── Run 14-agent Intelligence Pipeline ───────────────────────────────
            parsed_data_for_intel: dict = {}
            if parse_result and not parse_result.is_empty:
                parsed_data_for_intel = {
                    "orders": [
                        {k: str(v) if hasattr(v, "__class__") and v.__class__.__name__ == "Decimal" else v
                         for k, v in (o.__dict__ if hasattr(o, "__dict__") else o).items()
                         if not k.startswith("_")}
                        for o in (parse_result.ledger_records or [])[:500]
                    ],
                    "summary": {},
                }

            intel_result = None
            try:
                intel_pipeline = IntelligencePipeline()
                intel_result = await intel_pipeline.run(
                    file_bytes=file_bytes,
                    filename=file_name,
                    upload_id=str(uploaded_file_id),
                    company_id=str(company_id),
                    db=db,
                    parsed_data=parsed_data_for_intel,
                    platform_hint=platform_hint,
                    report_type_hint=report_type_hint,
                )
                logger.info(
                    "Intelligence pipeline complete for file %s: platform=%s quality=%.0f "
                    "insights=%d recoverable=%s",
                    uploaded_file_id,
                    intel_result.summary.get("platform", "?"),
                    intel_result.summary.get("quality_score", 0),
                    intel_result.summary.get("insights_count", 0),
                    intel_result.summary.get("total_recoverable", "0"),
                )
            except Exception as intel_exc:
                logger.warning(
                    "Intelligence pipeline error for file %s (non-fatal): %s",
                    uploaded_file_id, intel_exc,
                )

            # Build detection_metadata: combine existing pipeline metadata + intelligence result
            base_metadata = pipeline_result.detection_metadata or {}
            if intel_result:
                try:
                    intel_dict = intel_result.model_dump(mode="json")
                    base_metadata["intelligence"] = intel_dict
                    base_metadata["intelligence_summary"] = intel_result.summary
                except Exception:
                    pass

            # ── Persist detection result ──────────────────────────────────────
            detection = ReportDetectionResult(
                id=uuid.uuid4(),
                uploaded_file_id=uploaded_file_id,
                detected_platform=pipeline_result.platform,
                detected_report_type=pipeline_result.report_type,
                schema_version=pipeline_result.schema_version,
                confidence_score=Decimal(str(pipeline_result.confidence_score)),
                detection_metadata=base_metadata,
                parser_name=pipeline_result.parser_name,
                needs_manual_review=pipeline_result.needs_manual_review,
            )
            db.add(detection)

            # ── Persist processing logs ───────────────────────────────────────
            for entry in (pipeline_result.detection_metadata.get("processing_logs") or []):
                db.add(ReportProcessingLog(
                    id=uuid.uuid4(),
                    uploaded_file_id=uploaded_file_id,
                    level=entry.get("level", "info"),
                    stage=entry.get("stage", "pipeline"),
                    message=entry.get("message", ""),
                    context=entry.get("context"),
                ))

            # ── Persist ledger records ────────────────────────────────────────
            if parse_result and not parse_result.is_empty:
                logger.info(
                    "[INFO] Ledger creation started file_id=%s records=%d",
                    uploaded_file_id, parse_result.record_count,
                )
                record.upload_status = "processing"
                await db.commit()

                for lr in parse_result.ledger_records:
                    db.add(IngestionLedger(
                        id=uuid.uuid4(),
                        uploaded_file_id=uploaded_file_id,
                        company_id=company_id,
                        platform=lr.platform,
                        report_type=lr.report_type,
                        order_id=lr.order_id,
                        shipment_id=lr.shipment_id,
                        settlement_id=lr.settlement_id,
                        invoice_id=lr.invoice_id,
                        sku=lr.sku,
                        product_title=lr.product_title,
                        category=lr.category,
                        transaction_type=lr.transaction_type,
                        fee_type=lr.fee_type,
                        amount=Decimal(str(lr.amount)) if lr.amount is not None else None,
                        tax_amount=Decimal(str(lr.tax_amount)) if lr.tax_amount is not None else None,
                        currency=lr.currency,
                        transaction_date=lr.transaction_date,
                        settlement_date=lr.settlement_date,
                        return_status=lr.return_status,
                        payout_status=lr.payout_status,
                        source_row_number=lr.source_row_number,
                        lineage_metadata=lr.lineage_metadata,
                    ))

            final_status = "needs_review" if pipeline_result.needs_manual_review else (
                "failed" if pipeline_result.errors and not parse_result else "done"
            )
            record.upload_status = final_status
            record.processed_at  = datetime.utcnow()
            if pipeline_result.errors:
                record.error_message = "; ".join(pipeline_result.errors[:3])

            await db.commit()

            if pipeline_result.ledger_count > 0:
                logger.info(
                    "[INFO] Ledger records created count=%d file_id=%s",
                    pipeline_result.ledger_count, uploaded_file_id,
                )
            logger.info(
                "[INFO] Reconciliation completed recon_issues=%d file_id=%s",
                pipeline_result.recon_issue_count, uploaded_file_id,
            )
            if pipeline_result.errors:
                for err in pipeline_result.errors[:5]:
                    logger.error("[ERROR] Pipeline error file_id=%s error=%s", uploaded_file_id, err)
            logger.info(
                "[INFO] Dashboard metrics generated platform=%s type=%s "
                "ledger=%d status=%s file_id=%s",
                pipeline_result.platform, pipeline_result.report_type,
                pipeline_result.ledger_count, final_status, uploaded_file_id,
            )

        except Exception as exc:
            logger.error(
                "[ERROR] Ingestion pipeline failed file=%s file_id=%s error=%s",
                file_name, uploaded_file_id, exc,
            )
            try:
                record.upload_status = "failed"
                record.error_message = str(exc)[:500]
                record.processed_at  = datetime.utcnow()  # always set on all paths
                await db.commit()
            except Exception:
                pass


# ── Upload endpoint ───────────────────────────────────────────────────────────

@router.post("/upload", status_code=202)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    platform:    Optional[str] = Form(None, description="Platform hint: flipkart | amazon | meesho"),
    report_type: Optional[str] = Form(None, description="Report type hint: pl_report | payment_report | settlement_report | …"),
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Upload any marketplace report.

    Optional form fields:
    - platform: 'flipkart' | 'amazon' | 'meesho' — skips auto-detection when provided
    - report_type: 'pl_report' | 'payment_report' | 'settlement_report' | … — skips report type detection

    The system automatically (or uses hints when provided):
    1. Fingerprints the file (extracts sheets, headers, column signatures)
    2. Detects the platform with confidence score (or uses platform hint)
    3. Detects report type (or uses report_type hint)
    4. Detects schema version and flags drift if schema changed
    5. Routes to the correct parser
    6. Normalises into the unified ingestion ledger
    7. Runs reconciliation and detects anomalies

    Returns immediately (202) with file_id + confidence preview.
    Processing happens in background — poll GET /ingestion/files/{id} for status.
    """
    # Normalise hint values
    platform_hint    = (platform or "").strip().lower() or None
    report_type_hint = (report_type or "").strip().lower() or None
    company_id = _company_id(user)

    fname_lower = (file.filename or "").lower()
    allowed = {".xlsx", ".xls", ".xlsm", ".csv", ".tsv", ".txt"}
    ext = "." + fname_lower.rsplit(".", 1)[-1] if "." in fname_lower else ""
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed))}",
        )

    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_FILE_MB} MB.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # ── Duplicate detection ───────────────────────────────────────────────────
    existing = (await db.execute(
        select(UploadedFile)
        .where(
            UploadedFile.company_id == company_id,
            UploadedFile.file_hash_sha256 == file_hash,
            UploadedFile.upload_status != "failed",
        )
        .order_by(desc(UploadedFile.uploaded_at))
        .limit(1)
    )).scalar_one_or_none()

    if existing:
        detection = (await db.execute(
            select(ReportDetectionResult)
            .where(ReportDetectionResult.uploaded_file_id == existing.id)
        )).scalar_one_or_none()

        return {
            "id":           str(existing.id),
            "duplicate":    True,
            "upload_status": existing.upload_status,
            "message":      "Duplicate file already uploaded. Returning existing record.",
            "detection":    _detection_to_dict(detection) if detection else None,
        }

    # ── Store file ────────────────────────────────────────────────────────────
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as fh:
        fh.write(file_bytes)

    # ── Quick fingerprint preview (synchronous, lightweight) ─────────────────
    preview: Dict[str, Any] = {}
    try:
        from app.services.detection.fingerprinter import fingerprint_file
        from app.services.detection.platform_detector import detect_platform
        fp = fingerprint_file(file_bytes, file.filename or "")
        plat = detect_platform(fp)
        preview = {
            "sheet_names":        [s.sheet_name for s in fp.sheets],
            "column_count":       len(fp.all_column_names),
            "detected_platform":  plat.detected_platform,
            "platform_confidence": plat.confidence_score,
            "needs_manual_review": plat.needs_manual_review,
            "matched_signals":    plat.matched_signals[:10],
        }
    except Exception as exc:
        preview = {"preview_error": str(exc)[:200]}

    # ── Persist UploadedFile record ───────────────────────────────────────────
    try:
        record = UploadedFile(
            id=uuid.uuid4(),
            company_id=company_id,
            uploaded_by=user.id if hasattr(user, "id") else None,
            original_file_name=file.filename or stored_name,
            file_hash_sha256=file_hash,
            mime_type=preview.get("mime_type", "application/octet-stream"),
            file_size_bytes=len(file_bytes),
            upload_source="web_upload",
            storage_path=stored_path,
            upload_status="uploaded",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Database error: {exc}. Run 'alembic upgrade head' if migration is pending.",
        )

    background_tasks.add_task(
        _run_ingestion,
        record.id, file_bytes, file.filename or stored_name,
        company_id, user.id if hasattr(user, "id") else None,
        platform_hint, report_type_hint,
    )

    return {
        "id":             str(record.id),
        "original_file_name": record.original_file_name,
        "file_size_bytes": len(file_bytes),
        "upload_status":  "uploaded",
        "platform_hint":  platform_hint,
        "report_type_hint": report_type_hint,
        "preview":        preview,
        "message":        (
            "File uploaded. Detection + ingestion running in background. "
            f"Poll GET /ingestion/files/{record.id} for status."
        ),
    }


# ── List files ────────────────────────────────────────────────────────────────

@router.get("/files")
async def list_files(
    platform:     Optional[str] = Query(None),
    upload_status: Optional[str] = Query(None),
    page:  int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all uploaded files for the company with detection status."""
    company_id = _company_id(user)

    q = select(UploadedFile).where(UploadedFile.company_id == company_id)
    if upload_status:
        q = q.where(UploadedFile.upload_status == upload_status)
    q = q.order_by(desc(UploadedFile.uploaded_at))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.offset((page - 1) * limit).limit(limit)
    files = (await db.execute(q)).scalars().all()

    # Fetch detections in one query
    file_ids = [f.id for f in files]
    detections: Dict[UUID, ReportDetectionResult] = {}
    if file_ids:
        det_rows = (await db.execute(
            select(ReportDetectionResult)
            .where(ReportDetectionResult.uploaded_file_id.in_(file_ids))
        )).scalars().all()
        detections = {d.uploaded_file_id: d for d in det_rows}

    # Apply platform filter if specified (post-fetch, since platform is in detection)
    items = []
    for f in files:
        det = detections.get(f.id)
        if platform and (not det or det.detected_platform != platform):
            continue
        items.append(_file_to_dict(f, det))

    return {"total": total, "page": page, "limit": limit, "items": items}


# ── Single file ───────────────────────────────────────────────────────────────

@router.get("/files/{file_id}")
async def get_file(
    file_id: UUID,
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    detection = (await db.execute(
        select(ReportDetectionResult)
        .where(ReportDetectionResult.uploaded_file_id == file_id)
    )).scalar_one_or_none()

    return _file_to_dict(record, detection)


# ── Detection result ──────────────────────────────────────────────────────────

@router.get("/files/{file_id}/detection")
async def get_detection(
    file_id: UUID,
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return full detection result including matched signals and schema hints."""
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    detection = (await db.execute(
        select(ReportDetectionResult)
        .where(ReportDetectionResult.uploaded_file_id == file_id)
    )).scalar_one_or_none()

    if not detection:
        return {
            "file_id":      str(file_id),
            "upload_status": record.upload_status,
            "message":      "Detection not yet complete. File may still be processing.",
        }

    result = _detection_to_dict(detection)

    # Enrich with live DB counts so frontend ledger_records_count / recon_issue_count are accurate
    ledger_count = (await db.execute(
        select(func.count()).where(IngestionLedger.uploaded_file_id == file_id)
    )).scalar_one()
    result["ledger_records_count"] = ledger_count

    # Recon issue count: warnings from processing logs that contain "variance"
    warning_count = (await db.execute(
        select(func.count())
        .where(ReportProcessingLog.uploaded_file_id == file_id)
        .where(ReportProcessingLog.level == "warning")
    )).scalar_one()
    result["recon_issue_count"] = warning_count

    # Include drift alert from metadata for convenient frontend access
    meta = detection.detection_metadata or {}
    if meta.get("drift_alert"):
        result["drift_alert"] = meta["drift_alert"]

    return result


# ── Processing logs ───────────────────────────────────────────────────────────

@router.get("/files/{file_id}/logs")
async def get_logs(
    file_id: UUID,
    level:   Optional[str] = Query(None, description="info | warning | error"),
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return the full processing audit trail for a file."""
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    q = select(ReportProcessingLog).where(ReportProcessingLog.uploaded_file_id == file_id)
    if level:
        q = q.where(ReportProcessingLog.level == level)
    q = q.order_by(ReportProcessingLog.created_at)
    logs = (await db.execute(q)).scalars().all()

    return {"file_id": str(file_id), "count": len(logs), "logs": [_log_to_dict(l) for l in logs]}


# ── Ledger records ────────────────────────────────────────────────────────────

@router.get("/files/{file_id}/ledger")
async def get_ledger(
    file_id:          UUID,
    transaction_type: Optional[str] = Query(None),
    platform:         Optional[str] = Query(None),
    page:  int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return normalised ledger records for a file (paginated)."""
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    q = select(IngestionLedger).where(IngestionLedger.uploaded_file_id == file_id)
    if transaction_type:
        q = q.where(IngestionLedger.transaction_type == transaction_type)
    if platform:
        q = q.where(IngestionLedger.platform == platform)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(IngestionLedger.source_row_number).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    return {
        "file_id": str(file_id),
        "total":   total,
        "page":    page,
        "limit":   limit,
        "items":   [_ledger_to_dict(r) for r in rows],
    }


# ── Reprocess ─────────────────────────────────────────────────────────────────

@router.post("/files/{file_id}/reprocess", status_code=202)
async def reprocess_file(
    file_id: UUID,
    background_tasks: BackgroundTasks,
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Re-run the full ingestion pipeline for a file (e.g. after schema update)."""
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    if record.upload_status in ("detecting", "processing"):
        raise HTTPException(status_code=409, detail="File is already being processed.")

    stored_path = record.storage_path
    if not stored_path or not os.path.exists(stored_path):
        raise HTTPException(status_code=404, detail="Original file not found in storage.")

    with open(stored_path, "rb") as fh:
        file_bytes = fh.read()

    # Clear previous derived data
    await db.execute(
        select(ReportDetectionResult)
        .where(ReportDetectionResult.uploaded_file_id == file_id)
    )
    old_detection = (await db.execute(
        select(ReportDetectionResult)
        .where(ReportDetectionResult.uploaded_file_id == file_id)
    )).scalar_one_or_none()
    if old_detection:
        await db.delete(old_detection)

    old_logs = (await db.execute(
        select(ReportProcessingLog)
        .where(ReportProcessingLog.uploaded_file_id == file_id)
    )).scalars().all()
    for l in old_logs:
        await db.delete(l)

    old_ledger = (await db.execute(
        select(IngestionLedger)
        .where(IngestionLedger.uploaded_file_id == file_id)
    )).scalars().all()
    for r in old_ledger:
        await db.delete(r)

    record.upload_status = "uploaded"
    record.error_message = None
    record.processed_at  = None
    await db.commit()

    background_tasks.add_task(
        _run_ingestion,
        record.id, file_bytes, record.original_file_name,
        company_id, user.id if hasattr(user, "id") else None,
    )

    return {"file_id": str(file_id), "status": "reprocessing", "message": "Reprocessing started."}


# ── Manual review override ────────────────────────────────────────────────────

class ManualReviewBody(BaseModel):
    platform:     str
    report_type:  str
    parser_name:  Optional[str] = None
    schema_version: Optional[str] = None


@router.post("/files/{file_id}/manual-review")
async def manual_review(
    file_id: UUID,
    body:    ManualReviewBody,
    background_tasks: BackgroundTasks,
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Admin override: manually set platform/report_type/parser and re-run parsing.
    Used when auto-detection confidence is low.
    """
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    # Determine parser_name from schema if not provided
    parser_name = body.parser_name
    if not parser_name:
        from app.services.detection.schema_detector import KNOWN_SCHEMAS, _default_parser
        versions = KNOWN_SCHEMAS.get(body.platform, {}).get(body.report_type, {})
        if versions:
            latest = next(iter(versions.values()))
            parser_name = latest.get("parser", _default_parser(body.platform, body.report_type))
        else:
            parser_name = _default_parser(body.platform, body.report_type)

    # Upsert detection override
    detection = (await db.execute(
        select(ReportDetectionResult)
        .where(ReportDetectionResult.uploaded_file_id == file_id)
    )).scalar_one_or_none()

    if detection:
        detection.detected_platform    = body.platform
        detection.detected_report_type = body.report_type
        detection.schema_version       = body.schema_version
        detection.parser_name          = parser_name
        detection.needs_manual_review  = False
        detection.reviewed_by          = user.id if hasattr(user, "id") else None
        detection.reviewed_at          = datetime.utcnow()
    else:
        db.add(ReportDetectionResult(
            id=uuid.uuid4(),
            uploaded_file_id=file_id,
            detected_platform=body.platform,
            detected_report_type=body.report_type,
            schema_version=body.schema_version,
            parser_name=parser_name,
            needs_manual_review=False,
            reviewed_by=user.id if hasattr(user, "id") else None,
            reviewed_at=datetime.utcnow(),
        ))

    record.upload_status = "uploaded"
    await db.commit()

    # Trigger re-parse with overridden settings
    stored_path = record.storage_path
    if stored_path and os.path.exists(stored_path):
        with open(stored_path, "rb") as fh:
            file_bytes = fh.read()
        background_tasks.add_task(
            _run_ingestion,
            record.id, file_bytes, record.original_file_name,
            company_id, user.id if hasattr(user, "id") else None,
        )

    return {
        "file_id":     str(file_id),
        "platform":    body.platform,
        "report_type": body.report_type,
        "parser_name": parser_name,
        "status":      "reprocessing",
        "message":     "Manual override applied. Re-parsing started.",
    }


# ── Schema drift alerts ───────────────────────────────────────────────────────

@router.get("/schema-drifts")
async def get_schema_drifts(
    platform: Optional[str] = Query(None),
    page:  int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    List all files where schema drift was detected (unknown schema or low match confidence).
    These files may need parser updates or manual review.
    """
    company_id = _company_id(user)

    q = (
        select(ReportDetectionResult, UploadedFile)
        .join(UploadedFile, UploadedFile.id == ReportDetectionResult.uploaded_file_id)
        .where(UploadedFile.company_id == company_id)
        .where(ReportDetectionResult.needs_manual_review.is_(True))
    )
    if platform:
        q = q.where(ReportDetectionResult.detected_platform == platform)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(desc(UploadedFile.uploaded_at)).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).all()

    items = []
    for det, f in rows:
        meta = det.detection_metadata or {}
        drift = meta.get("drift_alert")
        items.append({
            "file_id":         str(f.id),
            "file_name":       f.original_file_name,
            "uploaded_at":     f.uploaded_at.isoformat(),
            "detected_platform": det.detected_platform,
            "report_type":     det.detected_report_type,
            "schema_version":  det.schema_version,
            "confidence_score": float(det.confidence_score or 0),
            "drift_alert":     drift,
        })

    return {"total": total, "page": page, "limit": limit, "items": items}


# ── Financial summary ─────────────────────────────────────────────────────────

@router.get("/files/{file_id}/summary", summary="Financial KPI summary for a file")
async def get_file_summary(
    file_id: UUID,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Aggregate ledger records into financial KPIs: gross revenue, fees, net settlement, etc."""
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    rows = (await db.execute(
        select(IngestionLedger)
        .where(IngestionLedger.uploaded_file_id == file_id)
    )).scalars().all()

    gross_revenue = Decimal("0")
    returns_total = Decimal("0")
    fees_total    = Decimal("0")
    tax_total     = Decimal("0")
    payout_total  = Decimal("0")
    order_ids     = set()
    platforms     = set()

    for r in rows:
        amt = r.amount or Decimal("0")
        tx  = (r.transaction_type or "").lower()
        platforms.add(r.platform)
        if r.order_id:
            order_ids.add(r.order_id)
        if tx in ("sale", "order"):
            gross_revenue += amt
        elif tx == "return":
            returns_total += amt
        elif tx == "fee":
            fees_total += amt
        elif tx in ("tax", "tds", "tcs", "gst"):
            tax_total += amt
        elif tx in ("payout", "settlement", "transfer"):
            payout_total += amt

    net_sales = gross_revenue + returns_total  # returns are typically negative
    net_settlement = net_sales + fees_total + tax_total

    detection = (await db.execute(
        select(ReportDetectionResult)
        .where(ReportDetectionResult.uploaded_file_id == file_id)
    )).scalar_one_or_none()

    return {
        "file_id":         str(file_id),
        "file_name":       record.original_file_name,
        "platform":        detection.detected_platform if detection else "unknown",
        "report_type":     detection.detected_report_type if detection else "unknown",
        "total_records":   len(rows),
        "unique_orders":   len(order_ids),
        "platforms":       list(platforms),
        "gross_revenue":   float(gross_revenue),
        "returns_total":   float(returns_total),
        "net_sales":       float(net_sales),
        "fees_total":      float(fees_total),
        "tax_total":       float(tax_total),
        "payout_total":    float(payout_total),
        "net_settlement":  float(net_settlement),
        "variance":        float(payout_total - net_settlement) if payout_total else None,
    }


# ── Reconciliation: compute discrepancies from ledger ─────────────────────────

@router.get("/files/{file_id}/reconciliation", summary="Per-order discrepancy list")
async def get_reconciliation(
    file_id:    UUID,
    min_variance: float = Query(1.0, description="Minimum absolute variance to include (default ₹1)"),
    severity:   Optional[str] = Query(None, description="critical (>500) | warning (>50) | info"),
    page:  int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Computes expected vs actual settlement per order from IngestionLedger.
    Expected = gross sale amount. Actual = payout/settlement amount.
    Returns orders where |variance| > min_variance, sorted by |variance| desc.
    """
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    rows = (await db.execute(
        select(IngestionLedger)
        .where(IngestionLedger.uploaded_file_id == file_id)
        .order_by(IngestionLedger.source_row_number)
    )).scalars().all()

    # Group by order_id
    by_order: Dict[str, Dict] = {}
    ungrouped = []  # rows without order_id

    for r in rows:
        key = r.order_id or f"__row_{r.source_row_number}"
        if key not in by_order:
            by_order[key] = {
                "order_id":   r.order_id,
                "sku":        r.sku,
                "platform":   r.platform,
                "date":       r.transaction_date or r.settlement_date,
                "expected":   Decimal("0"),
                "actual":     Decimal("0"),
                "fees":       Decimal("0"),
                "taxes":      Decimal("0"),
            }
        amt = r.amount or Decimal("0")
        tx  = (r.transaction_type or "").lower()
        if tx in ("sale", "order"):
            by_order[key]["expected"] += amt
        elif tx == "return":
            by_order[key]["expected"] += amt  # negative amount reduces expected
        elif tx in ("payout", "settlement", "transfer"):
            by_order[key]["actual"] += amt
        elif tx == "fee":
            by_order[key]["fees"] += amt
        elif tx in ("tax", "tds", "tcs", "gst"):
            by_order[key]["taxes"] += amt

    # Build discrepancy list
    issues = []
    for key, o in by_order.items():
        # If we have both expected and actual, compute variance
        if o["expected"] != 0:
            # Actual should equal expected + fees + taxes (fees are usually negative)
            computed_actual = o["expected"] + o["fees"] + o["taxes"]
            reported_actual = o["actual"] if o["actual"] != 0 else computed_actual
            variance = float(reported_actual - computed_actual)
        elif o["actual"] != 0:
            variance = float(o["actual"])
        else:
            continue

        abs_var = abs(variance)
        if abs_var < min_variance:
            continue

        sev = "critical" if abs_var >= 500 else "warning" if abs_var >= 50 else "info"
        if severity and sev != severity:
            continue

        issues.append({
            "order_id":         o["order_id"] or key,
            "sku":              o["sku"],
            "platform":         o["platform"],
            "date":             o["date"],
            "expected_amount":  float(o["expected"]),
            "actual_amount":    float(reported_actual),
            "fees":             float(o["fees"]),
            "taxes":            float(o["taxes"]),
            "variance":         variance,
            "abs_variance":     abs_var,
            "severity":         sev,
            "direction":        "under_paid" if variance < 0 else "over_paid",
        })

    issues.sort(key=lambda x: x["abs_variance"], reverse=True)

    total = len(issues)
    paginated = issues[(page - 1) * limit : page * limit]

    summary = {
        "total_issues":    total,
        "critical_count":  sum(1 for i in issues if i["severity"] == "critical"),
        "warning_count":   sum(1 for i in issues if i["severity"] == "warning"),
        "info_count":      sum(1 for i in issues if i["severity"] == "info"),
        "total_variance":  round(sum(i["variance"] for i in issues), 2),
        "recoverable":     round(sum(i["abs_variance"] for i in issues if i["direction"] == "under_paid"), 2),
    }

    return {
        "file_id":   str(file_id),
        "summary":   summary,
        "total":     total,
        "page":      page,
        "limit":     limit,
        "items":     paginated,
    }


# ── CSV Export ────────────────────────────────────────────────────────────────

@router.get("/files/{file_id}/export", summary="Download ledger as CSV")
async def export_ledger_csv(
    file_id: UUID,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Stream all IngestionLedger records for the file as a CSV download."""
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    rows = (await db.execute(
        select(IngestionLedger)
        .where(IngestionLedger.uploaded_file_id == file_id)
        .order_by(IngestionLedger.source_row_number)
    )).scalars().all()

    def _generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "source_row", "platform", "report_type", "order_id", "shipment_id",
            "settlement_id", "sku", "product_title", "category",
            "transaction_type", "fee_type", "amount", "tax_amount", "currency",
            "transaction_date", "settlement_date", "return_status", "payout_status",
        ])
        yield buf.getvalue()
        buf.truncate(0)
        buf.seek(0)

        for r in rows:
            writer.writerow([
                r.source_row_number, r.platform, r.report_type,
                r.order_id, r.shipment_id, r.settlement_id,
                r.sku, r.product_title, r.category,
                r.transaction_type, r.fee_type,
                float(r.amount) if r.amount is not None else "",
                float(r.tax_amount) if r.tax_amount is not None else "",
                r.currency, r.transaction_date, r.settlement_date,
                r.return_status, r.payout_status,
            ])
            yield buf.getvalue()
            buf.truncate(0)
            buf.seek(0)

    safe_name = (record.original_file_name or "export").replace(" ", "_").split(".")[0]
    filename  = f"{safe_name}_ledger.csv"

    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Intelligence result ───────────────────────────────────────────────────────

@router.get("/files/{file_id}/intelligence", summary="Full 14-agent intelligence pipeline result")
async def get_intelligence(
    file_id: UUID,
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Returns the stored 14-agent intelligence pipeline result for a file.

    The result is stored in ReportDetectionResult.detection_metadata['intelligence']
    after the upload pipeline runs.

    If the intelligence pipeline has not yet run (e.g. older files or still processing),
    returns a 202 with a 'pending' status.
    """
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    if record.upload_status in ("uploaded", "detecting", "processing"):
        return {
            "file_id": str(file_id),
            "status": "pending",
            "message": f"File is still being processed (status: {record.upload_status}). Retry shortly.",
        }

    detection = (await db.execute(
        select(ReportDetectionResult)
        .where(ReportDetectionResult.uploaded_file_id == file_id)
    )).scalar_one_or_none()

    if not detection:
        raise HTTPException(
            status_code=404,
            detail="Detection result not found. File may have failed processing.",
        )

    meta = detection.detection_metadata or {}
    intelligence = meta.get("intelligence")

    if not intelligence:
        # Intelligence pipeline not yet run — trigger it now synchronously
        if record.storage_path and os.path.exists(record.storage_path):
            try:
                with open(record.storage_path, "rb") as fh:
                    file_bytes = fh.read()

                intel_pipeline = IntelligencePipeline()
                intel_result = await intel_pipeline.run(
                    file_bytes=file_bytes,
                    filename=record.original_file_name,
                    upload_id=str(file_id),
                    company_id=str(company_id),
                    db=db,
                    platform_hint=detection.detected_platform,
                    report_type_hint=detection.detected_report_type,
                )
                intelligence = intel_result.model_dump(mode="json")

                # Persist for future calls
                updated_meta = dict(meta)
                updated_meta["intelligence"] = intelligence
                updated_meta["intelligence_summary"] = intel_result.summary
                detection.detection_metadata = updated_meta
                await db.commit()

            except Exception as exc:
                logger.warning("On-demand intelligence pipeline failed for %s: %s", file_id, exc)
                raise HTTPException(
                    status_code=503,
                    detail=f"Intelligence pipeline not available: {exc}",
                )
        else:
            raise HTTPException(
                status_code=404,
                detail="Intelligence data not available for this file (original file not found in storage).",
            )

    return {
        "file_id": str(file_id),
        "status": "ready",
        "intelligence": intelligence,
    }


# ── HTML Report Generator ─────────────────────────────────────────────────────

@router.get("/files/{file_id}/report", summary="Generate premium HTML analytics report")
async def generate_html_report(
    file_id: UUID,
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Generates a premium single-page HTML analytics report from the IngestionLedger.

    Output includes:
    - Executive Summary KPI grid
    - Revenue Waterfall (interactive chart)
    - Product Intelligence (SKU profitability table)
    - Return Intelligence (logistics vs customer returns)
    - Settlement Reconciliation (expected vs actual)
    - Fee Analysis (breakdown with progress bars)
    - Tax Intelligence (TCS/TDS/GST + recovery instructions)
    - Recovery Engine (priority matrix)
    - Risk Dashboard (6-dimension radar)
    - CFO + CA + Investor + Founder Insights
    - Business Health Score (0–100)
    """
    from app.services.analytics_engine import AnalyticsEngine
    from app.services.report_generator import ReportGenerator

    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    if record.upload_status not in ("done", "needs_review"):
        raise HTTPException(
            status_code=409,
            detail=f"File is still processing (status: {record.upload_status}). Retry shortly.",
        )

    rows = (await db.execute(
        select(IngestionLedger)
        .where(IngestionLedger.uploaded_file_id == file_id)
        .order_by(IngestionLedger.source_row_number)
    )).scalars().all()

    if not rows:
        raise HTTPException(status_code=422, detail="No ledger records found for this file.")

    detection = (await db.execute(
        select(ReportDetectionResult)
        .where(ReportDetectionResult.uploaded_file_id == file_id)
    )).scalar_one_or_none()

    file_meta = {
        "id":                 str(record.id),
        "original_file_name": record.original_file_name,
        "uploaded_at":        record.uploaded_at.isoformat(),
    }
    detection_meta = {}
    if detection:
        detection_meta = {
            "detected_platform":    detection.detected_platform or "unknown",
            "detected_report_type": detection.detected_report_type or "",
        }

    try:
        engine  = AnalyticsEngine(rows, file_meta, detection_meta)
        report  = engine.run()
        html    = ReportGenerator(report).generate()
    except Exception as exc:
        logger.exception("Report generation failed for %s: %s", file_id, exc)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")

    safe_name = (record.original_file_name or "report").replace(" ", "_").split(".")[0]
    filename  = f"{safe_name}_clearsettle_report.html"

    return StreamingResponse(
        iter([html.encode("utf-8")]),
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Health-Score": str(report.health_score.total),
            "X-Report-GMV": str(round(report.gross_revenue, 2)),
        },
    )


# ── Delete file ───────────────────────────────────────────────────────────────

@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: UUID,
    db:  AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    company_id = _company_id(user)
    record = await db.get(UploadedFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    _assert_owner(record, company_id)

    # Remove from storage
    if record.storage_path and os.path.exists(record.storage_path):
        try:
            os.remove(record.storage_path)
        except Exception:
            pass

    await db.delete(record)
    await db.commit()
