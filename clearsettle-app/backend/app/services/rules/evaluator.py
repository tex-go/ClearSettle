"""
Condition evaluator — compares a RuleCondition against a context dict.

Supports these operators:
    gt  | lt  | gte | lte   — numeric comparisons
    eq  | neq               — equality (type-aware)
    contains               — substring or list membership
    in  | not_in           — value is / isn't in a comma-separated list
    exists                 — field is present and not None

value_type controls how the stored string 'value' is cast before comparison:
    number  → float
    boolean → bool ("true"/"1" = True)
    string  → str (no cast)
    list    → split on comma, each element stripped
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _cast(raw: str, value_type: str) -> Any:
    if value_type == "number":
        return float(raw)
    if value_type == "boolean":
        return raw.strip().lower() in ("true", "1", "yes")
    if value_type == "list":
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw   # string — no cast


def _coerce(field_value: Any, value_type: str) -> Any:
    """Coerce the context value to the same type as the condition value."""
    if value_type == "number":
        return float(field_value)
    if value_type == "boolean":
        if isinstance(field_value, bool):
            return field_value
        return str(field_value).strip().lower() in ("true", "1", "yes")
    return str(field_value)


def _apply_operator(op: str, field_val: Any, cond_val: Any, value_type: str) -> bool:
    if op == "exists":
        return field_val is not None

    if op == "contains":
        if isinstance(field_val, (list, tuple)):
            return str(cond_val) in [str(x) for x in field_val]
        return str(cond_val).lower() in str(field_val).lower()

    if op in ("in", "not_in"):
        # cond_val is a comma-separated list
        allowed = [x.strip() for x in str(cond_val).split(",")]
        result = str(field_val) in allowed
        return result if op == "in" else not result

    # Numeric / equality ops — coerce field value
    try:
        coerced = _coerce(field_val, value_type)
    except (TypeError, ValueError):
        logger.debug("evaluator: cannot coerce field value %r to %s", field_val, value_type)
        return False

    if op == "eq":
        return coerced == cond_val
    if op == "neq":
        return coerced != cond_val
    if op == "gt":
        return coerced > cond_val
    if op == "lt":
        return coerced < cond_val
    if op == "gte":
        return coerced >= cond_val
    if op == "lte":
        return coerced <= cond_val

    logger.warning("evaluator: unknown operator '%s'", op)
    return False


def evaluate_condition(condition, context: dict[str, Any]) -> bool:
    """Return True if the condition matches the context."""
    field_value = context.get(condition.field)
    if field_value is None and condition.operator != "exists":
        return False

    try:
        cond_value = _cast(condition.value, condition.value_type)
        return _apply_operator(condition.operator, field_value, cond_value, condition.value_type)
    except Exception as exc:
        logger.warning(
            "evaluator: condition field=%s op=%s value=%s raised %s",
            condition.field, condition.operator, condition.value, exc,
        )
        return False


def evaluate_rule_conditions(rule, context: dict[str, Any]) -> bool:
    """
    Return True if the rule's conditions pass against context.

    condition_logic='all'  → every condition must match (AND)
    condition_logic='any'  → at least one condition must match (OR)
    Empty conditions list  → returns False (explicit conditions required).
    """
    if not rule.conditions:
        return False

    results = [evaluate_condition(c, context) for c in rule.conditions]

    if rule.condition_logic == "any":
        return any(results)
    return all(results)
