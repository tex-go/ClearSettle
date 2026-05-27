"""
Rule engine — loads, applies overrides, evaluates, and logs configurable rules.

Entry points
------------
evaluate_rules_for_settlement(db, settlement_id, company_id, *, dry_run, triggered_by)
    Build a context dict from the settlement and evaluate all applicable rules.

evaluate_rule(db, rule_id, company_id, context, *, dry_run, triggered_by)
    Evaluate a single rule against the supplied context dict (used for testing).

load_effective_rules(db, company_id, platform, *, enabled_only)
    Return rules with company overrides applied — used by the router for listing.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.rule import Rule
from app.db.models.company_rule_override import CompanyRuleOverride
from app.db.models.rule_execution_log import RuleExecutionLog
from app.db.models.settlement import Settlement
from app.db.models.settlement_transaction import SettlementTransaction
from app.services.rules.evaluator import evaluate_rule_conditions
from app.services.rules.actions import execute_actions

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class RuleEvaluationResult:
    rule_id:         UUID
    rule_type:       str
    rule_name:       str
    severity:        str
    matched:         bool
    actions_taken:   list[dict]   = field(default_factory=list)
    error_message:   Optional[str] = None
    duration_ms:     int           = 0
    is_dry_run:      bool          = False


@dataclass
class BatchEvaluationResult:
    settlement_id:  UUID
    company_id:     UUID
    platform:       str
    rules_evaluated: int          = 0
    rules_matched:   int          = 0
    total_actions:   int          = 0
    results:         list[RuleEvaluationResult] = field(default_factory=list)
    duration_ms:     int          = 0
    error_message:   Optional[str] = None


# ── Context builder ───────────────────────────────────────────────────────────

def _build_settlement_context(settlement: Settlement) -> dict[str, Any]:
    """
    Build a flat evaluation context from a loaded Settlement.

    All amounts are cast to float so numeric operators work without Decimal handling
    in the evaluator.
    """
    payout = settlement.payout
    transactions = settlement.transactions or []

    total_fees    = _ZERO
    total_sales   = _ZERO
    total_refunds = _ZERO
    fee_counts: dict[str, int] = {}

    for txn in transactions:
        if txn.transaction_type == "shipment":
            total_sales += abs(txn.principal_amount or _ZERO)
        elif txn.transaction_type == "refund":
            total_refunds += abs(txn.principal_amount or _ZERO)
        for fee in (txn.fees or []):
            total_fees += abs(fee.amount or _ZERO)
            fee_counts[fee.fee_type or ""] = fee_counts.get(fee.fee_type or "", 0) + 1

    payout_amount = float(abs(payout.amount or _ZERO)) if payout else 0.0
    expected_transfer = float(abs(settlement.fund_transfer_amount or _ZERO))
    payout_variance = abs(expected_transfer - payout_amount)

    days_since_close = 0
    if settlement.settlement_end_date:
        days_since_close = (datetime.utcnow() - settlement.settlement_end_date).days

    return {
        # Settlement-level
        "settlement_status":    settlement.status or "",
        "platform":             settlement.platform or "",
        "total_amount":         float(abs(settlement.total_amount or _ZERO)),
        "fund_transfer_amount": float(abs(settlement.fund_transfer_amount or _ZERO)),
        "days_since_close":     max(0, days_since_close),

        # Payout
        "payout_amount":   payout_amount,
        "payout_received": 1 if payout else 0,
        "payout_variance": float(payout_variance),

        # Financials
        "total_sales":   float(total_sales),
        "total_refunds": float(total_refunds),
        "total_fees":    float(total_fees),
        "return_rate_pct": (
            float(total_refunds / total_sales * 100)
            if total_sales > _ZERO else 0.0
        ),

        # Duplicate detection helper
        "max_fee_type_count": max(fee_counts.values()) if fee_counts else 0,
    }


# ── Rule loader with override merging ─────────────────────────────────────────

async def _load_rules_with_overrides(
    db: AsyncSession,
    company_id: UUID,
    platform: str,
    *,
    enabled_only: bool = True,
) -> list[Rule]:
    """
    Load global + company rules and apply CompanyRuleOverride patches.

    Override fields (is_enabled, severity, priority, parameters_json) are merged
    onto the rule object in memory — the DB rows are not modified.
    """
    result = await db.execute(
        select(Rule)
        .where(
            (Rule.company_id == company_id) | Rule.company_id.is_(None),
            (Rule.platform == platform) | Rule.platform.is_(None),
        )
        .options(
            selectinload(Rule.conditions),
            selectinload(Rule.actions),
        )
        .order_by(Rule.priority.asc())
    )
    rules = list(result.scalars().all())

    # Load all overrides for this company in one query
    ov_result = await db.execute(
        select(CompanyRuleOverride).where(CompanyRuleOverride.company_id == company_id)
    )
    overrides: dict[UUID, CompanyRuleOverride] = {
        ov.rule_id: ov for ov in ov_result.scalars().all()
    }

    effective: list[Rule] = []
    for rule in rules:
        ov = overrides.get(rule.id)
        if ov:
            # Apply override fields in memory without mutating the ORM row permanently
            if ov.is_enabled is not None:
                rule.is_enabled = ov.is_enabled
            if ov.severity is not None:
                rule.severity = ov.severity
            if ov.priority is not None:
                rule.priority = ov.priority
            if ov.parameters_json:
                try:
                    base = json.loads(rule.parameters_json or "{}")
                    override = json.loads(ov.parameters_json)
                    rule.parameters_json = json.dumps({**base, **override})
                except Exception:
                    pass

        if enabled_only and not rule.is_enabled:
            continue
        effective.append(rule)

    return effective


async def load_effective_rules(
    db: AsyncSession,
    company_id: UUID,
    platform: str,
    *,
    enabled_only: bool = False,
) -> list[Rule]:
    """Public accessor used by the router."""
    return await _load_rules_with_overrides(db, company_id, platform, enabled_only=enabled_only)


# ── Single-rule evaluator ─────────────────────────────────────────────────────

async def evaluate_rule(
    db: AsyncSession,
    rule_id: UUID,
    company_id: UUID,
    context: dict[str, Any],
    *,
    dry_run: bool = True,
    triggered_by: str = "manual",
    settlement_id: Optional[UUID] = None,
) -> RuleEvaluationResult:
    """
    Evaluate a single rule against a supplied context dict.

    Used for the /rules/{id}/test endpoint.  Does not fire real actions when
    dry_run=True (actions are simulated and returned but not persisted).
    """
    res = await db.execute(
        select(Rule)
        .where(Rule.id == rule_id)
        .options(selectinload(Rule.conditions), selectinload(Rule.actions))
    )
    rule = res.scalar_one_or_none()
    if not rule:
        return RuleEvaluationResult(
            rule_id=rule_id, rule_type="unknown", rule_name="unknown",
            severity="info", matched=False, error_message="Rule not found",
        )

    t0 = time.perf_counter()
    matched = False
    actions_taken: list[dict] = []
    error_msg: Optional[str] = None
    actions_count = 0

    try:
        matched = evaluate_rule_conditions(rule, context)
        if matched and not dry_run:
            actions_taken = execute_actions(rule, context)
            actions_count = len(actions_taken)
        elif matched and dry_run:
            actions_taken = [{"action": a.action_type, "dry_run": True} for a in rule.actions]
            actions_count = len(actions_taken)
    except Exception as exc:
        error_msg = str(exc)
        logger.exception("engine.evaluate_rule: rule=%s error=%s", rule_id, exc)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    # Persist execution log
    log_entry = RuleExecutionLog(
        rule_id=rule.id,
        company_id=company_id,
        settlement_id=settlement_id,
        context_json=json.dumps({k: str(v) for k, v in list(context.items())[:20]}),
        matched=matched,
        actions_executed=actions_count,
        duration_ms=elapsed_ms,
        error_message=error_msg,
        is_dry_run=dry_run,
        triggered_by=triggered_by,
    )
    db.add(log_entry)

    return RuleEvaluationResult(
        rule_id=rule.id,
        rule_type=rule.rule_type,
        rule_name=rule.name,
        severity=rule.severity,
        matched=matched,
        actions_taken=actions_taken,
        error_message=error_msg,
        duration_ms=elapsed_ms,
        is_dry_run=dry_run,
    )


# ── Batch evaluator for a full settlement ────────────────────────────────────

async def evaluate_rules_for_settlement(
    db: AsyncSession,
    settlement_id: UUID,
    company_id: UUID,
    *,
    dry_run: bool = False,
    triggered_by: str = "automatic",
) -> BatchEvaluationResult:
    """
    Load a settlement, build its evaluation context, then run all applicable rules.

    Persists one RuleExecutionLog per rule (committed by caller).
    Returns a BatchEvaluationResult summary.
    """
    t0 = time.perf_counter()

    # Load settlement
    s_res = await db.execute(
        select(Settlement)
        .where(Settlement.id == settlement_id, Settlement.company_id == company_id)
        .options(
            selectinload(Settlement.transactions).selectinload(SettlementTransaction.fees),
            selectinload(Settlement.payout),
        )
    )
    settlement = s_res.scalar_one_or_none()
    if not settlement:
        return BatchEvaluationResult(
            settlement_id=settlement_id, company_id=company_id,
            platform="unknown", error_message="Settlement not found or access denied",
        )

    context = _build_settlement_context(settlement)
    rules = await _load_rules_with_overrides(db, company_id, settlement.platform, enabled_only=True)

    results: list[RuleEvaluationResult] = []
    for rule in rules:
        det_t0 = time.perf_counter()
        matched = False
        actions_taken: list[dict] = []
        error_msg: Optional[str] = None
        actions_count = 0

        try:
            matched = evaluate_rule_conditions(rule, context)
            if matched and not dry_run:
                actions_taken = execute_actions(rule, context)
                actions_count = len(actions_taken)
            elif matched and dry_run:
                actions_taken = [{"action": a.action_type, "dry_run": True} for a in rule.actions]
                actions_count = len(actions_taken)
        except Exception as exc:
            error_msg = str(exc)
            logger.exception("engine.batch: rule=%s settlement=%s: %s", rule.id, settlement_id, exc)

        elapsed_ms = int((time.perf_counter() - det_t0) * 1000)

        log_entry = RuleExecutionLog(
            rule_id=rule.id,
            company_id=company_id,
            settlement_id=settlement_id,
            context_json=json.dumps({k: str(v) for k, v in list(context.items())[:20]}),
            matched=matched,
            actions_executed=actions_count,
            duration_ms=elapsed_ms,
            error_message=error_msg,
            is_dry_run=dry_run,
            triggered_by=triggered_by,
        )
        db.add(log_entry)

        results.append(RuleEvaluationResult(
            rule_id=rule.id,
            rule_type=rule.rule_type,
            rule_name=rule.name,
            severity=rule.severity,
            matched=matched,
            actions_taken=actions_taken,
            error_message=error_msg,
            duration_ms=elapsed_ms,
            is_dry_run=dry_run,
        ))

    matched_count = sum(1 for r in results if r.matched)
    total_actions = sum(len(r.actions_taken) for r in results)

    return BatchEvaluationResult(
        settlement_id=settlement_id,
        company_id=company_id,
        platform=settlement.platform,
        rules_evaluated=len(results),
        rules_matched=matched_count,
        total_actions=total_actions,
        results=results,
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )
