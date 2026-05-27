"""
Vendor Reconciliation Engine — orchestrates ETL + leakage detection + fact computation.

Call run_job(job_id, db) to execute a full reconciliation cycle:
  1. Load staged data for the job              [event: ingestion]
  2. Run all 10 leakage detectors              [event: leakage_detection × 10]
  3. Compute expected vs actual payout         [event: recovery_analysis]
  4. Write leakage_events + fact + update job  [event: report → completed]

Every meaningful stage transition emits a structured event via event_bus.emit()
so SSE clients can render live progress without polling.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recon_engine import (
    FactReconciliation, LeakageEvent, ReconJob,
    StgChargebackLine, StgInvoiceLine, StgOperationalLine,
    StgPaymentLine, StgSettlementLine,
)
from app.services.vendor_recon import event_bus
from app.services.vendor_recon.detectors import (
    LeakageCandidate,
    detect_accrual_mismatch,
    detect_coop,
    detect_damage,
    detect_dispute_recovery_failure,
    detect_duplicates,
    detect_otif,
    detect_return_leakage,
    detect_shortage,
    detect_tax_mismatch,
    detect_timing,
)

logger = logging.getLogger(__name__)
_ZERO = Decimal("0")

# ── Detector registry — ordered list of (event_key, display_label, fn, *args_keys) ──
# args_keys maps to staged dict keys; filled at runtime.
_DETECTORS = [
    ("SHORT",            "Shortage Claims",         detect_shortage,                  ["settlement", "operational"]),
    ("DUPLICATE",        "Duplicate Deductions",     detect_duplicates,                ["settlement"]),
    ("OTIF",             "OTIF Penalties",           detect_otif,                      ["operational"]),
    ("ACCRUAL",          "Accrual Mismatches",       detect_accrual_mismatch,          ["settlement"]),
    ("COOP",             "Unauthorized Co-Op",       detect_coop,                      ["settlement", "chargeback"]),
    ("RETURN",           "Return Leakage",           detect_return_leakage,            ["settlement", "operational"]),
    ("DAMAGE",           "Damage Overstatement",     detect_damage,                    ["settlement", "operational"]),
    ("TIMING",           "Payment Timing",           detect_timing,                    ["invoice", "payment"]),
    ("TAX",              "Tax Mismatch",             detect_tax_mismatch,              ["settlement", "invoice"]),
    ("DISPUTE_RECOVERY", "Unrecovered Disputes",     detect_dispute_recovery_failure,  ["chargeback", "operational"]),
]


async def _load_staged(job_id: UUID, db: AsyncSession) -> dict:
    """Load all staging rows for a job in one pass."""
    sl = (await db.execute(select(StgSettlementLine).where(StgSettlementLine.job_id == job_id))).scalars().all()
    il = (await db.execute(select(StgInvoiceLine).where(StgInvoiceLine.job_id == job_id))).scalars().all()
    cl = (await db.execute(select(StgChargebackLine).where(StgChargebackLine.job_id == job_id))).scalars().all()
    pl = (await db.execute(select(StgPaymentLine).where(StgPaymentLine.job_id == job_id))).scalars().all()
    ol = (await db.execute(select(StgOperationalLine).where(StgOperationalLine.job_id == job_id))).scalars().all()
    return {"settlement": sl, "invoice": il, "chargeback": cl, "payment": pl, "operational": ol}


def _compute_expected_payout(staged: dict) -> dict[str, Decimal]:
    invoice_total = sum(
        Decimal(str(r.invoice_total)) for r in staged["invoice"] if r.invoice_total
    ) or _ZERO
    discounts = sum(
        Decimal(str(r.discount_amount)) for r in staged["invoice"] if r.discount_amount
    ) or _ZERO
    valid_returns = sum(
        Decimal(str(r.amount)) for r in staged["operational"]
        if r.line_category == "return" and r.amount
    ) or _ZERO
    approved_coop = sum(
        Decimal(str(r.deduction_amount)) for r in staged["chargeback"]
        if r.deduction_amount and r.dispute_status and
           r.dispute_status.lower() in ("approved", "agreed", "recovered")
    ) or _ZERO
    valid_tax_adj = sum(
        Decimal(str(r.tax_amount)) for r in staged["invoice"] if r.tax_amount
    ) or _ZERO
    expected = invoice_total - discounts - valid_returns - approved_coop
    return {
        "total_invoice_value":    invoice_total,
        "total_agreed_discounts": discounts,
        "total_valid_returns":    valid_returns,
        "total_approved_coop":    approved_coop,
        "total_valid_tax_adj":    valid_tax_adj,
        "expected_payout":        expected,
    }


def _compute_actual_payout(staged: dict) -> Decimal:
    return sum(
        Decimal(str(r.paid_amount)) for r in staged["payment"] if r.paid_amount
    ) or _ZERO


def _compute_deduction_summary(staged: dict) -> dict[str, Decimal]:
    total_deductions = sum(
        Decimal(str(r.deduction_amount)) for r in staged["settlement"]
        if r.deduction_amount and Decimal(str(r.deduction_amount)) > _ZERO
    ) or _ZERO
    valid_deductions = sum(
        Decimal(str(r.deduction_amount)) for r in staged["chargeback"]
        if r.deduction_amount and r.dispute_status and
           r.dispute_status.lower() in ("approved", "agreed", "waived")
    ) or _ZERO
    return {"total_deductions": total_deductions, "valid_deductions": valid_deductions}


async def run_job(job_id: UUID, db: AsyncSession) -> ReconJob:
    """Execute the full reconciliation cycle for a job.

    Emits structured events to event_bus at every stage so SSE clients
    can render live pipeline progress.
    """
    jid = str(job_id)

    job = (await db.execute(select(ReconJob).where(ReconJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise ValueError(f"ReconJob {job_id} not found")

    job.status     = "running"
    job.started_at = datetime.utcnow()
    await db.commit()

    try:
        # ── STAGE: ingestion ─────────────────────────────────────────────────
        await event_bus.emit(jid, {
            "stage": "ingestion", "status": "started",
            "message": "Loading staged documents from database",
        })

        staged = await _load_staged(job_id, db)

        row_counts = {k: len(v) for k, v in staged.items()}
        total_rows = sum(row_counts.values())

        await event_bus.emit(jid, {
            "stage": "ingestion", "status": "completed",
            "total_rows": total_rows,
            "row_counts": row_counts,
            "message": f"Loaded {total_rows:,} rows across {len([v for v in row_counts.values() if v])} document types",
        })

        # ── STAGE: normalization (data integrity scan) ────────────────────────
        await event_bus.emit(jid, {
            "stage": "normalization", "status": "started",
            "message": "Scanning for structural anomalies and null fields",
        })

        # Count rows with key fields populated — real data quality metric
        settlement_with_amounts = sum(1 for r in staged["settlement"] if r.deduction_amount)
        invoice_with_totals     = sum(1 for r in staged["invoice"]     if r.invoice_total)

        await event_bus.emit(jid, {
            "stage": "normalization", "status": "completed",
            "settlement_coverage": settlement_with_amounts,
            "invoice_coverage":    invoice_with_totals,
            "message": f"{settlement_with_amounts} settlement lines with amounts, {invoice_with_totals} invoices with totals",
        })

        # ── STAGE: entity_resolution (cross-table link inspection) ───────────
        await event_bus.emit(jid, {
            "stage": "entity_resolution", "status": "started",
            "message": "Resolving PO → Invoice → Shipment → Settlement links",
        })

        # Real entity resolution: count POs that appear across tables
        settlement_pos = {r.po_number for r in staged["settlement"] if r.po_number}
        invoice_pos    = {r.po_number for r in staged["invoice"]    if r.po_number}
        chargeback_pos = {r.po_number for r in staged["chargeback"] if r.po_number}
        matched_pos    = settlement_pos & invoice_pos
        unmatched_pos  = settlement_pos - invoice_pos

        await event_bus.emit(jid, {
            "stage": "entity_resolution", "status": "completed",
            "settlement_pos":  len(settlement_pos),
            "invoice_pos":     len(invoice_pos),
            "matched_pos":     len(matched_pos),
            "unmatched_pos":   len(unmatched_pos),
            "chargeback_pos":  len(chargeback_pos),
            "message": f"{len(matched_pos)} POs matched across settlement + invoice; {len(unmatched_pos)} unresolved",
        })

        # ── STAGE: leakage_detection ─────────────────────────────────────────
        await event_bus.emit(jid, {
            "stage": "leakage_detection", "status": "started",
            "total_detectors": len(_DETECTORS),
            "message": f"Running {len(_DETECTORS)} leakage detectors",
        })

        candidates: list[LeakageCandidate] = []
        detector_summary: dict[str, int] = {}
        running_leakage = _ZERO

        for idx, (key, label, fn, arg_keys) in enumerate(_DETECTORS):
            await event_bus.emit(jid, {
                "stage": "leakage_detection", "status": "detector_running",
                "detector": key, "detector_label": label,
                "detector_index": idx,
                "message": f"Running detector: {label}",
            })

            results = fn(*[staged[k] for k in arg_keys])
            detector_summary[key] = len(results)
            candidates.extend(results)
            found_amount = sum(float(c.amount or 0) for c in results)
            running_leakage += Decimal(str(found_amount))

            await event_bus.emit(jid, {
                "stage": "leakage_detection", "status": "detector_completed",
                "detector": key, "detector_label": label,
                "detector_index": idx,
                "found": len(results),
                "amount": found_amount,
                "running_total": float(running_leakage),
                "message": (
                    f"{label}: {len(results)} events · ₹{found_amount:,.0f}"
                    if results else
                    f"{label}: no leakage found"
                ),
            })

        await event_bus.emit(jid, {
            "stage": "leakage_detection", "status": "completed",
            "total_found": len(candidates),
            "total_amount": float(running_leakage),
            "detector_summary": detector_summary,
            "message": f"Detection complete — {len(candidates)} leakage events, ₹{float(running_leakage):,.0f} total",
        })

        # ── STAGE: recovery_analysis ─────────────────────────────────────────
        await event_bus.emit(jid, {
            "stage": "recovery_analysis", "status": "started",
            "message": "Computing expected payout and disputable amounts",
        })

        payout_components = _compute_expected_payout(staged)
        actual_payout     = _compute_actual_payout(staged)
        ded_summary       = _compute_deduction_summary(staged)
        expected_payout   = payout_components["expected_payout"]
        variance          = expected_payout - actual_payout
        variance_pct      = (variance / expected_payout * 100) if expected_payout else _ZERO

        disputable_amt = _ZERO
        total_leakage  = _ZERO
        dup_ded_amt    = _ZERO
        suspicious_amt = _ZERO
        recovery_total = _ZERO

        for c in candidates:
            amt = c.amount or _ZERO
            total_leakage += amt
            if c.is_disputable:
                disputable_amt += amt
            if c.leakage_type == "DUPLICATE":
                dup_ded_amt += amt
            if c.leakage_type in ("SHORT", "COOP", "RETURN", "DAMAGE", "DISPUTE_RECOVERY"):
                suspicious_amt += amt
            if c.recovery_potential:
                recovery_total += Decimal(str(c.recovery_potential))

        await event_bus.emit(jid, {
            "stage": "recovery_analysis", "status": "completed",
            "expected_payout":  float(expected_payout),
            "actual_payout":    float(actual_payout),
            "variance":         float(variance),
            "variance_pct":     float(variance_pct),
            "total_leakage":    float(total_leakage),
            "disputable":       float(disputable_amt),
            "recovery_total":   float(recovery_total),
            "message": f"Expected ₹{float(expected_payout):,.0f} · Actual ₹{float(actual_payout):,.0f} · Variance ₹{float(variance):,.0f}",
        })

        # ── STAGE: report (write to DB) ──────────────────────────────────────
        await event_bus.emit(jid, {
            "stage": "report", "status": "started",
            "message": f"Persisting {len(candidates)} leakage events and reconciliation fact",
        })

        leakage_by_type: dict[str, float] = {}
        for c in candidates:
            ev = LeakageEvent(
                job_id                  = job_id,
                leakage_type            = c.leakage_type,
                severity                = c.severity,
                reference_type          = c.reference_type,
                reference_id            = c.reference_id,
                po_number               = c.po_number,
                invoice_number          = c.invoice_number,
                sku                     = c.sku,
                deduction_code          = c.deduction_code,
                amount                  = c.amount,
                description             = c.description,
                root_cause              = c.root_cause,
                is_disputable           = c.is_disputable,
                recovery_potential      = c.recovery_potential,
                recovery_recommendation = c.recovery_recommendation,
                evidence_json           = json.dumps(c.evidence),
                status                  = "open",
            )
            db.add(ev)
            t = c.leakage_type
            leakage_by_type[t] = leakage_by_type.get(t, 0.0) + float(c.amount or 0)

        existing_fact = (
            await db.execute(select(FactReconciliation).where(FactReconciliation.job_id == job_id))
        ).scalar_one_or_none()
        fact = existing_fact or FactReconciliation(job_id=job_id)
        if not existing_fact:
            db.add(fact)

        fact.total_invoice_value    = payout_components["total_invoice_value"]
        fact.total_agreed_discounts = payout_components["total_agreed_discounts"]
        fact.total_valid_returns    = payout_components["total_valid_returns"]
        fact.total_approved_coop    = payout_components["total_approved_coop"]
        fact.total_valid_tax_adj    = payout_components["total_valid_tax_adj"]
        fact.expected_payout        = expected_payout
        fact.actual_payout          = actual_payout
        fact.variance_amount        = variance
        fact.variance_pct           = variance_pct
        fact.total_deductions       = ded_summary["total_deductions"]
        fact.valid_deductions       = ded_summary["valid_deductions"]
        fact.suspicious_deductions  = suspicious_amt
        fact.duplicate_deductions   = dup_ded_amt
        fact.disputable_amount      = disputable_amt
        fact.unrecovered_claims     = sum(
            Decimal(str(c.recovery_potential or 0)) for c in candidates
            if c.leakage_type == "DISPUTE_RECOVERY"
        ) or _ZERO
        fact.total_leakage          = total_leakage
        fact.leakage_by_type_json   = json.dumps(leakage_by_type)
        fact.computed_at            = datetime.utcnow()

        job.status            = "completed"
        job.completed_at      = datetime.utcnow()
        job.expected_payout   = expected_payout
        job.actual_payout     = actual_payout
        job.variance_amount   = variance
        job.variance_pct      = variance_pct
        job.total_leakage     = total_leakage
        job.leakage_count     = len(candidates)
        job.disputable_amount = disputable_amt
        job.summary_json      = json.dumps({
            "detectors":      detector_summary,
            "leakage_by_type": leakage_by_type,
            "staged_rows":    row_counts,
        })

        await db.commit()

        await event_bus.emit(jid, {
            "stage": "report", "status": "completed",
            "message": "Reconciliation fact written to database",
        })

        # ── Terminal event: completed ────────────────────────────────────────
        await event_bus.emit(jid, {
            "type":           "completed",
            "total_leakage":  float(total_leakage),
            "leakage_count":  len(candidates),
            "disputable":     float(disputable_amt),
            "recovery_total": float(recovery_total),
            "expected_payout": float(expected_payout),
            "actual_payout":   float(actual_payout),
            "variance":        float(variance),
            "variance_pct":    float(variance_pct),
            "message": "Reconciliation complete",
        })
        await event_bus.close(jid)

        logger.info(
            "ReconJob %s completed: %d leakage events, total ₹%s",
            job_id, len(candidates), total_leakage,
        )

    except Exception as exc:
        await db.rollback()
        job.status        = "failed"
        job.error_message = str(exc)
        job.completed_at  = datetime.utcnow()
        await db.commit()

        await event_bus.emit(jid, {
            "type":    "failed",
            "error":   str(exc),
            "message": f"Reconciliation failed: {exc}",
        })
        await event_bus.close(jid)

        logger.exception("ReconJob %s failed: %s", job_id, exc)

    return job
