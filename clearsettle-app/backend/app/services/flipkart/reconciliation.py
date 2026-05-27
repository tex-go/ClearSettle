"""
Flipkart Settlement Reconciliation Engine.

For each order row, computes:
  Expected = Gross Amount - Commission - Shipping - Reverse Shipping - Other Fees
  Variance = Expected - Actual Settlement Amount

Detects:
  missing_settlement  — delivered but no settlement
  partial_settlement  — settled < 90% of expected (critical)
  mismatch            — variance > 5% of expected (warning)
  delayed_payout      — settlement > 15 days after order
  excess_deduction    — total fees > 40% of gross
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

DELAY_THRESHOLD_DAYS   = 15
PARTIAL_THRESHOLD      = Decimal("0.90")   # settled < 90% of expected → critical
MISMATCH_THRESHOLD_PCT = Decimal("0.05")   # variance > 5% → warning
EXCESS_FEE_RATIO       = Decimal("0.40")   # fees > 40% of gross → warning


def _d(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _parse_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _pct_var(expected: Decimal, actual: Decimal) -> Optional[Decimal]:
    if expected == 0:
        return None
    return abs(expected - actual) / abs(expected)


def run_reconciliation(order_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run full reconciliation on order rows.
    Returns list of issue dicts (ready for DB insertion).
    """
    issues: List[Dict[str, Any]] = []

    for row in order_rows:
        order_id = str(row.get("order_id") or "").strip() or "unknown"
        sku      = row.get("sku_code")
        status   = (row.get("status") or "").lower().strip()
        sett_s   = (row.get("settlement_status") or "").lower().strip()

        gross    = _d(row.get("gross_amount"))
        comm     = _d(row.get("commission"))
        ship     = _d(row.get("shipping_charges"))
        rship    = _d(row.get("reverse_shipping"))
        other    = _d(row.get("other_fees"))
        earn     = _d(row.get("net_earnings"))
        sett_amt = _d(row.get("settlement_amount"))
        expected = _d(row.get("expected_settlement"))
        variance = _d(row.get("settlement_variance"))

        order_dt = _parse_date(row.get("order_date"))
        sett_dt  = _parse_date(row.get("settlement_date"))

        total_fees = abs(comm) + abs(ship) + abs(rship) + abs(other)

        # Skip cancelled orders — no settlement expected
        if status in ("cancelled", "cancel"):
            continue

        # ── 1. Missing settlement ──────────────────────────────────────────
        if sett_amt == 0 and sett_s in ("pending", "unsettled", ""):
            if status in ("delivered", "returned", "return"):
                exp_val = expected if expected != 0 else (gross - total_fees)
                issues.append({
                    "issue_type":      "missing_settlement",
                    "severity":        "critical",
                    "order_id":        order_id,
                    "sku_code":        sku,
                    "expected_amount": float(exp_val),
                    "actual_amount":   0.0,
                    "variance":        float(exp_val),
                    "description":     f"Order {order_id}: status='{status}' but no settlement record found.",
                })
            continue

        # ── 2. Excess deduction ────────────────────────────────────────────
        if gross > 0 and total_fees / gross > EXCESS_FEE_RATIO:
            issues.append({
                "issue_type":      "excess_deduction",
                "severity":        "warning",
                "order_id":        order_id,
                "sku_code":        sku,
                "expected_amount": float(gross * (1 - EXCESS_FEE_RATIO)),
                "actual_amount":   float(total_fees),
                "variance":        float(total_fees - gross * EXCESS_FEE_RATIO),
                "description":     (
                    f"Order {order_id}: fees are {float(total_fees/gross*100):.1f}% of gross "
                    f"(threshold {float(EXCESS_FEE_RATIO)*100:.0f}%)."
                ),
            })

        # ── 3. Delayed payout ──────────────────────────────────────────────
        if order_dt and sett_dt:
            days = (sett_dt - order_dt).days
            if days > DELAY_THRESHOLD_DAYS:
                issues.append({
                    "issue_type":      "delayed_payout",
                    "severity":        "warning",
                    "order_id":        order_id,
                    "sku_code":        sku,
                    "expected_amount": float(expected),
                    "actual_amount":   float(sett_amt),
                    "variance":        None,
                    "description":     f"Order {order_id}: settled {days} days after order (threshold {DELAY_THRESHOLD_DAYS} days).",
                })

        if expected == 0 or sett_amt == 0:
            continue

        pct = _pct_var(expected, sett_amt)
        if pct is None:
            continue

        # ── 4. Partial settlement ──────────────────────────────────────────
        if sett_amt < expected * PARTIAL_THRESHOLD:
            issues.append({
                "issue_type":      "partial_settlement",
                "severity":        "critical",
                "order_id":        order_id,
                "sku_code":        sku,
                "expected_amount": float(expected),
                "actual_amount":   float(sett_amt),
                "variance":        float(variance),
                "description":     (
                    f"Order {order_id}: received ₹{float(sett_amt):,.2f} "
                    f"vs expected ₹{float(expected):,.2f} ({float(pct)*100:.1f}% gap)."
                ),
            })

        # ── 5. Mismatch (smaller variance, not partial) ────────────────────
        elif pct > MISMATCH_THRESHOLD_PCT:
            issues.append({
                "issue_type":      "mismatch",
                "severity":        "warning",
                "order_id":        order_id,
                "sku_code":        sku,
                "expected_amount": float(expected),
                "actual_amount":   float(sett_amt),
                "variance":        float(variance),
                "description":     (
                    f"Order {order_id}: settlement variance ₹{float(variance):,.2f} "
                    f"({float(pct)*100:.1f}%)."
                ),
            })

    return issues


def compute_recon_summary(
    issues: List[Dict[str, Any]],
    order_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate reconciliation stats for the report header."""
    delivered = sum(1 for r in order_rows if (r.get("status") or "").lower() == "delivered")
    settled   = sum(1 for r in order_rows if (r.get("settlement_status") or "").lower() in ("settled", "paid", "remitted"))

    type_counts: Dict[str, int]   = {}
    type_amounts: Dict[str, float]= {}
    for iss in issues:
        t = iss["issue_type"]
        type_counts[t]  = type_counts.get(t, 0) + 1
        v = iss.get("variance") or iss.get("expected_amount") or 0
        type_amounts[t] = type_amounts.get(t, 0.0) + abs(float(v))

    total_variance = sum(
        abs(float(i.get("variance") or i.get("expected_amount") or 0))
        for i in issues
    )

    return {
        "total_orders":       len(order_rows),
        "delivered_orders":   delivered,
        "settled_orders":     settled,
        "total_issues":       len(issues),
        "critical_issues":    sum(1 for i in issues if i["severity"] == "critical"),
        "warning_issues":     sum(1 for i in issues if i["severity"] == "warning"),
        "total_variance_amount": round(total_variance, 2),
        "issues_by_type": [
            {"type": t, "count": type_counts[t], "amount": round(type_amounts[t], 2)}
            for t in sorted(type_counts, key=lambda k: type_amounts[k], reverse=True)
        ],
    }
