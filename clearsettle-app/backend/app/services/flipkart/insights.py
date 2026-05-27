"""
Automated insight generation for Flipkart P&L reports.

Generates natural-language insights like:
  "42% return rate detected on SKU XYZ"
  "Settlement delayed more than 15 days for 12 orders"
  "3 SKUs are loss-making — combined loss of ₹12,450"
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List


def _d(val: Any) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


def _fmt_inr(amount: Any) -> str:
    try:
        return f"₹{abs(float(amount)):,.0f}"
    except Exception:
        return "₹0"


def generate_insights(
    summary: Dict[str, Any],
    sku_rows: List[Dict[str, Any]],
    recon_issues: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Returns list of insight dicts:
      { type: "critical"|"warning"|"info"|"positive",
        category: str,
        message: str,
        icon: str,
        data: Any (optional) }
    """
    insights: List[Dict[str, Any]] = []

    gross       = _d(summary.get("gross_sales"))
    net_earn    = _d(summary.get("net_earnings"))
    return_rate = _d(summary.get("return_rate_pct"))
    cancel_rate = _d(summary.get("cancellation_rate_pct"))
    margin      = _d(summary.get("profit_margin_pct"))
    pending     = _d(summary.get("amount_pending"))
    settled     = _d(summary.get("amount_settled"))
    rev_ship    = abs(_d(summary.get("reverse_shipping")))
    returns_val = abs(_d(summary.get("returns")))
    commission  = abs(_d(summary.get("commission")))
    total_fees  = _d(summary.get("total_fees"))

    # ── Return rate ───────────────────────────────────────────────────────────
    if return_rate >= Decimal("30"):
        insights.append({
            "type": "critical", "category": "returns", "icon": "↩️",
            "message": f"Critical return rate: {float(return_rate):.1f}% — 3× industry average. Investigate product quality, listing accuracy, and sizing guides.",
        })
    elif return_rate >= Decimal("15"):
        insights.append({
            "type": "warning", "category": "returns", "icon": "↩️",
            "message": f"{float(return_rate):.1f}% return rate detected — above the 10% benchmark. Review top-returned SKUs.",
        })
    elif return_rate > 0 and return_rate < Decimal("8"):
        insights.append({
            "type": "positive", "category": "returns", "icon": "✅",
            "message": f"Return rate is healthy at {float(return_rate):.1f}% — below the 10% benchmark.",
        })

    # ── Cancellation rate ─────────────────────────────────────────────────────
    if cancel_rate >= Decimal("15"):
        insights.append({
            "type": "warning", "category": "cancellations", "icon": "❌",
            "message": f"High cancellation rate: {float(cancel_rate):.1f}%. Check stock availability, delivery SLAs, and pricing competitiveness.",
        })

    # ── Profit margin ─────────────────────────────────────────────────────────
    if margin < Decimal("3") and gross > 0:
        insights.append({
            "type": "critical", "category": "profitability", "icon": "📉",
            "message": f"Profit margin is critically low at {float(margin):.1f}%. Immediate review of pricing strategy and fee-heavy categories required.",
        })
    elif margin < Decimal("10") and gross > 0:
        insights.append({
            "type": "warning", "category": "profitability", "icon": "💰",
            "message": f"Low profit margin: {float(margin):.1f}%. Consider delisting loss-making SKUs or renegotiating shipping rates.",
        })
    elif margin >= Decimal("20") and gross > 0:
        insights.append({
            "type": "positive", "category": "profitability", "icon": "🏆",
            "message": f"Strong profit margin of {float(margin):.1f}% — outperforming typical marketplace margins.",
        })

    # ── Loss-making SKUs ──────────────────────────────────────────────────────
    loss_skus = [r for r in sku_rows if _d(r.get("net_earnings") or 0) < 0]
    if loss_skus:
        total_loss = sum(_d(r.get("net_earnings") or 0) for r in loss_skus)
        loss_codes = [r.get("sku_code") for r in loss_skus[:5]]
        insights.append({
            "type": "critical", "category": "sku_profitability", "icon": "🔴",
            "message": f"{len(loss_skus)} SKU(s) are loss-making with a combined loss of {_fmt_inr(abs(total_loss))}. Consider delisting or repricing.",
            "data": loss_codes,
        })

    # ── High return rate individual SKUs ──────────────────────────────────────
    high_ret = sorted(
        [r for r in sku_rows if _d(r.get("return_rate_pct") or 0) >= Decimal("35")],
        key=lambda r: _d(r.get("return_rate_pct") or 0),
        reverse=True,
    )[:3]
    for r in high_ret:
        rr = float(_d(r.get("return_rate_pct")))
        insights.append({
            "type": "warning", "category": "returns", "icon": "↩️",
            "message": f"{rr:.0f}% return rate on {r.get('sku_code', 'unknown SKU')} — check product description, images, or quality.",
        })

    # ── Reverse shipping vs returns ratio ─────────────────────────────────────
    if rev_ship > 0 and returns_val > 0:
        rev_ratio = rev_ship / returns_val
        if rev_ratio > Decimal("0.25"):
            insights.append({
                "type": "info", "category": "shipping", "icon": "🚚",
                "message": f"Reverse shipping costs are {float(rev_ratio*100):.0f}% of total return value ({_fmt_inr(rev_ship)}). Explore return logistics optimisation.",
            })

    # ── Commission as % of gross ──────────────────────────────────────────────
    if gross > 0 and commission > 0:
        comm_pct = commission / gross * Decimal("100")
        if comm_pct > Decimal("22"):
            insights.append({
                "type": "info", "category": "fees", "icon": "💳",
                "message": f"Platform commission is {float(comm_pct):.1f}% of gross sales ({_fmt_inr(commission)}). Shift product mix to lower-commission categories.",
            })

    # ── Pending settlement ────────────────────────────────────────────────────
    if pending > 0 and (settled + pending) > 0:
        pend_pct = pending / (settled + pending) * Decimal("100")
        if pend_pct > Decimal("20"):
            insights.append({
                "type": "warning", "category": "settlement", "icon": "⏳",
                "message": f"{_fmt_inr(pending)} ({float(pend_pct):.0f}% of expected earnings) is still pending settlement. Follow up with Flipkart Seller Support.",
            })

    # ── Reconciliation issues ─────────────────────────────────────────────────
    critical_recon = [i for i in recon_issues if i.get("severity") == "critical"]
    if critical_recon:
        at_risk = sum(
            abs(float(i.get("variance") or i.get("expected_amount") or 0))
            for i in critical_recon
        )
        insights.append({
            "type": "critical", "category": "reconciliation", "icon": "⚠️",
            "message": f"{len(critical_recon)} critical settlement issue(s) detected — {_fmt_inr(at_risk)} at risk. Raise disputes immediately.",
        })

    delayed = [i for i in recon_issues if i.get("issue_type") == "delayed_payout"]
    if delayed:
        insights.append({
            "type": "warning", "category": "reconciliation", "icon": "⏰",
            "message": f"{len(delayed)} order(s) had settlement delayed beyond 15 days. Monitor payout timelines.",
        })

    # Sort: critical first, then warning, then info/positive
    order_map = {"critical": 0, "warning": 1, "info": 2, "positive": 3}
    insights.sort(key=lambda x: order_map.get(x["type"], 9))

    return insights
