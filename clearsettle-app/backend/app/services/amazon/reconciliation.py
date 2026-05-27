"""
Amazon Settlement Reconciliation Engine.

Detects:
  settlement_variance    — net_amount differs significantly from expected_net
  excess_deduction       — total fees exceed 30% of gross (warning) or 50% (critical)
  refund_anomaly         — refund with no matching order or unusually large refund
  missing_settlement     — order with gross > 0 but net = 0 (no payout)
  unaccounted_adjustment — transaction type = Adjustment with large amount
  withheld_tax_anomaly   — TCS deduction significantly over expected 1% rate
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

VARIANCE_WARN_PCT    = Decimal("0.05")   # 5% variance → warning
VARIANCE_CRIT_PCT    = Decimal("0.15")   # 15% variance → critical
EXCESS_FEE_WARN      = Decimal("0.30")   # fees > 30% of gross → warning
EXCESS_FEE_CRIT      = Decimal("0.50")   # fees > 50% of gross → critical
TCS_EXPECTED_RATE    = Decimal("0.01")   # 1% TCS expected
TCS_TOLERANCE        = Decimal("0.005")  # ±0.5% tolerance


def _d(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _pct_var(expected: Decimal, actual: Decimal) -> Optional[Decimal]:
    if expected == 0:
        return None
    return abs(expected - actual) / abs(expected)


def run_amazon_reconciliation(order_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run reconciliation on enriched order rows (output of compute_amazon_order_analytics).
    Returns list of issue dicts ready for AmazonReconIssue insertion.
    """
    issues: List[Dict[str, Any]] = []

    for row in order_rows:
        order_id = row.get("order_id") or ""
        sku      = row.get("sku")
        gross    = _d(row.get("gross_amount"))
        net      = _d(row.get("net_amount"))
        expected = _d(row.get("expected_net"))
        txn_type = (row.get("transaction_type") or "").lower()
        comm     = _d(row.get("commission"))
        fba      = _d(row.get("fba_fee"))
        ship     = _d(row.get("shipping_fee"))
        tax      = _d(row.get("withheld_tax"))
        other    = _d(row.get("other_fees"))
        variance = _d(row.get("settlement_variance"))

        # ── 1. Settlement variance ─────────────────────────────────────────
        if expected != 0 and abs(variance) > 0:
            pct = _pct_var(expected, net)
            if pct and pct >= VARIANCE_CRIT_PCT:
                issues.append({
                    "issue_type":       "settlement_variance",
                    "severity":         "critical",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(expected),
                    "actual_amount":    float(net),
                    "variance":         float(variance),
                    "description":      f"Net payout ₹{float(net):.2f} deviates {float(pct)*100:.1f}% from expected ₹{float(expected):.2f}",
                })
            elif pct and pct >= VARIANCE_WARN_PCT:
                issues.append({
                    "issue_type":       "settlement_variance",
                    "severity":         "warning",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(expected),
                    "actual_amount":    float(net),
                    "variance":         float(variance),
                    "description":      f"Net payout ₹{float(net):.2f} deviates {float(pct)*100:.1f}% from expected ₹{float(expected):.2f}",
                })

        # ── 2. Excess deductions ───────────────────────────────────────────
        if gross > 0:
            total_fees = abs(comm) + abs(fba) + abs(ship) + abs(tax) + abs(other)
            fee_ratio  = total_fees / gross
            if fee_ratio >= EXCESS_FEE_CRIT:
                issues.append({
                    "issue_type":       "excess_deduction",
                    "severity":         "critical",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(gross * EXCESS_FEE_CRIT),
                    "actual_amount":    float(total_fees),
                    "variance":         float(total_fees - gross * EXCESS_FEE_WARN),
                    "description":      f"Total fees ₹{float(total_fees):.2f} are {float(fee_ratio)*100:.1f}% of gross ₹{float(gross):.2f} (expected <30%)",
                })
            elif fee_ratio >= EXCESS_FEE_WARN:
                issues.append({
                    "issue_type":       "excess_deduction",
                    "severity":         "warning",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(gross * EXCESS_FEE_WARN),
                    "actual_amount":    float(total_fees),
                    "variance":         float(total_fees - gross * EXCESS_FEE_WARN),
                    "description":      f"Total fees ₹{float(total_fees):.2f} are {float(fee_ratio)*100:.1f}% of gross ₹{float(gross):.2f}",
                })

        # ── 3. Missing settlement ──────────────────────────────────────────
        if gross > 0 and net == 0 and "refund" not in txn_type and "adjustment" not in txn_type:
            issues.append({
                "issue_type":       "missing_settlement",
                "severity":         "critical",
                "order_id":         order_id,
                "sku":              sku,
                "expected_amount":  float(gross),
                "actual_amount":    0.0,
                "variance":         float(gross),
                "description":      f"Order has gross revenue ₹{float(gross):.2f} but net payout is ₹0",
            })

        # ── 4. TCS anomaly ─────────────────────────────────────────────────
        if gross > 0 and tax < 0:
            actual_tcs_rate = abs(tax) / gross
            diff = abs(actual_tcs_rate - TCS_EXPECTED_RATE)
            if diff > TCS_TOLERANCE:
                issues.append({
                    "issue_type":       "tcs_mismatch",
                    "severity":         "warning",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(gross * TCS_EXPECTED_RATE),
                    "actual_amount":    float(abs(tax)),
                    "variance":         float(abs(tax) - gross * TCS_EXPECTED_RATE),
                    "description":      f"TCS deducted ₹{float(abs(tax)):.2f} ({float(actual_tcs_rate)*100:.2f}% of gross); expected ~1%",
                })

        # ── 5. Refund anomaly ──────────────────────────────────────────────
        if "refund" in txn_type and abs(gross) > Decimal("5000"):
            issues.append({
                "issue_type":       "refund_anomaly",
                "severity":         "warning",
                "order_id":         order_id,
                "sku":              sku,
                "expected_amount":  None,
                "actual_amount":    float(abs(gross)),
                "variance":         float(abs(gross)),
                "description":      f"Large refund detected: ₹{float(abs(gross)):.2f} for order {order_id}",
            })

        # ── 6. Unaccounted adjustment ──────────────────────────────────────
        if "adjustment" in txn_type and abs(net) > Decimal("1000"):
            issues.append({
                "issue_type":       "unaccounted_adjustment",
                "severity":         "warning",
                "order_id":         order_id,
                "sku":              sku,
                "expected_amount":  0.0,
                "actual_amount":    float(net),
                "variance":         float(abs(net)),
                "description":      f"Unaccounted adjustment of ₹{float(abs(net)):.2f} on order {order_id}",
            })

    return issues
