"""
Vendor Reconciliation Engine API.

Prefix: /recon-engine

Endpoints:
  POST   /recon-engine/files/upload          — upload a file (multipart/form-data)
  GET    /recon-engine/files                 — list files for company
  DELETE /recon-engine/files/{file_id}       — delete an uploaded file
  POST   /recon-engine/jobs                  — create a reconciliation job
  GET    /recon-engine/jobs                  — list jobs
  GET    /recon-engine/jobs/{job_id}         — job detail + fact summary
  POST   /recon-engine/jobs/{job_id}/run     — trigger engine run (background)
  GET    /recon-engine/jobs/{job_id}/leakage — list leakage events for job
  PATCH  /recon-engine/leakage/{event_id}    — update leakage event status
  GET    /recon-engine/deduction-codes       — list dim_deduction_codes
  GET    /recon-engine/summary               — company-level summary stats
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import date
from typing import Any, Optional
from uuid import UUID

import asyncio
import json as _json_stdlib

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.database import AsyncSessionLocal
from app.db.models.recon_engine import (
    DimDeductionCode, FactReconciliation, LeakageEvent,
    ReconFile, ReconJob, ReconJobFile,
    StgChargebackLine, StgInvoiceLine, StgOperationalLine,
    StgPaymentLine, StgSettlementLine,
)
from app.services.vendor_recon import engine as recon_engine
from app.services.vendor_recon import event_bus as recon_event_bus
from app.services.vendor_recon.ingestion import route_parse

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "/tmp/recon_uploads"


def _company_id(user) -> UUID:
    if not hasattr(user, "companies") or not user.companies:
        raise HTTPException(status_code=422, detail="No company associated with this account.")
    return user.companies[0].id


def _assert_job_owner(job: ReconJob, company_id: UUID) -> None:
    if job.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied.")


# ── schemas ───────────────────────────────────────────────────────────────────

class FileOut(BaseModel):
    id:             str
    filename:       str
    original_name:  str
    file_type:      str
    file_format:    Optional[str]
    file_size_bytes:Optional[int]
    status:         str
    row_count:      Optional[int]
    error_message:  Optional[str]
    created_at:     str
    processed_at:   Optional[str]

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    name:         str
    description:  Optional[str] = None
    period_start: Optional[date] = None
    period_end:   Optional[date] = None
    platform:     Optional[str] = None
    currency:     str = "INR"
    file_ids:     list[str] = []


class JobOut(BaseModel):
    id:               str
    name:             str
    description:      Optional[str]
    period_start:     Optional[date]
    period_end:       Optional[date]
    platform:         Optional[str]
    currency:         str
    status:           str
    expected_payout:  Optional[float]
    actual_payout:    Optional[float]
    variance_amount:  Optional[float]
    variance_pct:     Optional[float]
    total_leakage:    Optional[float]
    leakage_count:    Optional[int]
    disputable_amount:Optional[float]
    summary_json:     Optional[str]
    error_message:    Optional[str]
    created_at:       str
    started_at:       Optional[str]
    completed_at:     Optional[str]


class LeakageOut(BaseModel):
    id:                      str
    leakage_type:            str
    severity:                str
    reference_type:          Optional[str]
    reference_id:            Optional[str]
    po_number:               Optional[str]
    invoice_number:          Optional[str]
    sku:                     Optional[str]
    deduction_code:          Optional[str]
    amount:                  Optional[float]
    description:             str
    root_cause:              Optional[str]
    is_disputable:           bool
    recovery_potential:      Optional[float]
    recovery_recommendation: Optional[str]
    evidence_json:           Optional[str]
    status:                  str
    resolved_by:             Optional[str]
    resolution_note:         Optional[str]
    created_at:              str
    resolved_at:             Optional[str]


class LeakagePatch(BaseModel):
    status:          Optional[str] = None
    resolution_note: Optional[str] = None
    resolved_by:     Optional[str] = None


def _file_out(f: ReconFile) -> dict:
    return {
        "id":              str(f.id),
        "filename":        f.filename,
        "original_name":   f.original_name,
        "file_type":       f.file_type,
        "file_format":     f.file_format,
        "file_size_bytes": f.file_size_bytes,
        "status":          f.status,
        "row_count":       f.row_count,
        "error_message":   f.error_message,
        "created_at":      f.created_at.isoformat() if f.created_at else "",
        "processed_at":    f.processed_at.isoformat() if f.processed_at else None,
    }


def _job_out(j: ReconJob) -> dict:
    return {
        "id":               str(j.id),
        "name":             j.name,
        "description":      j.description,
        "period_start":     j.period_start.isoformat() if j.period_start else None,
        "period_end":       j.period_end.isoformat() if j.period_end else None,
        "platform":         j.platform,
        "currency":         j.currency,
        "status":           j.status,
        "expected_payout":  float(j.expected_payout)   if j.expected_payout   is not None else None,
        "actual_payout":    float(j.actual_payout)     if j.actual_payout     is not None else None,
        "variance_amount":  float(j.variance_amount)   if j.variance_amount   is not None else None,
        "variance_pct":     float(j.variance_pct)      if j.variance_pct      is not None else None,
        "total_leakage":    float(j.total_leakage)     if j.total_leakage     is not None else None,
        "leakage_count":    j.leakage_count,
        "disputable_amount":float(j.disputable_amount) if j.disputable_amount is not None else None,
        "summary_json":     j.summary_json,
        "error_message":    j.error_message,
        "created_at":       j.created_at.isoformat() if j.created_at else "",
        "started_at":       j.started_at.isoformat() if j.started_at else None,
        "completed_at":     j.completed_at.isoformat() if j.completed_at else None,
    }


def _leakage_out(e: LeakageEvent) -> dict:
    return {
        "id":                      str(e.id),
        "leakage_type":            e.leakage_type,
        "severity":                e.severity,
        "reference_type":          e.reference_type,
        "reference_id":            e.reference_id,
        "po_number":               e.po_number,
        "invoice_number":          e.invoice_number,
        "sku":                     e.sku,
        "deduction_code":          e.deduction_code,
        "amount":                  float(e.amount) if e.amount is not None else None,
        "description":             e.description,
        "root_cause":              e.root_cause,
        "is_disputable":           e.is_disputable,
        "recovery_potential":      float(e.recovery_potential) if e.recovery_potential is not None else None,
        "recovery_recommendation": e.recovery_recommendation,
        "evidence_json":           e.evidence_json,
        "status":                  e.status,
        "resolved_by":             e.resolved_by,
        "resolution_note":         e.resolution_note,
        "created_at":              e.created_at.isoformat() if e.created_at else "",
        "resolved_at":             e.resolved_at.isoformat() if e.resolved_at else None,
    }


# ── file endpoints ────────────────────────────────────────────────────────────

@router.post("/files/upload")
async def upload_file(
    file:      UploadFile = File(...),
    file_type: str        = Form(...),
    db: AsyncSession      = Depends(get_db),
    user                  = Depends(get_current_user),
):
    company_id = _company_id(user)
    content    = await file.read()
    fmt        = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else None

    # Parse immediately to get row count and validate
    try:
        _table, rows, row_count = route_parse(content, file.filename or "upload", fmt, file_type)
        parse_error = None
        parse_status = "processed"
    except Exception as exc:
        rows, row_count, parse_error = [], 0, str(exc)
        parse_status = "failed"
        _table = "settlement"

    # Store file metadata
    rec = ReconFile(
        company_id      = company_id,
        filename        = f"{uuid.uuid4()}.{fmt or 'csv'}",
        original_name   = file.filename or "upload",
        file_type       = file_type,
        file_format     = fmt,
        file_size_bytes = len(content),
        status          = parse_status,
        row_count       = row_count,
        error_message   = parse_error,
    )
    db.add(rec)
    await db.flush()   # get rec.id

    # Store parsed rows in staging — they need a job_id, so we store raw
    # in the file record as column_map_json for now; rows are re-staged when a job runs.
    # To enable pre-job preview, we store a small sample in column_map_json.
    sample = rows[:5] if rows else []
    rec.column_map_json = json.dumps({
        "sample_rows": sample,
        "columns":     list(sample[0].keys()) if sample else [],
        "raw_content_b64": None,  # don't store full content in DB
    })

    # Save file to disk for re-use when job runs
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, rec.filename)
    with open(file_path, "wb") as fh:
        fh.write(content)

    await db.commit()
    return _file_out(rec)


@router.get("/files")
async def list_files(
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    company_id = _company_id(user)
    rows = (await db.execute(
        select(ReconFile)
        .where(ReconFile.company_id == company_id)
        .order_by(ReconFile.created_at.desc())
    )).scalars().all()
    return {"items": [_file_out(r) for r in rows]}


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    company_id = _company_id(user)
    rec = (await db.execute(
        select(ReconFile).where(ReconFile.id == UUID(file_id), ReconFile.company_id == company_id)
    )).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    fpath = os.path.join(UPLOAD_DIR, rec.filename)
    if os.path.exists(fpath):
        os.remove(fpath)
    await db.delete(rec)
    await db.commit()


# ── job endpoints ─────────────────────────────────────────────────────────────

@router.post("/jobs", status_code=201)
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    company_id = _company_id(user)
    job = ReconJob(
        company_id   = company_id,
        name         = body.name,
        description  = body.description,
        period_start = body.period_start,
        period_end   = body.period_end,
        platform     = body.platform,
        currency     = body.currency,
        status       = "draft",
    )
    db.add(job)
    await db.flush()

    # Link files
    for fid in body.file_ids:
        file_rec = (await db.execute(
            select(ReconFile).where(ReconFile.id == UUID(fid), ReconFile.company_id == company_id)
        )).scalar_one_or_none()
        if file_rec:
            jf = ReconJobFile(job_id=job.id, file_id=file_rec.id, file_role=file_rec.file_type)
            db.add(jf)

    await db.commit()
    return _job_out(job)


@router.get("/jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
):
    company_id = _company_id(user)
    q = select(ReconJob).where(ReconJob.company_id == company_id)
    if status_filter:
        q = q.where(ReconJob.status == status_filter)
    q = q.order_by(ReconJob.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [_job_out(r) for r in rows], "total": len(rows)}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    company_id = _company_id(user)
    job = (await db.execute(
        select(ReconJob).where(ReconJob.id == UUID(job_id))
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _assert_job_owner(job, company_id)

    # Include fact if available
    fact = (await db.execute(
        select(FactReconciliation).where(FactReconciliation.job_id == job.id)
    )).scalar_one_or_none()

    out = _job_out(job)
    if fact:
        out["fact"] = {
            "total_invoice_value":    float(fact.total_invoice_value or 0),
            "total_agreed_discounts": float(fact.total_agreed_discounts or 0),
            "total_valid_returns":    float(fact.total_valid_returns or 0),
            "total_approved_coop":    float(fact.total_approved_coop or 0),
            "total_valid_tax_adj":    float(fact.total_valid_tax_adj or 0),
            "expected_payout":        float(fact.expected_payout or 0),
            "actual_payout":          float(fact.actual_payout or 0),
            "variance_amount":        float(fact.variance_amount or 0),
            "variance_pct":           float(fact.variance_pct or 0),
            "total_deductions":       float(fact.total_deductions or 0),
            "valid_deductions":       float(fact.valid_deductions or 0),
            "suspicious_deductions":  float(fact.suspicious_deductions or 0),
            "duplicate_deductions":   float(fact.duplicate_deductions or 0),
            "disputable_amount":      float(fact.disputable_amount or 0),
            "unrecovered_claims":     float(fact.unrecovered_claims or 0),
            "total_leakage":          float(fact.total_leakage or 0),
            "leakage_by_type":        json.loads(fact.leakage_by_type_json or "{}"),
        }

    # Include linked files
    job_files = (await db.execute(
        select(ReconJobFile, ReconFile)
        .join(ReconFile, ReconJobFile.file_id == ReconFile.id)
        .where(ReconJobFile.job_id == job.id)
    )).all()
    out["files"] = [_file_out(f) for _, f in job_files]

    return out


async def _stage_and_run(job_id: UUID, db: AsyncSession) -> None:
    """Background task: re-parse files → stage rows → run engine."""
    from datetime import datetime

    job_files = (await db.execute(
        select(ReconJobFile, ReconFile)
        .join(ReconFile, ReconJobFile.file_id == ReconFile.id)
        .where(ReconJobFile.job_id == job_id)
    )).all()

    for jf, file_rec in job_files:
        file_path = os.path.join(UPLOAD_DIR, file_rec.filename)
        if not os.path.exists(file_path):
            continue
        with open(file_path, "rb") as fh:
            content = fh.read()

        try:
            table_name, rows, _ = route_parse(
                content, file_rec.original_name, file_rec.file_format, file_rec.file_type
            )
        except Exception as exc:
            logger.warning("Failed to parse file %s: %s", file_rec.id, exc)
            continue

        # Insert into appropriate staging table
        for row in rows:
            row["job_id"]  = job_id
            row["file_id"] = file_rec.id
            if table_name == "settlement":
                db.add(StgSettlementLine(**row))
            elif table_name == "invoice":
                db.add(StgInvoiceLine(**row))
            elif table_name == "chargeback":
                db.add(StgChargebackLine(**row))
            elif table_name == "payment":
                db.add(StgPaymentLine(**row))
            elif table_name == "operational":
                db.add(StgOperationalLine(**row))

    await db.commit()
    await recon_engine.run_job(job_id, db)


async def _run_job_background(job_id: UUID) -> None:
    """Background coroutine: opens its own DB session so it survives after the HTTP request closes."""
    if AsyncSessionLocal is None:
        logger.error("AsyncSessionLocal not initialised — cannot run job %s", job_id)
        return
    async with AsyncSessionLocal() as db:
        try:
            await _stage_and_run(job_id, db)
        except Exception as exc:
            logger.exception("Background job %s failed: %s", job_id, exc)


@router.post("/jobs/{job_id}/run")
async def run_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    """Queue the job for execution and return immediately.

    The job runs as a FastAPI background task with its own DB session.
    Clients should open the SSE stream (/jobs/{job_id}/events) to
    receive real-time progress events.
    """
    company_id = _company_id(user)
    job = (await db.execute(
        select(ReconJob).where(ReconJob.id == UUID(job_id))
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _assert_job_owner(job, company_id)

    if job.status in ("running", "queued"):
        raise HTTPException(status_code=409, detail="Job is already running")

    job.status = "queued"
    await db.commit()

    background_tasks.add_task(_run_job_background, UUID(job_id))
    return {"status": "queued", "job_id": job_id}


@router.get("/jobs/{job_id}/events")
async def job_event_stream(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    """SSE stream of reconciliation engine events for a job.

    Emits: stage start/complete events, per-detector results, terminal completed/failed.
    Late-connecting clients receive a history replay of all events emitted so far.

    Authentication: standard Bearer token via Authorization header.
    """
    company_id = _company_id(user)
    job = (await db.execute(
        select(ReconJob).where(ReconJob.id == UUID(job_id))
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _assert_job_owner(job, company_id)

    job_status = job.status
    # Close the DB session before entering the long-lived generator
    await db.close()

    async def _event_generator():
        # Immediate keepalive so nginx/proxies don't close the connection
        yield ": ping\n\n"

        # If the job is already in a terminal state, send a synthetic event and close
        if job_status in ("completed", "failed"):
            payload = _json_stdlib.dumps({"type": job_status, "message": f"Job already {job_status}"})
            yield f"data: {payload}\n\n"
            yield "data: {\"type\": \"stream_end\"}\n\n"
            return

        q, history = recon_event_bus.subscribe(job_id)
        try:
            # Replay buffered history so late-connecting clients catch up
            for evt in history:
                yield f"data: {_json_stdlib.dumps(evt)}\n\n"

            # Stream live events
            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Keepalive comment — prevents proxy timeouts
                    yield ": keepalive\n\n"
                    continue

                if recon_event_bus.is_done(item):
                    yield "data: {\"type\": \"stream_end\"}\n\n"
                    break

                yield f"data: {_json_stdlib.dumps(item)}\n\n"
        finally:
            recon_event_bus.unsubscribe(job_id, q)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx response buffering
            "Connection":        "keep-alive",
        },
    )


# ── leakage endpoints ─────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/leakage")
async def list_leakage(
    job_id: str,
    db: AsyncSession         = Depends(get_db),
    user                     = Depends(get_current_user),
    leakage_type: Optional[str] = Query(default=None),
    severity: Optional[str]     = Query(default=None),
    event_status: Optional[str] = Query(default=None, alias="status"),
    is_disputable: Optional[bool]= Query(default=None),
    limit: int  = Query(default=50, le=200),
    offset: int = Query(default=0),
):
    company_id = _company_id(user)
    job = (await db.execute(select(ReconJob).where(ReconJob.id == UUID(job_id)))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _assert_job_owner(job, company_id)

    q = select(LeakageEvent).where(LeakageEvent.job_id == UUID(job_id))
    if leakage_type:
        q = q.where(LeakageEvent.leakage_type == leakage_type.upper())
    if severity:
        q = q.where(LeakageEvent.severity == severity)
    if event_status:
        q = q.where(LeakageEvent.status == event_status)
    if is_disputable is not None:
        q = q.where(LeakageEvent.is_disputable == is_disputable)
    q = q.order_by(LeakageEvent.created_at.desc()).limit(limit).offset(offset)

    rows = (await db.execute(q)).scalars().all()
    total_amt = sum(float(r.amount or 0) for r in rows)
    return {
        "items":       [_leakage_out(r) for r in rows],
        "total_count": len(rows),
        "total_amount": total_amt,
    }


@router.patch("/leakage/{event_id}")
async def update_leakage(
    event_id: str,
    body: LeakagePatch,
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    from datetime import datetime
    company_id = _company_id(user)
    ev = (await db.execute(select(LeakageEvent).where(LeakageEvent.id == UUID(event_id)))).scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Leakage event not found")

    # Verify job ownership
    job = (await db.execute(select(ReconJob).where(ReconJob.id == ev.job_id))).scalar_one_or_none()
    if not job or job.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if body.status:
        ev.status = body.status
        if body.status in ("resolved", "waived", "disputed"):
            ev.resolved_at = datetime.utcnow()
    if body.resolution_note:
        ev.resolution_note = body.resolution_note
    if body.resolved_by:
        ev.resolved_by = body.resolved_by

    await db.commit()
    return _leakage_out(ev)


# ── deduction codes ───────────────────────────────────────────────────────────

@router.get("/deduction-codes")
async def list_deduction_codes(
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    rows = (await db.execute(
        select(DimDeductionCode).order_by(DimDeductionCode.category, DimDeductionCode.code)
    )).scalars().all()
    return {"items": [
        {
            "id":                 r.id,
            "code":               r.code,
            "name":               r.name,
            "category":           r.category,
            "is_dispute_allowed": r.is_dispute_allowed,
            "severity_level":     r.severity_level,
            "description":        r.description,
            "platform":           r.platform,
        }
        for r in rows
    ]}


# ── summary ───────────────────────────────────────────────────────────────────

@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    user             = Depends(get_current_user),
):
    company_id = _company_id(user)

    total_jobs = (await db.execute(
        select(func.count()).where(ReconJob.company_id == company_id)
    )).scalar() or 0

    completed = (await db.execute(
        select(func.count()).where(ReconJob.company_id == company_id, ReconJob.status == "completed")
    )).scalar() or 0

    total_leakage = (await db.execute(
        select(func.sum(ReconJob.total_leakage))
        .where(ReconJob.company_id == company_id, ReconJob.status == "completed")
    )).scalar() or 0

    total_disputable = (await db.execute(
        select(func.sum(ReconJob.disputable_amount))
        .where(ReconJob.company_id == company_id, ReconJob.status == "completed")
    )).scalar() or 0

    open_events = (await db.execute(
        select(func.count(LeakageEvent.id))
        .join(ReconJob, LeakageEvent.job_id == ReconJob.id)
        .where(ReconJob.company_id == company_id, LeakageEvent.status == "open")
    )).scalar() or 0

    total_files = (await db.execute(
        select(func.count()).where(ReconFile.company_id == company_id)
    )).scalar() or 0

    return {
        "total_jobs":       total_jobs,
        "completed_jobs":   completed,
        "total_leakage":    float(total_leakage),
        "total_disputable": float(total_disputable),
        "open_events":      open_events,
        "total_files":      total_files,
    }
