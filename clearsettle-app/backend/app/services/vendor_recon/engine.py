"""
Vendor Reconciliation Engine — orchestrates ETL + leakage detection + fact computation.

Call run_job(job_id, db) to execute a full reconciliation cycle:
  1. Load staged data for the job
  2. Run all 10 leakage detectors
  3. Compute expected vs actual payout
  4. Write leakage_events + fact_reconciliation + update recon_job
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


async def _load_staged(job_id: UUID, db: AsyncSession) -> dict:
    """Load all staging rows for a job in one pass."""
    sl = (await db.execute(select(StgSettlementLine).where(StgSettlementLine.job_id == job_id))).scalars().all()
    il = (await db.execute(select(StgInvoiceLine).where(StgInvoiceLine.job_id == job_id))).scalars().all()
    cl = (await db.execute(select(StgChargebackLine).where(StgChargebackLine.job_id == job_id))).scalars().all()
    pl = (await db.execute(select(StgPaymentLine).where(StgPaymentLine.job_id == job_id))).scalars().all()
    ol = (await db.execute(select(StgOperationalLine).where(StgOperationalLine.job_id == job_id))).scalars().all()
    return {"settlement": sl, "invoice": il, "chargeback": cl, "payment": pl, "operational": ol}


def _compute_expected_payout(staged: dict) -> dict[str, Decimal]:
    """
    expected_payout = total_invoice_value
                    - total_agreed_discounts
                    - total_valid_returns
                    - total_approved_coop
                    - total_valid_tax_adj

    We approximate from staged data:
    - invoice total = sum of stg_invoice_lines.invoice_total
    - discounts     = sum of stg_invoice_lines.discount_amount
    - returns       = sum of operational_lines[return].amount
    - coop          = sum of chargeback_lines[coop].deduction_amount where approved
    - tax adj       = sum of stg_invoice_lines.tax_amount (valid tax is part of invoiced amount)
    """
    invoice_total    = sum(
        Decimal(str(r.invoice_total)) for r in staged["invoice"]
        if r.invoice_total
    ) or _ZERO
    discounts = sum(
        Decimal(str(r.discount_amount)) for r in staged["invoice"]
        if r.discount_amount
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
        Decimal(str(r.tax_amount)) for r in staged["invoice"]
        if r.tax_amount
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
    """Sum of all payment_lines.paid_amount."""
    return sum(
        Decimal(str(r.paid_amount)) for r in staged["payment"]
        if r.paid_amount
    ) or _ZERO


def _compute_deduction_summary(staged: dict) -> dict[str, Decimal]:
    total_deductions = sum(
        Decimal(str(r.deduction_amount)) for r in staged["settlement"]
        if r.deduction_amount and Decimal(str(r.deduction_amount)) > _ZERO
    ) or _ZERO
    # Valid = known approved deductions from chargeback lines
    valid_deductions = sum(
        Decimal(str(r.deduction_amount)) for r in staged["chargeback"]
        if r.deduction_amount and r.dispute_status and
           r.dispute_status.lower() in ("approved", "agreed", "waived")
    ) or _ZERO
    return {"total_deductions": total_deductions, "valid_deductions": valid_deductions}


async def run_job(job_id: UUID, db: AsyncSession) -> ReconJob:
    """Execute the full reconciliation cycle for a job. Updates job + creates fact + leakage events."""
    job = (await db.execute(select(ReconJob).where(ReconJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise ValueError(f"ReconJob {job_id} not found")

    job.status     = "running"
    job.started_at = datetime.utcnow()
    await db.commit()

    try:
        staged = await _load_staged(job_id, db)

        # ── run all 10 detectors ──────────────────────────────────────────────
        candidates: list[LeakageCandidate] = []
        detector_summary: dict[str, int] = {}

        def run(name: str, results: list[LeakageCandidate]) -> None:
            detector_summary[name] = len(results)
            candidates.extend(results)

        run("SHORT",            detect_shortage(staged["settlement"], staged["operational"]))
        run("DUPLICATE",        detect_duplicates(staged["settlement"]))
        run("OTIF",             detect_otif(staged["operational"]))
        run("ACCRUAL",          detect_accrual_mismatch(staged["settlement"]))
        run("COOP",             detect_coop(staged["settlement"], staged["chargeback"]))
        run("RETURN",           detect_return_leakage(staged["settlement"], staged["operational"]))
        run("DAMAGE",           detect_damage(staged["settlement"], staged["operational"]))
        run("TIMING",           detect_timing(staged["invoice"], staged["payment"]))
        run("TAX",              detect_tax_mismatch(staged["settlement"], staged["invoice"]))
        run("DISPUTE_RECOVERY", detect_dispute_recovery_failure(staged["chargeback"], staged["operational"]))

        # ── persist leakage events ────────────────────────────────────────────
        disputable_amt = _ZERO
        total_leakage  = _ZERO
        dup_ded_amt    = _ZERO
        suspicious_amt = _ZERO

        for c in candidates:
            amt = c.amount or _ZERO
            total_leakage += amt
            if c.is_disputable:
                disputable_amt += amt
            if c.leakage_type == "DUPLICATE":
                dup_ded_amt += amt
            if c.leakage_type in ("SHORT", "COOP", "RETURN", "DAMAGE", "DISPUTE_RECOVERY"):
                suspicious_amt += amt

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

        # ── compute payout figures ────────────────────────────────────────────
        payout_components = _compute_expected_payout(staged)
        actual_payout     = _compute_actual_payout(staged)
        ded_summary       = _compute_deduction_summary(staged)
        expected_payout   = payout_components["expected_payout"]
        variance          = expected_payout - actual_payout
        variance_pct      = (variance / expected_payout * 100) if expected_payout else _ZERO

        # leakage by type
        leakage_by_type: dict[str, float] = {}
        for c in candidates:
            t = c.leakage_type
            leakage_by_type[t] = leakage_by_type.get(t, 0.0) + float(c.amount or 0)

        # ── upsert fact_reconciliation ────────────────────────────────────────
        existing_fact = (
            await db.execute(select(FactReconciliation).where(FactReconciliation.job_id == job_id))
        ).scalar_one_or_none()

        if existing_fact:
            fact = existing_fact
        else:
            fact = FactReconciliation(job_id=job_id)
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

        # ── update job summary ────────────────────────────────────────────────
        job.status           = "completed"
        job.completed_at     = datetime.utcnow()
        job.expected_payout  = expected_payout
        job.actual_payout    = actual_payout
        job.variance_amount  = variance
        job.variance_pct     = variance_pct
        job.total_leakage    = total_leakage
        job.leakage_count    = len(candidates)
        job.disputable_amount= disputable_amt
        job.summary_json     = json.dumps({
            "detectors": detector_summary,
            "leakage_by_type": leakage_by_type,
            "staged_rows": {k: len(v) for k, v in staged.items()},
        })

        await db.commit()
        logger.info("ReconJob %s completed: %d leakage events, total ₹%s", job_id, len(candidates), total_leakage)

    except Exception as exc:
        await db.rollback()
        job.status        = "failed"
        job.error_message = str(exc)
        job.completed_at  = datetime.utcnow()
        await db.commit()
        logger.exception("ReconJob %s failed: %s", job_id, exc)

    return job
