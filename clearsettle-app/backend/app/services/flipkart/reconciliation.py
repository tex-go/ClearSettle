"""
Flipkart Settlement Reconciliation Engine.

For each order row, computes:
  Expected = Gross Amount - Commission - Shipping - Reverse Shipping - Other Fees
  Variance = Expected - Actual Settlement Amount

Detects:
  missing_settlement      — delivered but no settlement
  partial_settlement      — settled < 90% of expected (critical)
  mismatch                — variance > 5% of expected (warning)
  delayed_payout          — settlement > 15 days after order
  excess_deduction        — total fees > 40% of gross
  wallet_redeem           — 'Wallet Redeem' deduction (not a standard fee)
  fixed_fee_anomaly       — fixed fee per order > Rs.30 (vs normal Rs.3-10)
  reverse_shipping_audit  — reverse shipping on misshipment/platform-error returns
  commission_mismatch     — actual commission != rate × sale_amount
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

DELAY_THRESHOLD_DAYS     = 15
PARTIAL_THRESHOLD        = Decimal("0.90")   # settled < 90% of expected → critical
MISMATCH_THRESHOLD_PCT   = Decimal("0.05")   # variance > 5% → warning
EXCESS_FEE_RATIO         = Decimal("0.40")   # fees > 40% of gross → warning
FIXED_FEE_ANOMALY_THRESH = Decimal("30")     # > Rs.30/order fixed fee triggers review
REVERSE_SHIP_HIGH_THRESH = Decimal("200")    # > Rs.200/return triggers audit

# Fee names that are NOT standard Flipkart seller deductions
SUSPECT_FEE_NAMES: frozenset = frozenset(["wallet redeem"])


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


def run_payment_report_reconciliation(
    order_rows: List[Dict[str, Any]],
    gst_rows: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Extended reconciliation for quarterly Payment Report data.
    Uses richer per-order fields from payment_parser.

    Detects payment-report-specific issues on top of base reconciliation:
      - wallet_redeem:         suspect fee in GST_Details
      - fixed_fee_anomaly:     per-order fixed fee abnormally high
      - high_reverse_shipping: reverse shipping > Rs.200/return
      - commission_mismatch:   actual comm != rate × sale_amount
    """
    issues: List[Dict[str, Any]] = []
    gst_rows = gst_rows or []

    # ── Wallet Redeem (aggregate across all GST rows) ───────────────────────
    wallet_rows = [r for r in gst_rows if (r.get("fee_name") or "").lower().strip() in SUSPECT_FEE_NAMES]
    if wallet_rows:
        total_wallet = sum(abs(float(r.get("fee_amount", 0))) for r in wallet_rows)
        total_gst    = sum(abs(float(r.get("gst_amount", 0))) for r in wallet_rows)
        affected_ids = [r.get("order_item_id") for r in wallet_rows if r.get("order_item_id")]
        issues.append({
            "issue_type":      "wallet_redeem",
            "severity":        "critical",
            "order_id":        affected_ids[0] if affected_ids else "MULTIPLE",
            "sku_code":        None,
            "expected_amount": 0.0,
            "actual_amount":   -total_wallet,
            "variance":        total_wallet + total_gst,
            "description":     (
                f"'Wallet Redeem' deduction ₹{total_wallet:,.2f} (+ ₹{total_gst:,.2f} GST) "
                f"across {len(wallet_rows)} transactions. Not a standard Flipkart seller fee. "
                "Raise seller support dispute immediately."
            ),
        })

    # ── Per-order checks ────────────────────────────────────────────────────
    for row in order_rows:
        order_id = str(row.get("order_item_id") or row.get("order_id") or "").strip() or "unknown"
        sku      = row.get("seller_sku") or row.get("sku_code")
        fixed    = _d(row.get("fixed_fee", 0))
        rship    = _d(row.get("reverse_shipping_fee", 0))
        comm     = _d(row.get("commission", 0))
        comm_rate = _d(row.get("commission_rate_pct", 0))
        sale     = _d(row.get("sale_amount", 0))

        # ── Fixed fee anomaly ──────────────────────────────────────────────
        if abs(fixed) > FIXED_FEE_ANOMALY_THRESH:
            issues.append({
                "issue_type":      "fixed_fee_anomaly",
                "severity":        "warning",
                "order_id":        order_id,
                "sku_code":        sku,
                "expected_amount": float(FIXED_FEE_ANOMALY_THRESH),
                "actual_amount":   float(abs(fixed)),
                "variance":        float(abs(fixed) - FIXED_FEE_ANOMALY_THRESH),
                "description":     (
                    f"Order {order_id}: fixed fee ₹{float(abs(fixed)):,.2f} > threshold ₹{float(FIXED_FEE_ANOMALY_THRESH):,.0f}. "
                    "Verify against Flipkart published Fixed Fee slab for this category."
                ),
            })

        # ── High reverse shipping ──────────────────────────────────────────
        if abs(rship) > REVERSE_SHIP_HIGH_THRESH:
            issues.append({
                "issue_type":      "high_reverse_shipping",
                "severity":        "warning",
                "order_id":        order_id,
                "sku_code":        sku,
                "expected_amount": float(REVERSE_SHIP_HIGH_THRESH),
                "actual_amount":   float(abs(rship)),
                "variance":        float(abs(rship) - REVERSE_SHIP_HIGH_THRESH),
                "description":     (
                    f"Order {order_id}: reverse shipping ₹{float(abs(rship)):,.2f} > threshold. "
                    "Validate return reason: misshipment/platform-error returns are not seller liability."
                ),
            })

        # ── Commission rate mismatch ───────────────────────────────────────
        if sale > 0 and comm_rate > 0 and abs(comm) > 0:
            expected_comm = -(sale * comm_rate / Decimal("100"))
            comm_var = abs(comm - expected_comm)
            if comm_var > Decimal("1"):  # Rs.1 tolerance
                issues.append({
                    "issue_type":      "commission_mismatch",
                    "severity":        "warning",
                    "order_id":        order_id,
                    "sku_code":        sku,
                    "expected_amount": float(expected_comm),
                    "actual_amount":   float(comm),
                    "variance":        float(comm_var),
                    "description":     (
                        f"Order {order_id}: commission ₹{float(comm):,.2f} vs expected "
                        f"₹{float(expected_comm):,.2f} at {float(comm_rate):.2f}% rate."
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
