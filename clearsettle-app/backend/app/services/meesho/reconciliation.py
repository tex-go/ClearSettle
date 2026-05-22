"""
Meesho Payment Reconciliation Engine.

Detects:
  payment_variance       — net_payment differs from expected_net
  excess_deduction       — total deductions > 30% of customer paid
  return_deduction_mismatch — return order has unexpected deductions
  tcs_overcharge         — TCS > 1% of customer paid
  missing_payment        — delivered order with zero net payment
  shipping_overcharge    — forward + reverse shipping > expected flat rate threshold
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

VARIANCE_WARN_PCT  = Decimal("0.05")
VARIANCE_CRIT_PCT  = Decimal("0.15")
EXCESS_FEE_WARN    = Decimal("0.30")
EXCESS_FEE_CRIT    = Decimal("0.50")
TCS_EXPECTED_RATE  = Decimal("0.01")   # 1%
TCS_TOLERANCE      = Decimal("0.005")
SHIPPING_THRESHOLD = Decimal("100")    # ₹100 per shipment as rough upper bound


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


def run_meesho_reconciliation(order_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run reconciliation on enriched order rows (output of compute_meesho_order_analytics).
    Returns list of issue dicts ready for MeeshoReconIssue insertion.
    """
    issues: List[Dict[str, Any]] = []

    for row in order_rows:
        order_id  = row.get("order_id") or ""
        sku       = row.get("sku")
        cp        = _d(row.get("customer_paid"))
        net       = _d(row.get("net_payment"))
        expected  = _d(row.get("expected_net"))
        variance  = _d(row.get("payment_variance"))
        comm      = _d(row.get("commission"))
        ship      = _d(row.get("shipping_charges"))
        rev_ship  = _d(row.get("reverse_shipping"))
        gst       = _d(row.get("gst_on_commission"))
        tcs       = _d(row.get("tcs"))
        o_status  = (row.get("order_status") or "").lower()
        p_status  = (row.get("payment_status") or "").lower()

        # ── 1. Payment variance ────────────────────────────────────────────
        if expected != 0 and abs(variance) > Decimal("1"):
            pct = _pct_var(expected, net)
            if pct and pct >= VARIANCE_CRIT_PCT:
                issues.append({
                    "issue_type":       "payment_variance",
                    "severity":         "critical",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(expected),
                    "actual_amount":    float(net),
                    "variance":         float(variance),
                    "description":      f"Net payment ₹{float(net):.2f} deviates {float(pct)*100:.1f}% from expected ₹{float(expected):.2f}",
                })
            elif pct and pct >= VARIANCE_WARN_PCT:
                issues.append({
                    "issue_type":       "payment_variance",
                    "severity":         "warning",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(expected),
                    "actual_amount":    float(net),
                    "variance":         float(variance),
                    "description":      f"Net payment ₹{float(net):.2f} deviates {float(pct)*100:.1f}% from expected ₹{float(expected):.2f}",
                })

        # ── 2. Excess deductions ───────────────────────────────────────────
        if cp > 0:
            total_deductions = abs(comm) + abs(ship) + abs(rev_ship) + abs(gst) + abs(tcs)
            ded_ratio = total_deductions / cp
            if ded_ratio >= EXCESS_FEE_CRIT:
                issues.append({
                    "issue_type":       "excess_deduction",
                    "severity":         "critical",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(cp * EXCESS_FEE_WARN),
                    "actual_amount":    float(total_deductions),
                    "variance":         float(total_deductions - cp * EXCESS_FEE_WARN),
                    "description":      f"Deductions ₹{float(total_deductions):.2f} are {float(ded_ratio)*100:.1f}% of customer paid ₹{float(cp):.2f}",
                })
            elif ded_ratio >= EXCESS_FEE_WARN:
                issues.append({
                    "issue_type":       "excess_deduction",
                    "severity":         "warning",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(cp * EXCESS_FEE_WARN),
                    "actual_amount":    float(total_deductions),
                    "variance":         float(total_deductions - cp * EXCESS_FEE_WARN),
                    "description":      f"Deductions ₹{float(total_deductions):.2f} are {float(ded_ratio)*100:.1f}% of customer paid",
                })

        # ── 3. Missing payment ─────────────────────────────────────────────
        if ("deliver" in o_status or "complete" in o_status) and net == 0 and cp > 0:
            issues.append({
                "issue_type":       "missing_payment",
                "severity":         "critical",
                "order_id":         order_id,
                "sku":              sku,
                "expected_amount":  float(cp),
                "actual_amount":    0.0,
                "variance":         float(cp),
                "description":      f"Delivered order with customer paid ₹{float(cp):.2f} has zero net payment",
            })

        # ── 4. TCS overcharge ──────────────────────────────────────────────
        if cp > 0 and tcs < 0:
            actual_tcs_rate = abs(tcs) / cp
            diff = abs(actual_tcs_rate - TCS_EXPECTED_RATE)
            if diff > TCS_TOLERANCE:
                issues.append({
                    "issue_type":       "tcs_overcharge",
                    "severity":         "warning",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  float(cp * TCS_EXPECTED_RATE),
                    "actual_amount":    float(abs(tcs)),
                    "variance":         float(abs(tcs) - cp * TCS_EXPECTED_RATE),
                    "description":      f"TCS ₹{float(abs(tcs)):.2f} ({float(actual_tcs_rate)*100:.2f}%) is outside expected ~1% of ₹{float(cp):.2f}",
                })

        # ── 5. Return deduction mismatch ───────────────────────────────────
        if ("return" in o_status or "rto" in o_status) and rev_ship == 0:
            if abs(ship) > 0:
                issues.append({
                    "issue_type":       "return_deduction_mismatch",
                    "severity":         "warning",
                    "order_id":         order_id,
                    "sku":              sku,
                    "expected_amount":  0.0,
                    "actual_amount":    float(abs(ship)),
                    "variance":         float(abs(ship)),
                    "description":      f"Forward shipping ₹{float(abs(ship)):.2f} charged on returned order without reverse shipping",
                })

        # ── 6. Shipping overcharge ─────────────────────────────────────────
        total_ship = abs(ship) + abs(rev_ship)
        if total_ship > SHIPPING_THRESHOLD and cp > 0:
            issues.append({
                "issue_type":       "shipping_overcharge",
                "severity":         "warning",
                "order_id":         order_id,
                "sku":              sku,
                "expected_amount":  float(SHIPPING_THRESHOLD),
                "actual_amount":    float(total_ship),
                "variance":         float(total_ship - SHIPPING_THRESHOLD),
                "description":      f"Shipping charges ₹{float(total_ship):.2f} exceed expected threshold of ₹{float(SHIPPING_THRESHOLD):.0f}",
            })

    return issues
