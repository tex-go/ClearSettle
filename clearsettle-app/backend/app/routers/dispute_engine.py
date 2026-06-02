"""Dispute Engine — serves playbook rules from DB.

Phase 1: replaced get_db_optional with get_db; removed mock fallback.
Empty-DB returns [] instead of canned mock data.
"""
from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.db.models.rule import Rule

router = APIRouter()


def _rule_to_dict(r: Rule) -> dict:
    conditions = []
    try:
        conditions = [
            {"field": c.field, "operator": c.operator,
             "value": c.value, "value_type": c.value_type}
            for c in r.conditions
        ]
    except Exception:
        pass

    evidence = []
    try:
        evidence = json.loads(r.evidence_json or "[]")
    except Exception:
        pass

    return {
        "id":              str(r.id),
        "name":            r.name,
        "description":     r.description or "",
        "category":        r.category,
        "rule_type":       r.rule_type,
        "severity":        r.severity,
        "priority":        r.priority,
        "platform":        r.platform,
        "is_enabled":      r.is_enabled,
        "condition_logic": r.condition_logic,
        "conditions":      conditions,
        "verdict":         r.verdict or "",
        "legal_basis":     r.legal_basis or "",
        "evidence":        evidence,
        "dispute_window":  r.dispute_window or "",
        "success_rate_pct": float(r.success_rate_pct) if r.success_rate_pct is not None else None,
        "recovery_min":    float(r.recovery_min) if r.recovery_min is not None else None,
        "recovery_max":    float(r.recovery_max) if r.recovery_max is not None else None,
        "auto_raise":      r.auto_raise,
        "playbook_notes":  r.playbook_notes or "",
        "parameters_json": r.parameters_json or "{}",
    }


@router.get("/rules")
async def get_rules(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    verdict:  Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    enabled_only: bool = Query(default=False),
):
    q = select(Rule).options(selectinload(Rule.conditions))
    if enabled_only:
        q = q.where(Rule.is_enabled.is_(True))
    if category:
        q = q.where(Rule.category == category)
    if severity:
        q = q.where(Rule.severity == severity)
    if verdict:
        q = q.where(Rule.verdict == verdict)
    if platform:
        q = q.where((Rule.platform == platform) | Rule.platform.is_(None))
    q = q.order_by(Rule.priority.asc())

    rows = (await db.execute(q)).scalars().all()
    items = [_rule_to_dict(r) for r in rows]
    return {
        "items": items,
        "auto_raise_count": sum(1 for i in items if i["auto_raise"]),
    }


@router.get("/rules/{rule_id}")
async def get_rule(
    rule_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Rule not found")

    res = await db.execute(
        select(Rule)
        .where(Rule.id == uid)
        .options(selectinload(Rule.conditions), selectinload(Rule.actions))
    )
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_dict(rule)


@router.get("/calculator")
def calculator(
    gmv: float = Query(5000000),
    years: int = Query(1),
    platform: str = Query("multi"),
    model: str = Query("s15"),
):
    rates = {"amazon": 0.028, "flipkart": 0.022, "meesho": 0.008, "multi": 0.035}
    rate = rates.get(platform, 0.035)
    total_gmv = gmv * years
    raw_overcharge = total_gmv * rate
    platform_dispute = raw_overcharge * 0.25
    legal_route = raw_overcharge * 0.45
    gst_recovery = total_gmv * 0.01 * 0.6
    total_recoverable = platform_dispute + legal_route + gst_recovery
    model_rates = {"s15": 0.15, "s20": 0.20, "s25": 0.25}
    if model in model_rates:
        cs_earnings = total_recoverable * model_rates[model]
    else:
        cs_earnings = 1499 * 12 * years
    return {
        "total_gmv": round(total_gmv),
        "raw_overcharge": round(raw_overcharge),
        "platform_dispute": round(platform_dispute),
        "legal_route": round(legal_route),
        "gst_recovery": round(gst_recovery),
        "total_recoverable": round(total_recoverable),
        "clearsettle_earnings": round(cs_earnings),
    }
