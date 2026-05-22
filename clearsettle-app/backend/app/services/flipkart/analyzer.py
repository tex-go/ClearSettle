"""
Analytics engine for parsed Flipkart P&L data.

Responsibilities:
  - Fill summary gaps from SKU/order row aggregates
  - Compute derived KPIs (margin %, return rate, fee ratios)
  - Build chart-ready data structures (fee breakdown, category mix)
  - Rank SKUs by profitability, return rate, cancellation rate
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional


def _d(val: Any) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


def _pct(num: Any, denom: Any, precision: int = 2) -> Optional[Decimal]:
    n, d = _d(num), _d(denom)
    if d == 0:
        return None
    return round(n / d * Decimal("100"), precision)


# ── Summary enrichment ────────────────────────────────────────────────────────

def enrich_summary(
    summary: Dict[str, Any],
    sku_rows: List[Dict[str, Any]],
    order_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Populate missing summary fields from row-level data,
    then compute all derived KPIs.
    """
    s = dict(summary)

    # Aggregate from SKU rows if summary sheet was absent
    if not s and sku_rows:
        s["gross_sales"]        = sum(_d(r.get("gross_sales"))           for r in sku_rows) or None
        s["returns"]            = sum(_d(r.get("returns_value"))         for r in sku_rows) or None
        s["cancellations"]      = sum(_d(r.get("cancellations_value"))   for r in sku_rows) or None
        s["net_sales"]          = sum(_d(r.get("net_sales"))             for r in sku_rows) or None
        s["commission"]         = sum(_d(r.get("commission"))            for r in sku_rows) or None
        s["shipping_charges"]   = sum(_d(r.get("shipping_charges"))      for r in sku_rows) or None
        s["reverse_shipping"]   = sum(_d(r.get("reverse_shipping"))      for r in sku_rows) or None
        s["other_fees"]         = sum(_d(r.get("other_fees"))            for r in sku_rows) or None
        s["net_earnings"]       = sum(_d(r.get("net_earnings"))          for r in sku_rows) or None
        s["total_orders"]       = sum((r.get("total_orders") or 0)       for r in sku_rows) or None

    # Aggregate from order rows if still nothing
    if not s and order_rows:
        s["gross_sales"]       = sum(_d(r.get("gross_amount"))       for r in order_rows) or None
        s["commission"]        = sum(_d(r.get("commission"))         for r in order_rows) or None
        s["shipping_charges"]  = sum(_d(r.get("shipping_charges"))   for r in order_rows) or None
        s["reverse_shipping"]  = sum(_d(r.get("reverse_shipping"))   for r in order_rows) or None
        s["other_fees"]        = sum(_d(r.get("other_fees"))         for r in order_rows) or None
        s["net_earnings"]      = sum(_d(r.get("net_earnings"))       for r in order_rows) or None

        settled_orders  = [r for r in order_rows if (r.get("settlement_status") or "").lower() in ("settled", "paid", "remitted")]
        pending_orders  = [r for r in order_rows if (r.get("settlement_status") or "").lower() in ("pending", "unsettled", "")]
        returned_orders = [r for r in order_rows if (r.get("status") or "").lower() in ("returned", "return")]
        cancelled_orders= [r for r in order_rows if (r.get("status") or "").lower() in ("cancelled", "cancel")]

        s["amount_settled"]          = sum(_d(r.get("settlement_amount")) for r in settled_orders) or None
        s["amount_pending"]          = sum(_d(r.get("expected_settlement") or r.get("gross_amount")) for r in pending_orders) or None
        s["total_orders"]            = len(order_rows)
        s["total_returned_orders"]   = len(returned_orders)
        s["total_cancelled_orders"]  = len(cancelled_orders)

    # Fill net_sales if missing
    if s.get("net_sales") is None:
        gross = _d(s.get("gross_sales"))
        ret   = _d(s.get("returns"))
        can   = _d(s.get("cancellations"))
        if gross:
            s["net_sales"] = gross - abs(ret) - abs(can)

    # Compute total_fees
    fee_fields = ["commission", "shipping_charges", "reverse_shipping",
                  "collection_fees", "fixed_fees", "gst_on_fees", "tcs", "tds", "other_fees"]
    total_fees = sum(abs(_d(s.get(f))) for f in fee_fields)
    if total_fees:
        s["total_fees"] = total_fees

    # Profit margin %
    gross = _d(s.get("gross_sales"))
    earn  = _d(s.get("net_earnings"))
    if gross and gross != 0:
        s["profit_margin_pct"] = round(earn / gross * Decimal("100"), 4)

    # Return / cancellation rates
    total  = s.get("total_orders") or 0
    rets   = s.get("total_returned_orders") or 0
    cans   = s.get("total_cancelled_orders") or 0
    if total > 0:
        if rets:
            s["return_rate_pct"] = round(Decimal(str(rets)) / Decimal(str(total)) * Decimal("100"), 3)
        if cans:
            s["cancellation_rate_pct"] = round(Decimal(str(cans)) / Decimal(str(total)) * Decimal("100"), 3)

    return s


# ── SKU analytics ─────────────────────────────────────────────────────────────

def compute_sku_analytics(sku_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich SKU rows with derived flags and sort by net_earnings desc.
    """
    enriched = []
    for row in sku_rows:
        r = dict(row)
        gross = _d(r.get("gross_sales"))
        earn  = _d(r.get("net_earnings"))

        # Fill margin if absent
        if r.get("margin_pct") is None and gross != 0:
            r["margin_pct"] = round(earn / gross * Decimal("100"), 4)

        r["is_loss_making"]   = bool(earn < 0)
        r["high_return_rate"] = bool(_d(r.get("return_rate_pct")) >= Decimal("20"))
        enriched.append(r)

    enriched.sort(key=lambda r: _d(r.get("net_earnings") or 0), reverse=True)
    return enriched


# ── Chart data builders ───────────────────────────────────────────────────────

def build_fee_breakdown(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pie-chart-ready fee breakdown."""
    fee_map = {
        "Commission":       summary.get("commission"),
        "Shipping":         summary.get("shipping_charges"),
        "Reverse Shipping": summary.get("reverse_shipping"),
        "Collection Fees":  summary.get("collection_fees"),
        "Fixed Fees":       summary.get("fixed_fees"),
        "GST on Services":  summary.get("gst_on_fees"),
        "TCS":              summary.get("tcs"),
        "TDS":              summary.get("tds"),
        "Other":            summary.get("other_fees"),
    }
    breakdown = [
        {"name": k, "value": float(abs(_d(v)))}
        for k, v in fee_map.items()
        if v is not None and _d(v) != 0
    ]
    breakdown.sort(key=lambda x: x["value"], reverse=True)
    return breakdown


def build_revenue_waterfall(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Waterfall chart: Gross Sales → deductions → Net Earnings.
    """
    steps = [
        {"name": "Gross Sales",       "value": float(_d(summary.get("gross_sales"))),       "type": "total"},
        {"name": "Returns",           "value": -float(abs(_d(summary.get("returns")))),      "type": "negative"},
        {"name": "Cancellations",     "value": -float(abs(_d(summary.get("cancellations")))), "type": "negative"},
        {"name": "Net Sales",         "value": float(_d(summary.get("net_sales"))),          "type": "subtotal"},
        {"name": "Commission",        "value": -float(abs(_d(summary.get("commission")))),   "type": "negative"},
        {"name": "Shipping",          "value": -float(abs(_d(summary.get("shipping_charges")))), "type": "negative"},
        {"name": "Reverse Shipping",  "value": -float(abs(_d(summary.get("reverse_shipping")))), "type": "negative"},
        {"name": "Taxes & Other",     "value": -float(abs(_d(summary.get("tcs"))) + abs(_d(summary.get("tds"))) + abs(_d(summary.get("gst_on_fees"))) + abs(_d(summary.get("other_fees")))), "type": "negative"},
        {"name": "Net Earnings",      "value": float(_d(summary.get("net_earnings"))),       "type": "total"},
    ]
    # Remove zero-value steps
    return [s for s in steps if abs(s["value"]) > 0.01]


def build_sku_chart_data(sku_rows: List[Dict[str, Any]], top_n: int = 15) -> Dict[str, Any]:
    """Top-N SKUs for bar charts."""
    sorted_by_earnings = sorted(sku_rows, key=lambda r: _d(r.get("net_earnings") or 0), reverse=True)
    sorted_by_returns  = sorted(sku_rows, key=lambda r: _d(r.get("return_rate_pct") or 0), reverse=True)

    def _sku_row(r: Dict) -> Dict:
        return {
            "sku":          r.get("sku_code", "Unknown"),
            "title":        (r.get("product_title") or r.get("sku_code") or "Unknown")[:30],
            "gross_sales":  float(_d(r.get("gross_sales"))),
            "net_earnings": float(_d(r.get("net_earnings"))),
            "margin_pct":   float(_d(r.get("margin_pct"))),
            "return_rate":  float(_d(r.get("return_rate_pct"))),
            "is_loss":      bool(r.get("is_loss_making")),
        }

    return {
        "top_profitable":  [_sku_row(r) for r in sorted_by_earnings[:top_n] if _d(r.get("net_earnings") or 0) >= 0],
        "top_loss_making": [_sku_row(r) for r in reversed(sorted_by_earnings) if _d(r.get("net_earnings") or 0) < 0][:top_n],
        "top_return_rate": [_sku_row(r) for r in sorted_by_returns[:top_n]],
    }


def build_category_breakdown(sku_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Category-level P&L breakdown."""
    cats: Dict[str, Dict[str, Decimal]] = {}
    for r in sku_rows:
        cat = r.get("category") or "Unknown"
        if cat not in cats:
            cats[cat] = {"gross": Decimal("0"), "earnings": Decimal("0"),
                         "returns": Decimal("0"), "orders": Decimal("0")}
        cats[cat]["gross"]    += _d(r.get("gross_sales"))
        cats[cat]["earnings"] += _d(r.get("net_earnings"))
        cats[cat]["returns"]  += abs(_d(r.get("returns_value")))
        cats[cat]["orders"]   += _d(r.get("total_orders"))

    result = []
    for cat, vals in cats.items():
        margin = round(vals["earnings"] / vals["gross"] * Decimal("100"), 2) if vals["gross"] else Decimal("0")
        result.append({
            "category":    cat,
            "gross_sales": float(vals["gross"]),
            "net_earnings":float(vals["earnings"]),
            "margin_pct":  float(margin),
            "returns":     float(vals["returns"]),
            "orders":      int(vals["orders"]),
        })

    result.sort(key=lambda x: x["gross_sales"], reverse=True)
    return result


def build_return_analysis(
    sku_rows: List[Dict[str, Any]],
    summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Return analytics with SKU ranking and category breakdown."""
    high_return = sorted(
        [r for r in sku_rows if _d(r.get("return_rate_pct") or 0) >= Decimal("10")],
        key=lambda r: _d(r.get("return_rate_pct") or 0),
        reverse=True,
    )

    cat_data: Dict[str, Dict[str, Decimal]] = {}
    for r in sku_rows:
        cat = r.get("category") or "Unknown"
        if cat not in cat_data:
            cat_data[cat] = {"ret_val": Decimal("0"), "gross": Decimal("0")}
        cat_data[cat]["ret_val"] += abs(_d(r.get("returns_value")))
        cat_data[cat]["gross"]   += _d(r.get("gross_sales"))

    cat_breakdown = sorted(
        [
            {
                "category":       cat,
                "return_value":   float(v["ret_val"]),
                "gross_sales":    float(v["gross"]),
                "return_rate_pct": float(round(v["ret_val"] / v["gross"] * Decimal("100"), 2)) if v["gross"] else 0,
            }
            for cat, v in cat_data.items()
        ],
        key=lambda x: x["return_value"],
        reverse=True,
    )

    return {
        "high_return_skus": [
            {
                "sku":            r.get("sku_code"),
                "title":          (r.get("product_title") or r.get("sku_code") or "")[:40],
                "return_rate_pct":float(_d(r.get("return_rate_pct"))),
                "returns_value":  float(_d(r.get("returns_value"))),
                "gross_sales":    float(_d(r.get("gross_sales"))),
            }
            for r in high_return[:10]
        ],
        "category_breakdown": cat_breakdown[:8],
        "overall_return_rate": float(_d(summary.get("return_rate_pct"))),
        "total_return_value":  float(abs(_d(summary.get("returns")))),
    }
