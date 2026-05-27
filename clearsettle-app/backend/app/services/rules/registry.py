"""
Built-in rule type registry.

Each entry describes a rule type — its category, default severity, the context
fields it expects, and human-readable metadata.  The registry is the single
source of truth for what rule_type strings are valid.
"""
from __future__ import annotations

from typing import Any

RULE_TYPES: dict[str, dict[str, Any]] = {
    "commission_overcharge": {
        "category": "fees",
        "default_severity": "warning",
        "description": "Referral/commission fee rate exceeds the expected maximum",
        "context_fields": ["fee_rate_pct", "fee_amount", "fee_type"],
        "default_parameters": {"max_rate_pct": 15},
        "supported_operators": ["gt", "gte"],
    },
    "missing_payout": {
        "category": "payout",
        "default_severity": "critical",
        "description": "Settlement closed with no fund-transfer payout recorded",
        "context_fields": ["settlement_status", "payout_amount", "days_since_close"],
        "default_parameters": {"settlement_status": "closed"},
        "supported_operators": ["eq", "lt", "lte"],
    },
    "duplicate_deduction": {
        "category": "fees",
        "default_severity": "critical",
        "description": "Same fee type deducted more than once for the same order item",
        "context_fields": ["fee_type", "deduction_count", "order_id"],
        "default_parameters": {"min_occurrences": 2},
        "supported_operators": ["gte", "gt"],
    },
    "tcs_mismatch": {
        "category": "tax",
        "default_severity": "warning",
        "description": "TCS deducted does not match 1% of taxable value (Section 52 CGST)",
        "context_fields": ["tcs_amount", "expected_tcs", "taxable_value"],
        "default_parameters": {"expected_rate_pct": 1, "tolerance_pct": 0.1},
        "supported_operators": ["gt", "gte"],
    },
    "penalty_overcharge": {
        "category": "fees",
        "default_severity": "warning",
        "description": "Service/penalty fee exceeds the contractual threshold",
        "context_fields": ["penalty_amount", "fee_type"],
        "default_parameters": {"max_penalty_amount": 5000},
        "supported_operators": ["gt", "gte"],
    },
    "high_return_rate": {
        "category": "risk",
        "default_severity": "info",
        "description": "Return rate for the settlement period exceeds the acceptable threshold",
        "context_fields": ["return_rate_pct", "total_orders", "returned_orders"],
        "default_parameters": {"max_return_rate_pct": 20},
        "supported_operators": ["gt", "gte"],
    },
    "payout_delay": {
        "category": "payout",
        "default_severity": "warning",
        "description": "Settlement closed but payout exceeds the expected settlement window",
        "context_fields": ["days_since_close", "payout_received"],
        "default_parameters": {"max_delay_days": 7},
        "supported_operators": ["gt", "gte"],
    },
    "gst_discrepancy": {
        "category": "tax",
        "default_severity": "warning",
        "description": "GST computed from settlement fees does not match reported tax amount",
        "context_fields": ["computed_gst", "reported_gst", "variance_amount"],
        "default_parameters": {"tolerance_amount": 1.0},
        "supported_operators": ["gt", "gte"],
    },
    "custom": {
        "category": "custom",
        "default_severity": "info",
        "description": "User-defined custom rule with arbitrary condition fields",
        "context_fields": [],
        "default_parameters": {},
        "supported_operators": ["gt", "lt", "gte", "lte", "eq", "neq", "contains", "in", "not_in", "exists"],
    },
}

VALID_RULE_TYPES: frozenset[str] = frozenset(RULE_TYPES)
VALID_CATEGORIES: frozenset[str] = frozenset(
    {rt["category"] for rt in RULE_TYPES.values()}
)
VALID_OPERATORS: frozenset[str] = frozenset({
    "gt", "lt", "gte", "lte", "eq", "neq", "contains", "in", "not_in", "exists",
})
VALID_SEVERITIES: frozenset[str] = frozenset({"info", "warning", "critical"})
VALID_ACTIONS: frozenset[str] = frozenset({
    "create_discrepancy", "create_alert", "auto_dispute",
    "recommend_recovery", "send_notification", "escalate_case",
})


def get_rule_type_meta(rule_type: str) -> dict[str, Any]:
    return RULE_TYPES.get(rule_type, RULE_TYPES["custom"])
