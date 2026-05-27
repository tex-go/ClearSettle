"""
Variance-aware severity scorer for reconciliation discrepancies.

The rule config assigns a base severity. This module can promote or demote
that severity based on actual variance amounts and discrepancy type.

Promotion rules (override rule config):
  - MISSING_PAYOUT, DUPLICATE_DEDUCTION  → always critical
  - PAYOUT_AMOUNT_MISMATCH               → critical if |variance| >= 1 000 INR
  - OVERCHARGE_REFERRAL_FEE              → critical if |variance| >= 500 INR
  - OVERCHARGE_FBA_FEE                   → critical if |variance| >= 2 000 INR
  - PENALTY_MISMATCH                     → critical if |variance| >= 5 000 INR

Demotion rules:
  - UNEXPECTED_FEE                       → always info (needs human review, not urgent)
"""
from decimal import Decimal

from app.services.reconciliation.models import DiscrepancyCandidate

_ZERO = Decimal("0")

_ALWAYS_CRITICAL = frozenset(["missing_payout", "duplicate_deduction"])
_ALWAYS_INFO     = frozenset(["unexpected_fee"])

_CRITICAL_VARIANCE_THRESHOLD: dict[str, Decimal] = {
    "payout_amount_mismatch":   Decimal("1000"),
    "overcharge_referral_fee":  Decimal("500"),
    "overcharge_fba_fee":       Decimal("2000"),
    "penalty_mismatch":         Decimal("5000"),
}


def score_severity(candidate: DiscrepancyCandidate) -> str:
    """Return the effective severity for a single discrepancy candidate."""
    dtype = candidate.discrepancy_type.lower()

    if dtype in _ALWAYS_CRITICAL:
        return "critical"

    if dtype in _ALWAYS_INFO:
        return "info"

    variance = abs(candidate.variance_amount or _ZERO)
    threshold = _CRITICAL_VARIANCE_THRESHOLD.get(dtype)
    if threshold is not None and variance >= threshold:
        return "critical"

    return candidate.severity


def apply_scoring(candidates: list[DiscrepancyCandidate]) -> None:
    """Apply variance-aware scoring in-place to all candidates."""
    for c in candidates:
        c.severity = score_severity(c)
