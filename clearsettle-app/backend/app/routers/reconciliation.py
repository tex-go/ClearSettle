"""
Reconciliation engine API — run engine, browse results, manage rules.

All endpoints require a live DB (no mock-data fallback) and a valid JWT.

Prefix: /reconciliation
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_db
from app.core.rbac import audit_log, require_db_permission
from app.db.models.discrepancy_event import DiscrepancyEvent
from app.db.models.reconciliation_result import ReconciliationResult
from app.db.models.reconciliation_rule import ReconciliationRule
from app.db.models.settlement import Settlement
from app.services.reconciliation import engine as recon_engine
from app.services.reconciliation import storage as recon_storage

logger = logging.getLogger(__name__)
router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _company_id_for(user) -> UUID:
    """Return the first company ID for the authenticated user."""
    if not hasattr(user, "companies") or not user.companies:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No company associated with this account.",
        )
    return user.companies[0].id


def _assert_company_access(user, company_id: UUID) -> None:
    ids = {c.id for c in getattr(user, "companies", [])}
    if company_id not in ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


# ── response schemas ──────────────────────────────────────────────────────────

class DiscrepancyOut(BaseModel):
    id:               UUID
    discrepancy_type: str
    severity:         str
    description:      str
    order_id:         Optional[str]
    fee_type:         Optional[str]
    expected_amount:  Optional[float]
    actual_amount:    Optional[float]
    variance_amount:  Optional[float]
    is_resolved:      bool
    resolved_at:      Optional[datetime]
    transaction_id:   Optional[UUID]
    rule_id:          Optional[UUID]
    metadata:         Optional[dict]
    created_at:       datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_event(cls, e: DiscrepancyEvent) -> "DiscrepancyOut":
        return cls(
            id=e.id,
            discrepancy_type=e.discrepancy_type,
            severity=e.severity,
            description=e.description,
            order_id=e.order_id,
            fee_type=e.fee_type,
            expected_amount=float(e.expected_amount) if e.expected_amount is not None else None,
            actual_amount=float(e.actual_amount) if e.actual_amount is not None else None,
            variance_amount=float(e.variance_amount) if e.variance_amount is not None else None,
            is_resolved=e.is_resolved,
            resolved_at=e.resolved_at,
            transaction_id=e.transaction_id,
            rule_id=e.rule_id,
            metadata=json.loads(e.metadata_json) if e.metadata_json else None,
            created_at=e.created_at,
        )


class ResultSummaryOut(BaseModel):
    id:                   UUID
    settlement_id:        UUID
    platform:             str
    status:               str
    total_discrepancies:  int
    warning_count:        int
    critical_count:       int
    info_count:           int
    total_variance_amount: float
    rules_evaluated:      int
    processing_time_ms:   Optional[int]
    created_at:           datetime


class ResultDetailOut(ResultSummaryOut):
    discrepancies: list[DiscrepancyOut]
    error_message: Optional[str]


class RuleOut(BaseModel):
    id:          UUID
    rule_type:   str
    rule_name:   str
    description: Optional[str]
    severity:    str
    is_active:   bool
    is_global:   bool
    platform:    Optional[str]
    parameters:  dict
    created_at:  datetime


class RuleCreateIn(BaseModel):
    rule_type:       str = Field(..., max_length=100)
    rule_name:       str = Field(..., max_length=255)
    description:     Optional[str] = Field(None, max_length=500)
    severity:        str = Field("warning", pattern="^(info|warning|critical)$")
    platform:        Optional[str] = Field(None, max_length=50)
    parameters_json: Optional[str] = Field(None)
    is_active:       bool = True


class RulePatchIn(BaseModel):
    rule_name:       Optional[str] = Field(None, max_length=255)
    description:     Optional[str] = Field(None, max_length=500)
    severity:        Optional[str] = Field(None, pattern="^(info|warning|critical)$")
    parameters_json: Optional[str] = None
    is_active:       Optional[bool] = None


class RunResponseOut(BaseModel):
    result_id:             UUID
    settlement_id:         UUID
    status:                str
    total_discrepancies:   int
    warning_count:         int
    critical_count:        int
    info_count:            int
    total_variance_amount: float
    rules_evaluated:       int
    processing_time_ms:    int


def _result_summary(r: ReconciliationResult) -> ResultSummaryOut:
    return ResultSummaryOut(
        id=r.id,
        settlement_id=r.settlement_id,
        platform=r.platform,
        status=r.status,
        total_discrepancies=r.total_discrepancies,
        warning_count=r.warning_count,
        critical_count=r.critical_count,
        info_count=r.info_count,
        total_variance_amount=float(r.total_variance_amount or 0),
        rules_evaluated=r.rules_evaluated,
        processing_time_ms=r.processing_time_ms,
        created_at=r.created_at,
    )


# ── POST /reconciliation/run/{settlement_id} ──────────────────────────────────

@router.post("/run/{settlement_id}", response_model=RunResponseOut)
async def run_reconciliation(
    settlement_id: UUID,
    user=Depends(require_db_permission("reconciliation:run")),
    db: AsyncSession = Depends(get_db),
):
    """
    Run the reconciliation engine for a single settlement and persist the result.

    Returns a summary of detected discrepancies.  Re-running creates a new result
    row each time (full audit trail of engine runs).
    """
    company_id = _company_id_for(user)

    run = await recon_engine.run_reconciliation(
        db, settlement_id=settlement_id, company_id=company_id
    )

    if run.status == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=run.error_message or "Reconciliation failed.",
        )

    result = await recon_storage.save_result(db, run)
    await db.commit()

    warning_count  = sum(1 for d in run.discrepancies if d.severity == "warning")
    critical_count = sum(1 for d in run.discrepancies if d.severity == "critical")
    info_count     = sum(1 for d in run.discrepancies if d.severity == "info")

    return RunResponseOut(
        result_id=result.id,
        settlement_id=run.settlement_id,
        status=run.status,
        total_discrepancies=len(run.discrepancies),
        warning_count=warning_count,
        critical_count=critical_count,
        info_count=info_count,
        total_variance_amount=float(run.total_variance_amount),
        rules_evaluated=run.rules_evaluated,
        processing_time_ms=run.processing_time_ms,
    )


# ── POST /reconciliation/run-batch ────────────────────────────────────────────

@router.post("/run-batch")
async def run_reconciliation_batch(
    platform:   str  = Query("amazon"),
    limit:      int  = Query(50, ge=1, le=200),
    force:      bool = Query(False, description="Re-run even if a recent result exists"),
    skip_hours: int  = Query(24, ge=1, le=720, description="Hours to consider 'recent' when force=False"),
    user=Depends(require_db_permission("reconciliation:run")),
    db: AsyncSession = Depends(get_db),
):
    """
    Run the reconciliation engine for settlements belonging to the user's company.

    - `force=False` (default): skips settlements that already have a result
      created within the last `skip_hours` hours.
    - Each settlement is committed in isolation; a failure on one does not
      roll back the others.
    """
    company_id = _company_id_for(user)

    settlements_res = await db.execute(
        select(Settlement)
        .where(
            Settlement.company_id == company_id,
            Settlement.platform   == platform,
        )
        .order_by(Settlement.created_at.desc())
        .limit(limit)
    )
    settlements = settlements_res.scalars().all()

    recent_cutoff = datetime.utcnow() - timedelta(hours=skip_hours)

    summaries = []
    for s in settlements:
        # Skip-if-recent check
        if not force:
            recent_res = await db.execute(
                select(func.count(ReconciliationResult.id))
                .where(
                    ReconciliationResult.settlement_id == s.id,
                    ReconciliationResult.created_at    >= recent_cutoff,
                )
            )
            if (recent_res.scalar_one() or 0) > 0:
                summaries.append({
                    "settlement_id": str(s.id),
                    "external_id":   s.external_id,
                    "status":        "skipped",
                    "reason":        f"Recent result exists (within {skip_hours}h)",
                })
                continue

        # Per-settlement isolation: each gets its own try/commit
        try:
            run = await recon_engine.run_reconciliation(
                db, settlement_id=s.id, company_id=company_id
            )
            if run.status == "error":
                summaries.append({
                    "settlement_id": str(s.id),
                    "external_id":   s.external_id,
                    "status":        "error",
                    "error":         run.error_message,
                })
                continue

            result = await recon_storage.save_result(db, run)
            await db.commit()

            warning_count  = sum(1 for d in run.discrepancies if d.severity == "warning")
            critical_count = sum(1 for d in run.discrepancies if d.severity == "critical")
            info_count     = sum(1 for d in run.discrepancies if d.severity == "info")

            summaries.append({
                "settlement_id":         str(s.id),
                "external_id":           s.external_id,
                "result_id":             str(result.id),
                "status":                run.status,
                "total_discrepancies":   len(run.discrepancies),
                "warning_count":         warning_count,
                "critical_count":        critical_count,
                "info_count":            info_count,
                "total_variance_amount": float(run.total_variance_amount),
                "processing_time_ms":    run.processing_time_ms,
            })
        except Exception as exc:
            await db.rollback()
            logger.exception("run-batch: failed for settlement %s", s.id)
            summaries.append({
                "settlement_id": str(s.id),
                "external_id":   s.external_id,
                "status":        "error",
                "error":         str(exc),
            })

    return {
        "processed":   len(summaries),
        "settlements": summaries,
        "summary": {
            "clean":   sum(1 for s in summaries if s.get("status") == "clean"),
            "warning": sum(1 for s in summaries if s.get("status") == "warning"),
            "critical":sum(1 for s in summaries if s.get("status") == "critical"),
            "skipped": sum(1 for s in summaries if s.get("status") == "skipped"),
            "error":   sum(1 for s in summaries if s.get("status") == "error"),
        },
    }


# ── GET /reconciliation/results ───────────────────────────────────────────────

@router.get("/results", response_model=dict)
async def list_results(
    settlement_id: Optional[UUID]  = Query(None),
    result_status: Optional[str]   = Query(None, alias="status"),
    platform:      str             = Query("amazon"),
    skip:          int             = Query(0, ge=0),
    limit:         int             = Query(20, ge=1, le=100),
    user=Depends(require_db_permission("reconciliation:read")),
    db: AsyncSession = Depends(get_db),
):
    """List reconciliation results for the current user's company."""
    company_id = _company_id_for(user)

    q = (
        select(ReconciliationResult)
        .where(
            ReconciliationResult.company_id == company_id,
            ReconciliationResult.platform   == platform,
        )
        .order_by(ReconciliationResult.created_at.desc())
    )
    if settlement_id:
        q = q.where(ReconciliationResult.settlement_id == settlement_id)
    if result_status:
        q = q.where(ReconciliationResult.status == result_status)

    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar_one()

    items_res = await db.execute(q.offset(skip).limit(limit))
    items = items_res.scalars().all()

    return {
        "total": total,
        "items": [_result_summary(r) for r in items],
    }


# ── GET /reconciliation/results/{result_id} ───────────────────────────────────

@router.get("/results/{result_id}", response_model=ResultDetailOut)
async def get_result(
    result_id: UUID,
    user=Depends(require_db_permission("reconciliation:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a reconciliation result with all its discrepancy events."""
    company_id = _company_id_for(user)

    result = await recon_storage.load_result_with_discrepancies(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found.")

    _assert_company_access(user, result.company_id)

    return ResultDetailOut(
        id=result.id,
        settlement_id=result.settlement_id,
        platform=result.platform,
        status=result.status,
        total_discrepancies=result.total_discrepancies,
        warning_count=result.warning_count,
        critical_count=result.critical_count,
        info_count=result.info_count,
        total_variance_amount=float(result.total_variance_amount or 0),
        rules_evaluated=result.rules_evaluated,
        processing_time_ms=result.processing_time_ms,
        error_message=result.error_message,
        created_at=result.created_at,
        discrepancies=[DiscrepancyOut.from_orm_event(e) for e in result.discrepancies],
    )


# ── GET /reconciliation/discrepancies ─────────────────────────────────────────

@router.get("/discrepancies")
async def list_discrepancies(
    settlement_id:     Optional[UUID] = Query(None),
    discrepancy_type:  Optional[str]  = Query(None),
    severity:          Optional[str]  = Query(None),
    is_resolved:       Optional[bool] = Query(None),
    skip:              int            = Query(0, ge=0),
    limit:             int            = Query(50, ge=1, le=200),
    user=Depends(require_db_permission("reconciliation:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    List discrepancy events across all reconciliation runs for this company.

    Supports filtering by settlement, type, severity, and resolution status.
    """
    company_id = _company_id_for(user)

    q = (
        select(DiscrepancyEvent)
        .where(DiscrepancyEvent.company_id == company_id)
        .order_by(DiscrepancyEvent.created_at.desc())
    )
    if settlement_id:
        q = q.where(DiscrepancyEvent.settlement_id == settlement_id)
    if discrepancy_type:
        q = q.where(DiscrepancyEvent.discrepancy_type == discrepancy_type)
    if severity:
        q = q.where(DiscrepancyEvent.severity == severity)
    if is_resolved is not None:
        q = q.where(DiscrepancyEvent.is_resolved == is_resolved)

    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar_one()

    # Summary aggregates
    agg_res = await db.execute(
        select(
            DiscrepancyEvent.severity,
            func.count(DiscrepancyEvent.id).label("cnt"),
            func.coalesce(func.sum(DiscrepancyEvent.variance_amount), 0).label("variance"),
        )
        .where(
            DiscrepancyEvent.company_id  == company_id,
            DiscrepancyEvent.is_resolved == False,  # noqa: E712
        )
        .group_by(DiscrepancyEvent.severity)
    )
    severity_summary: dict = {"critical": 0, "warning": 0, "info": 0, "total_variance": 0.0}
    for row in agg_res:
        if row.severity in severity_summary:
            severity_summary[row.severity] = row.cnt
        severity_summary["total_variance"] += float(row.variance or 0)

    items_res = await db.execute(q.offset(skip).limit(limit))
    events = items_res.scalars().all()

    return {
        "total":   total,
        "summary": severity_summary,
        "items":   [DiscrepancyOut.from_orm_event(e) for e in events],
    }


# ── PATCH /reconciliation/discrepancies/{event_id}/resolve ────────────────────

@router.patch("/discrepancies/{event_id}/resolve")
async def resolve_discrepancy(
    event_id: UUID,
    user=Depends(require_db_permission("reconciliation:resolve")),
    db: AsyncSession = Depends(get_db),
):
    """Mark a discrepancy event as manually resolved."""
    company_id = _company_id_for(user)

    res = await db.execute(
        select(DiscrepancyEvent).where(DiscrepancyEvent.id == event_id)
    )
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Discrepancy not found.")

    _assert_company_access(user, event.company_id)

    if event.is_resolved:
        return {"message": "Already resolved.", "id": str(event_id)}

    event.is_resolved = True
    event.resolved_at = datetime.utcnow()
    event.resolved_by = user.id
    db.add(event)
    await db.commit()

    return {"message": "Discrepancy resolved.", "id": str(event_id), "resolved_at": event.resolved_at}


# ── GET /reconciliation/rules ─────────────────────────────────────────────────

@router.get("/rules")
async def list_rules(
    include_global: bool = Query(True),
    user=Depends(require_db_permission("reconciliation:rules:read")),
    db: AsyncSession = Depends(get_db),
):
    """List all reconciliation rules (global + company-specific)."""
    company_id = _company_id_for(user)

    conditions = [
        ReconciliationRule.company_id == company_id,
    ]
    if include_global:
        conditions = [
            (ReconciliationRule.company_id == company_id)
            | ReconciliationRule.company_id.is_(None)
        ]

    res = await db.execute(
        select(ReconciliationRule)
        .where(*conditions)
        .order_by(
            ReconciliationRule.company_id.nullsfirst(),
            ReconciliationRule.rule_type,
        )
    )
    rules = res.scalars().all()

    def _rule_out(r: ReconciliationRule) -> dict:
        return {
            "id":          str(r.id),
            "rule_type":   r.rule_type,
            "rule_name":   r.rule_name,
            "description": r.description,
            "severity":    r.severity,
            "is_active":   r.is_active,
            "is_global":   r.company_id is None,
            "platform":    r.platform,
            "parameters":  json.loads(r.parameters_json or "{}"),
            "created_at":  r.created_at.isoformat(),
        }

    return {
        "total": len(rules),
        "items": [_rule_out(r) for r in rules],
    }


# ── POST /reconciliation/rules ────────────────────────────────────────────────

@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: RuleCreateIn,
    user=Depends(require_db_permission("reconciliation:rules:write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a company-specific reconciliation rule."""
    company_id = _company_id_for(user)

    # Validate parameters_json is valid JSON
    params_str = body.parameters_json or "{}"
    try:
        json.loads(params_str)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="parameters_json must be valid JSON.",
        )

    rule = ReconciliationRule(
        company_id=company_id,
        platform=body.platform,
        rule_type=body.rule_type,
        rule_name=body.rule_name,
        description=body.description,
        parameters_json=params_str,
        severity=body.severity,
        is_active=body.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return {
        "id":        str(rule.id),
        "rule_type": rule.rule_type,
        "rule_name": rule.rule_name,
        "severity":  rule.severity,
        "is_active": rule.is_active,
        "is_global": False,
    }


# ── PATCH /reconciliation/rules/{rule_id} ─────────────────────────────────────

@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: UUID,
    body: RulePatchIn,
    user=Depends(require_db_permission("reconciliation:rules:write")),
    db: AsyncSession = Depends(get_db),
):
    """Update a company-specific rule (toggle active, change severity or parameters)."""
    company_id = _company_id_for(user)

    res = await db.execute(
        select(ReconciliationRule).where(ReconciliationRule.id == rule_id)
    )
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")

    # Global rules cannot be mutated — company must create an override
    if rule.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global rules cannot be edited. Create a company-specific rule instead.",
        )

    if rule.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if body.rule_name is not None:
        rule.rule_name = body.rule_name
    if body.description is not None:
        rule.description = body.description
    if body.severity is not None:
        rule.severity = body.severity
    if body.is_active is not None:
        rule.is_active = body.is_active
    if body.parameters_json is not None:
        try:
            json.loads(body.parameters_json)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="parameters_json must be valid JSON.",
            )
        rule.parameters_json = body.parameters_json

    db.add(rule)
    await db.commit()

    return {
        "id":        str(rule.id),
        "rule_type": rule.rule_type,
        "rule_name": rule.rule_name,
        "severity":  rule.severity,
        "is_active": rule.is_active,
        "is_global": False,
    }


# ── GET /reconciliation/summary ───────────────────────────────────────────────

@router.get("/summary")
async def get_summary(
    platform: str = Query("amazon"),
    user=Depends(require_db_permission("reconciliation:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    High-level reconciliation health summary for the company dashboard.

    Returns counts of settlements by reconciliation status and total variance.
    """
    company_id = _company_id_for(user)

    agg_res = await db.execute(
        select(
            ReconciliationResult.status,
            func.count(ReconciliationResult.id).label("cnt"),
            func.coalesce(func.sum(ReconciliationResult.total_variance_amount), 0).label("variance"),
            func.coalesce(func.sum(ReconciliationResult.total_discrepancies), 0).label("discrepancies"),
        )
        .where(
            ReconciliationResult.company_id == company_id,
            ReconciliationResult.platform   == platform,
        )
        .group_by(ReconciliationResult.status)
    )

    by_status: dict = {"clean": 0, "warning": 0, "critical": 0, "error": 0}
    total_variance     = 0.0
    total_discrepancies = 0

    for row in agg_res:
        by_status[row.status] = row.cnt
        total_variance       += float(row.variance or 0)
        total_discrepancies  += int(row.discrepancies or 0)

    total_runs = sum(by_status.values())

    # Unresolved discrepancies
    unresolved_res = await db.execute(
        select(func.count(DiscrepancyEvent.id))
        .where(
            DiscrepancyEvent.company_id  == company_id,
            DiscrepancyEvent.is_resolved == False,  # noqa: E712
        )
    )
    unresolved = unresolved_res.scalar_one() or 0

    return {
        "platform":           platform,
        "total_runs":         total_runs,
        "by_status":          by_status,
        "total_variance":     total_variance,
        "total_discrepancies": total_discrepancies,
        "unresolved_discrepancies": unresolved,
    }


# ── GET /reconciliation/stats ─────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    platform: str = Query("amazon"),
    days:     int = Query(30, ge=1, le=365),
    user=Depends(require_db_permission("reconciliation:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Daily time-series of reconciliation runs for the last N days.

    Returns one entry per (date, status) bucket so the frontend can render
    a stacked-bar or line chart of clean/warning/critical counts over time.
    """
    company_id = _company_id_for(user)
    cutoff = datetime.utcnow() - timedelta(days=days)

    res = await db.execute(
        select(
            func.date(ReconciliationResult.created_at).label("run_date"),
            ReconciliationResult.status,
            func.count(ReconciliationResult.id).label("cnt"),
            func.coalesce(
                func.sum(ReconciliationResult.total_variance_amount), 0
            ).label("variance"),
        )
        .where(
            ReconciliationResult.company_id == company_id,
            ReconciliationResult.platform   == platform,
            ReconciliationResult.created_at >= cutoff,
        )
        .group_by(
            func.date(ReconciliationResult.created_at),
            ReconciliationResult.status,
        )
        .order_by(func.date(ReconciliationResult.created_at))
    )

    by_date: dict[str, dict] = {}
    for row in res:
        d = str(row.run_date)
        if d not in by_date:
            by_date[d] = {
                "date": d, "clean": 0, "warning": 0,
                "critical": 0, "error": 0, "total_variance": 0.0,
            }
        if row.status in by_date[d]:
            by_date[d][row.status] = row.cnt
        by_date[d]["total_variance"] += float(row.variance or 0)

    return {
        "platform": platform,
        "days":     days,
        "data":     list(by_date.values()),
    }


# ── GET /reconciliation/results/{result_id}/log ───────────────────────────────

@router.get("/results/{result_id}/log")
async def get_result_log(
    result_id: UUID,
    user=Depends(require_db_permission("reconciliation:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the per-detector execution log for a reconciliation run.

    The log is stored in reconciliation_results.metadata_json and contains
    each detector's firing count, elapsed time, and any error message.
    """
    company_id = _company_id_for(user)

    res = await db.execute(
        select(
            ReconciliationResult.metadata_json,
            ReconciliationResult.company_id,
            ReconciliationResult.processing_time_ms,
        )
        .where(ReconciliationResult.id == result_id)
    )
    row = res.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Result not found.")

    _assert_company_access(user, row.company_id)

    metadata = json.loads(row.metadata_json or "{}")
    return {
        "result_id":           str(result_id),
        "processing_time_ms":  row.processing_time_ms,
        "loaded_transactions": metadata.get("loaded_transactions", 0),
        "loaded_fees":         metadata.get("loaded_fees", 0),
        "execution_log":       metadata.get("execution_log", []),
    }


# ── POST /reconciliation/test/seed ───────────────────────────────────────────

@router.post("/test/seed")
async def seed_test_settlement(
    run: bool = Query(True, description="Run reconciliation immediately after seeding"),
    user=Depends(require_db_permission("reconciliation:seed")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a synthetic test settlement designed to trigger all 7 detectors.

    Useful for verifying the reconciliation engine end-to-end in a real DB
    without needing actual marketplace data.

    Set `run=false` to only create the settlement without running reconciliation.
    """
    from app.services.reconciliation.seed import generate_test_settlement

    company_id = _company_id_for(user)

    settlement = await generate_test_settlement(db, company_id)
    await db.commit()
    await db.refresh(settlement)

    if not run:
        return {
            "settlement_id": str(settlement.id),
            "external_id":   settlement.external_id,
            "message":       "Settlement created. Run reconciliation manually.",
        }

    run_result = await recon_engine.run_reconciliation(
        db, settlement_id=settlement.id, company_id=company_id
    )

    result_id: UUID | None = None
    if run_result.status != "error":
        saved = await recon_storage.save_result(db, run_result)
        await db.commit()
        result_id = saved.id

    return {
        "settlement_id":            str(settlement.id),
        "external_id":              settlement.external_id,
        "reconciliation_result_id": str(result_id) if result_id else None,
        "status":                   run_result.status,
        "total_discrepancies":      len(run_result.discrepancies),
        "discrepancy_types": sorted({d.discrepancy_type for d in run_result.discrepancies}),
        "processing_time_ms":       run_result.processing_time_ms,
        "error_message":            run_result.error_message,
    }
