"""
Reconciliation engine — orchestrates rule loading, detection, and result assembly.

Entry point: run_reconciliation(db, settlement_id=..., company_id=...)

The engine is read-only with respect to the DB: it loads data, evaluates rules,
and returns a ReconciliationRunResult. Persisting the result is the caller's job
(use storage.save_result).
"""
import json
import logging
import time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.reconciliation_rule import ReconciliationRule
from app.db.models.settlement import Settlement
from app.db.models.settlement_transaction import SettlementTransaction
from app.services.reconciliation.detectors import (
    detect_missing_payout,
    detect_payout_mismatch,
    detect_referral_fee_overcharge,
    detect_fba_fee_overcharge,
    detect_duplicate_deductions,
    detect_unexpected_fees,
    detect_penalty_mismatches,
)
from app.services.reconciliation.models import (
    DetectorLog,
    DiscrepancyCandidate,
    ReconciliationRunResult,
    RuleConfig,
)
from app.services.reconciliation.scorer import apply_scoring

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")

# Registry maps rule_type → detector function.
# Each detector: (settlement, transactions, payout, params, rule_id) → list[DiscrepancyCandidate]
DETECTOR_REGISTRY = {
    "missing_payout":           detect_missing_payout,
    "payout_amount_mismatch":   detect_payout_mismatch,
    "referral_fee_overcharge":  detect_referral_fee_overcharge,
    "fba_fee_overcharge":       detect_fba_fee_overcharge,
    "duplicate_deduction":      detect_duplicate_deductions,
    "unexpected_fee":           detect_unexpected_fees,
    "penalty_mismatch":         detect_penalty_mismatches,
}


async def _load_settlement(db: AsyncSession, settlement_id: UUID) -> Settlement | None:
    result = await db.execute(
        select(Settlement)
        .options(
            selectinload(Settlement.transactions).selectinload(SettlementTransaction.fees),
            selectinload(Settlement.payout),
        )
        .where(Settlement.id == settlement_id)
    )
    return result.scalar_one_or_none()


async def _load_rules(
    db: AsyncSession, company_id: UUID, platform: str
) -> list[RuleConfig]:
    result = await db.execute(
        select(ReconciliationRule)
        .where(
            ReconciliationRule.is_active.is_(True),
            (ReconciliationRule.company_id == company_id)
            | ReconciliationRule.company_id.is_(None),
            (ReconciliationRule.platform == platform)
            | ReconciliationRule.platform.is_(None),
        )
        .order_by(ReconciliationRule.company_id.nullsfirst())
    )
    rows = result.scalars().all()
    return [
        RuleConfig(
            id=r.id,
            rule_type=r.rule_type,
            rule_name=r.rule_name,
            severity=r.severity,
            parameters=json.loads(r.parameters_json or "{}"),
            platform=r.platform,
        )
        for r in rows
    ]


def _compute_status(discrepancies: list[DiscrepancyCandidate]) -> str:
    if any(d.severity == "critical" for d in discrepancies):
        return "critical"
    if any(d.severity == "warning" for d in discrepancies):
        return "warning"
    if discrepancies:
        return "warning"
    return "clean"


async def run_reconciliation(
    db: AsyncSession,
    *,
    settlement_id: UUID,
    company_id: UUID,
) -> ReconciliationRunResult:
    """
    Run the full reconciliation pipeline for one settlement.

    Steps:
      1. Load settlement + transactions + fees + payout (one round-trip).
      2. Load applicable rules (global + company-specific).
      3. Evaluate each active rule via its registered detector.
      4. Aggregate discrepancies and compute status.
      5. Return ReconciliationRunResult (not persisted — caller saves it).
    """
    t0 = time.perf_counter()

    settlement = await _load_settlement(db, settlement_id)
    if not settlement:
        return ReconciliationRunResult(
            settlement_id=settlement_id,
            company_id=company_id,
            platform="unknown",
            status="error",
            discrepancies=[],
            rules_evaluated=0,
            processing_time_ms=0,
            total_variance_amount=_ZERO,
            error_message="Settlement not found.",
        )

    if settlement.company_id != company_id:
        return ReconciliationRunResult(
            settlement_id=settlement_id,
            company_id=company_id,
            platform=settlement.platform,
            status="error",
            discrepancies=[],
            rules_evaluated=0,
            processing_time_ms=0,
            total_variance_amount=_ZERO,
            error_message="Settlement does not belong to the specified company.",
        )

    rules = await _load_rules(db, company_id, settlement.platform)
    transactions = settlement.transactions
    payout = settlement.payout

    loaded_fees = sum(len(txn.fees) for txn in transactions)

    all_discrepancies: list[DiscrepancyCandidate] = []
    execution_log: list[DetectorLog] = []

    for rule in rules:
        detector = DETECTOR_REGISTRY.get(rule.rule_type)
        if detector is None:
            logger.warning("No detector registered for rule_type='%s'", rule.rule_type)
            continue

        det_t0 = time.perf_counter()
        error_msg: str | None = None
        events: list[DiscrepancyCandidate] = []

        try:
            events = detector(settlement, transactions, payout, rule.parameters, rule.id)
            for event in events:
                event.rule_id = rule.id
        except Exception as exc:
            error_msg = str(exc)
            logger.exception(
                "Detector '%s' raised an exception for settlement %s",
                rule.rule_type, settlement_id,
            )

        elapsed_ms = int((time.perf_counter() - det_t0) * 1000)
        execution_log.append(DetectorLog(
            rule_type=rule.rule_type,
            rule_name=rule.rule_name,
            fired=len(events),
            elapsed_ms=elapsed_ms,
            error=error_msg,
        ))
        all_discrepancies.extend(events)

    # Variance-aware severity scoring (may promote warning → critical or demote to info)
    apply_scoring(all_discrepancies)

    total_variance = sum(
        (d.variance_amount or _ZERO) for d in all_discrepancies
    )

    return ReconciliationRunResult(
        settlement_id=settlement_id,
        company_id=company_id,
        platform=settlement.platform,
        status=_compute_status(all_discrepancies),
        discrepancies=all_discrepancies,
        rules_evaluated=len(rules),
        processing_time_ms=int((time.perf_counter() - t0) * 1000),
        total_variance_amount=total_variance,
        execution_log=execution_log,
        loaded_transactions=len(transactions),
        loaded_fees=loaded_fees,
    )
