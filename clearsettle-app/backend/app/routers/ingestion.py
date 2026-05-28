"""
Intelligent Report Ingestion Engine — API Router.

Prefix: /ingestion

Endpoints:
  POST   /ingestion/upload                  — upload any marketplace report (auto-detect)
  GET    /ingestion/files                   — list uploaded files with detection status
  GET    /ingestion/files/{id}              — single file metadata
  GET    /ingestion/files/{id}/detection    — detection result + confidence + signals
  GET    /ingestion/files/{id}/logs         — processing audit trail
  GET    /ingestion/files/{id}/ledger       — normalized ledger records (paginated)
  POST   /ingestion/files/{id}/reprocess    — re-run pipeline (e.g. after schema update)
  POST   /ingestion/files/{id}/manual-review — admin override: set platform/type/parser
  GET    /ingestion/schema-drifts           — list files with schema drift alerts
  DELETE /ingestion/files/{id}              — delete file + all derived data
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
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.database import AsyncSessionLocal
from app.db.models.ingestion import (
    UploadedFile, ReportDetectionResult,
    ReportProcessingLog, IngestionLedger,
)

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "/tmp/ingestion_uploads"
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
) -> None:
    """Full ingestion pipeline: detect → parse → persist."""
    if AsyncSessionLocal is None:
        return

    async with AsyncSessionLocal() as db:
        record = await db.get(UploadedFile, uploaded_file_id)
        if not record:
            return

        try:
            record.upload_status = "detecting"
            await db.commit()

            # ── Run pipeline ──────────────────────────────────────────────────
            from app.services.pipeline.router import run_ingestion_pipeline
            pipeline_result, parse_result = run_ingestion_pipeline(
                file_bytes, file_name, uploaded_file_id
            )

            # ── Persist detection result ──────────────────────────────────────
            detection = ReportDetectionResult(
                id=uuid.uuid4(),
                uploaded_file_id=uploaded_file_id,
                detected_platform=pipeline_result.platform,
                detected_report_type=pipeline_result.report_type,
                schema_version=pipeline_result.schema_version,
                confidence_score=Decimal(str(pipeline_result.confidence_score)),
                detection_metadata=pipeline_result.detection_metadata,
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
            logger.info(
                "Ingestion complete for file %s: platform=%s type=%s ledger=%d status=%s",
                uploaded_file_id, pipeline_result.platform, pipeline_result.report_type,
                pipeline_result.ledger_count, final_status,
            )

        except Exception as exc:
            logger.exception("Ingestion pipeline failed for file %s", uploaded_file_id)
            try:
                record.upload_status = "failed"
                record.error_message = str(exc)[:500]
                await db.commit()
            except Exception:
                pass


# ── Upload endpoint ───────────────────────────────────────────────────────────

@router.post("/upload", status_code=202)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db:   AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Upload any marketplace report.

    The system automatically:
    1. Fingerprints the file (extracts sheets, headers, column signatures)
    2. Detects the platform (Flipkart / Amazon / Meesho) with confidence score
    3. Detects report type (P&L / Payment / Settlement / Tax / Returns)
    4. Detects schema version and flags drift if schema changed
    5. Routes to the correct parser
    6. Normalises into the unified ingestion ledger
    7. Runs reconciliation and detects anomalies

    Returns immediately (202) with file_id + confidence preview.
    Processing happens in background — poll GET /ingestion/files/{id} for status.
    """
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
    )

    return {
        "id":             str(record.id),
        "original_file_name": record.original_file_name,
        "file_size_bytes": len(file_bytes),
        "upload_status":  "uploaded",
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

    return _detection_to_dict(detection)


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
