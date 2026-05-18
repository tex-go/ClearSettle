"""
Action executor — runs the actions attached to a Rule when it fires.

Each handler receives (rule, context, parameters) and returns a dict describing
what was done.  Handlers are intentionally lightweight and do not commit to DB —
the engine handles persistence of the log row.

Supported action types:
    create_discrepancy   — records a discrepancy finding for review
    create_alert         — emits a structured alert log entry
    auto_dispute         — marks the discrepancy for auto-dispute submission
    recommend_recovery   — attaches a recovery suggestion
    send_notification    — logs a notification intent (actual delivery is async)
    escalate_case        — flags for human escalation
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _params(action) -> dict[str, Any]:
    try:
        return json.loads(action.parameters_json or "{}")
    except Exception:
        return {}


def _action_create_discrepancy(rule, context: dict, params: dict) -> dict:
    return {
        "action":           "create_discrepancy",
        "rule_type":        rule.rule_type,
        "severity":         rule.severity,
        "description":      f"[{rule.rule_type}] {rule.name}: rule conditions matched",
        "context_snapshot": {k: str(v) for k, v in list(context.items())[:10]},
    }


def _action_create_alert(rule, context: dict, params: dict) -> dict:
    return {
        "action":   "create_alert",
        "rule_type": rule.rule_type,
        "severity":  rule.severity,
        "message":   f"Alert: {rule.name} triggered",
        "channel":   params.get("channel", "internal"),
    }


def _action_auto_dispute(rule, context: dict, params: dict) -> dict:
    return {
        "action":      "auto_dispute",
        "rule_type":   rule.rule_type,
        "template":    params.get("template", rule.rule_type),
        "auto_submit": params.get("auto_submit", False),
    }


def _action_recommend_recovery(rule, context: dict, params: dict) -> dict:
    try:
        recovery_meta = json.loads(rule.recovery_metadata_json or "{}")
    except Exception:
        recovery_meta = {}
    return {
        "action":          "recommend_recovery",
        "rule_type":       rule.rule_type,
        "recovery_days":   recovery_meta.get("recovery_days", 30),
        "recommendation":  recovery_meta.get("template", f"Review {rule.rule_type}"),
    }


def _action_send_notification(rule, context: dict, params: dict) -> dict:
    return {
        "action":    "send_notification",
        "rule_type": rule.rule_type,
        "channel":   params.get("channel", "email"),
        "template":  params.get("template", rule.rule_type),
        "queued":    True,
    }


def _action_escalate_case(rule, context: dict, params: dict) -> dict:
    return {
        "action":       "escalate_case",
        "rule_type":    rule.rule_type,
        "severity":     rule.severity,
        "escalate_to":  params.get("escalate_to", "admin"),
        "priority":     rule.priority,
    }


_HANDLERS = {
    "create_discrepancy":  _action_create_discrepancy,
    "create_alert":        _action_create_alert,
    "auto_dispute":        _action_auto_dispute,
    "recommend_recovery":  _action_recommend_recovery,
    "send_notification":   _action_send_notification,
    "escalate_case":       _action_escalate_case,
}


def execute_action(rule, action, context: dict[str, Any]) -> dict[str, Any] | None:
    """
    Execute a single RuleAction.

    Returns the action result dict, or None if the action type is unknown
    or the action is disabled.
    """
    if not action.is_enabled:
        return None
    handler = _HANDLERS.get(action.action_type)
    if not handler:
        logger.warning("actions: unknown action_type '%s' on rule %s", action.action_type, rule.id)
        return None
    try:
        return handler(rule, context, _params(action))
    except Exception as exc:
        logger.exception("actions: %s failed for rule %s: %s", action.action_type, rule.id, exc)
        return {"action": action.action_type, "error": str(exc)}


def execute_actions(rule, context: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute all enabled actions for a rule and return their results."""
    results = []
    for action in rule.actions:
        result = execute_action(rule, action, context)
        if result is not None:
            results.append(result)
    return results
