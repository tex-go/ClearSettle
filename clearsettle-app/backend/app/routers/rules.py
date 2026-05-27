"""
Configurable rule engine router.

Endpoints
---------
GET    /rules                          — list all applicable rules (global + company)
POST   /rules                          — create a new company rule
GET    /rules/types                    — list supported rule types
GET    /rules/{rule_id}                — rule detail with conditions + actions
PATCH  /rules/{rule_id}               — update rule metadata
DELETE /rules/{rule_id}               — delete a company-owned rule
PATCH  /rules/{rule_id}/toggle        — enable or disable a rule
POST   /rules/{rule_id}/override      — upsert a company override for a global rule
DELETE /rules/{rule_id}/override      — remove company override
POST   /rules/{rule_id}/test          — evaluate rule against a supplied context
GET    /rules/{rule_id}/logs          — rule execution history
POST   /rules/evaluate/{settlement_id} — dry-run all rules against a settlement
"""
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_db
from app.core.rbac import require_db_permission
from app.db.models.rule import Rule
from app.db.models.rule_action import RuleAction
from app.db.models.rule_condition import RuleCondition
from app.db.models.company_rule_override import CompanyRuleOverride
from app.db.models.rule_execution_log import RuleExecutionLog
from app.db.models.user import User
from app.schemas.rules import (
    ActionCreate, BatchEvaluationOut, ConditionCreate,
    OverrideCreate, OverrideOut, RuleCreate, RuleEvaluationOut,
    RuleOut, RuleUpdate, TestRuleRequest,
)
from app.services.rules.engine import (
    evaluate_rule, evaluate_rules_for_settlement, load_effective_rules,
)
from app.services.rules.registry import RULE_TYPES, get_rule_type_meta

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _company(user: User):
    c = user.companies[0] if getattr(user, "companies", None) else None
    if not c:
        raise HTTPException(status_code=400, detail="No company found for this user")
    return c


async def _get_owned_rule(db: AsyncSession, rule_id: str, company_id: UUID) -> Rule:
    res = await db.execute(
        select(Rule)
        .where(Rule.id == UUID(rule_id), Rule.company_id == company_id)
        .options(selectinload(Rule.conditions), selectinload(Rule.actions))
    )
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found or not owned by this company")
    return rule


async def _get_any_rule(db: AsyncSession, rule_id: str) -> Rule:
    res = await db.execute(
        select(Rule)
        .where(Rule.id == UUID(rule_id))
        .options(selectinload(Rule.conditions), selectinload(Rule.actions))
    )
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[RuleOut])
async def list_rules(
    platform:    Optional[str] = Query(default=None),
    category:    Optional[str] = Query(default=None),
    rule_type:   Optional[str] = Query(default=None),
    enabled_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:read")),
):
    """List global rules plus company-specific rules, with overrides applied."""
    company = _company(current_user)
    rules = await load_effective_rules(
        db, company.id, platform or "amazon", enabled_only=enabled_only
    )
    # Apply category / rule_type filter after loading
    if category:
        rules = [r for r in rules if r.category == category]
    if rule_type:
        rules = [r for r in rules if r.rule_type == rule_type]
    return rules


# ── Supported types ───────────────────────────────────────────────────────────

@router.get("/types")
def list_rule_types():
    """Return all supported rule type strings with metadata."""
    return {
        "rule_types": {
            rt: {
                "category":          meta["category"],
                "default_severity":  meta["default_severity"],
                "description":       meta["description"],
                "context_fields":    meta["context_fields"],
            }
            for rt, meta in RULE_TYPES.items()
        }
    }


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=RuleOut, status_code=201)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:write")),
):
    """Create a new company-scoped rule with conditions and actions."""
    company = _company(current_user)

    rule = Rule(
        company_id=company.id,
        name=body.name,
        description=body.description,
        category=body.category,
        rule_type=body.rule_type,
        severity=body.severity,
        priority=body.priority,
        platform=body.platform,
        is_enabled=body.is_enabled,
        condition_logic=body.condition_logic,
        parameters_json=body.parameters_json,
        recovery_metadata_json=body.recovery_metadata_json,
        verdict=body.verdict,
        legal_basis=body.legal_basis,
        evidence_json=body.evidence_json,
        dispute_window=body.dispute_window,
        success_rate_pct=body.success_rate_pct,
        recovery_min=body.recovery_min,
        recovery_max=body.recovery_max,
        auto_raise=body.auto_raise,
        playbook_notes=body.playbook_notes,
    )
    db.add(rule)
    await db.flush()   # get rule.id before inserting children

    for c in body.conditions:
        db.add(RuleCondition(
            rule_id=rule.id, field=c.field, operator=c.operator,
            value=c.value, value_type=c.value_type, description=c.description,
        ))
    for a in body.actions:
        db.add(RuleAction(
            rule_id=rule.id, action_type=a.action_type,
            action_order=a.action_order, parameters_json=a.parameters_json,
            is_enabled=a.is_enabled,
        ))

    await db.commit()

    # Reload with relationships
    res = await db.execute(
        select(Rule)
        .where(Rule.id == rule.id)
        .options(selectinload(Rule.conditions), selectinload(Rule.actions))
    )
    return res.scalar_one()


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{rule_id}", response_model=RuleOut)
async def get_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:read")),
):
    """Return a single rule with conditions and actions."""
    return await _get_any_rule(db, rule_id)


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{rule_id}", response_model=RuleOut)
async def update_rule(
    rule_id: str,
    body: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:write")),
):
    """Update a company-owned rule. Cannot modify global (company_id=None) rules."""
    company = _company(current_user)
    rule = await _get_owned_rule(db, rule_id, company.id)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    db.add(rule)
    await db.commit()

    res = await db.execute(
        select(Rule)
        .where(Rule.id == rule.id)
        .options(selectinload(Rule.conditions), selectinload(Rule.actions))
    )
    return res.scalar_one()


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:write")),
):
    """Delete a company-owned rule (cascade deletes conditions, actions, logs)."""
    company = _company(current_user)
    rule = await _get_owned_rule(db, rule_id, company.id)
    await db.delete(rule)
    await db.commit()


# ── Toggle ────────────────────────────────────────────────────────────────────

@router.patch("/{rule_id}/toggle")
async def toggle_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:write")),
):
    """Flip the is_enabled flag on any accessible rule."""
    company = _company(current_user)
    # Try company rule first, then global
    res = await db.execute(
        select(Rule).where(
            Rule.id == UUID(rule_id),
            (Rule.company_id == company.id) | Rule.company_id.is_(None),
        )
    )
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.company_id is None:
        # For global rules, upsert a company override instead of mutating the rule
        ov_res = await db.execute(
            select(CompanyRuleOverride).where(
                CompanyRuleOverride.rule_id == rule.id,
                CompanyRuleOverride.company_id == company.id,
            )
        )
        ov = ov_res.scalar_one_or_none()
        new_enabled = not (ov.is_enabled if ov and ov.is_enabled is not None else rule.is_enabled)
        if ov:
            ov.is_enabled = new_enabled
        else:
            db.add(CompanyRuleOverride(
                rule_id=rule.id, company_id=company.id, is_enabled=new_enabled,
            ))
        await db.commit()
        return {"rule_id": rule_id, "is_enabled": new_enabled, "via": "override"}

    rule.is_enabled = not rule.is_enabled
    db.add(rule)
    await db.commit()
    return {"rule_id": rule_id, "is_enabled": rule.is_enabled, "via": "direct"}


# ── Company override ──────────────────────────────────────────────────────────

@router.post("/{rule_id}/override", response_model=OverrideOut)
async def upsert_override(
    rule_id: str,
    body: OverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:write")),
):
    """Upsert a company-specific override for a global rule."""
    rule = await _get_any_rule(db, rule_id)
    company = _company(current_user)

    ov_res = await db.execute(
        select(CompanyRuleOverride).where(
            CompanyRuleOverride.rule_id == rule.id,
            CompanyRuleOverride.company_id == company.id,
        )
    )
    ov = ov_res.scalar_one_or_none()
    if ov:
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(ov, field, value)
    else:
        ov = CompanyRuleOverride(
            rule_id=rule.id,
            company_id=company.id,
            **body.model_dump(exclude_none=True),
        )
        db.add(ov)
    await db.commit()
    await db.refresh(ov)
    return ov


@router.delete("/{rule_id}/override", status_code=204)
async def delete_override(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:write")),
):
    """Remove the company override — the rule reverts to its global defaults."""
    company = _company(current_user)
    await db.execute(
        delete(CompanyRuleOverride).where(
            CompanyRuleOverride.rule_id == UUID(rule_id),
            CompanyRuleOverride.company_id == company.id,
        )
    )
    await db.commit()


# ── Test rule ─────────────────────────────────────────────────────────────────

@router.post("/{rule_id}/test", response_model=RuleEvaluationOut)
async def test_rule(
    rule_id: str,
    body: TestRuleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:read")),
):
    """Evaluate a rule against a manually supplied context dict (always dry-run by default)."""
    company = _company(current_user)
    result = await evaluate_rule(
        db, UUID(rule_id), company.id, body.context,
        dry_run=body.dry_run, triggered_by="test",
    )
    await db.commit()
    return RuleEvaluationOut(
        rule_id=str(result.rule_id),
        rule_type=result.rule_type,
        rule_name=result.rule_name,
        severity=result.severity,
        matched=result.matched,
        actions_taken=result.actions_taken,
        error_message=result.error_message,
        duration_ms=result.duration_ms,
        is_dry_run=result.is_dry_run,
    )


# ── Execution logs ────────────────────────────────────────────────────────────

@router.get("/{rule_id}/logs")
async def get_rule_logs(
    rule_id: str,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:rules:read")),
):
    """Return the most recent execution logs for a rule."""
    company = _company(current_user)
    res = await db.execute(
        select(RuleExecutionLog)
        .where(
            RuleExecutionLog.rule_id == UUID(rule_id),
            RuleExecutionLog.company_id == company.id,
        )
        .order_by(RuleExecutionLog.created_at.desc())
        .limit(limit)
    )
    logs = res.scalars().all()
    return [
        {
            "id":               str(log.id),
            "rule_id":          str(log.rule_id),
            "settlement_id":    str(log.settlement_id) if log.settlement_id else None,
            "matched":          log.matched,
            "actions_executed": log.actions_executed,
            "duration_ms":      log.duration_ms,
            "error_message":    log.error_message,
            "is_dry_run":       log.is_dry_run,
            "triggered_by":     log.triggered_by,
            "created_at":       log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ── Batch evaluate against a settlement ───────────────────────────────────────

@router.post("/evaluate/{settlement_id}", response_model=BatchEvaluationOut)
async def evaluate_settlement_rules(
    settlement_id: str,
    dry_run: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("reconciliation:run")),
):
    """
    Evaluate all applicable rules for a settlement.

    Set dry_run=false to execute real actions.  Default is dry_run=true
    (simulate actions, log everything, but don't fire real side-effects).
    """
    company = _company(current_user)
    result = await evaluate_rules_for_settlement(
        db, UUID(settlement_id), company.id,
        dry_run=dry_run, triggered_by="api",
    )
    await db.commit()
    return BatchEvaluationOut(
        settlement_id=str(result.settlement_id),
        company_id=str(result.company_id),
        platform=result.platform,
        rules_evaluated=result.rules_evaluated,
        rules_matched=result.rules_matched,
        total_actions=result.total_actions,
        results=[
            RuleEvaluationOut(
                rule_id=str(r.rule_id),
                rule_type=r.rule_type,
                rule_name=r.rule_name,
                severity=r.severity,
                matched=r.matched,
                actions_taken=r.actions_taken,
                error_message=r.error_message,
                duration_ms=r.duration_ms,
                is_dry_run=r.is_dry_run,
            )
            for r in result.results
        ],
        duration_ms=result.duration_ms,
        error_message=result.error_message,
    )
