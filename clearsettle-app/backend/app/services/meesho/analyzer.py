"""
Meesho Payment Report analyzer.

Computes summary KPIs from order rows returned by the parser.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional


def _d(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _pct(num: Decimal, den: Decimal) -> Optional[float]:
    if den == 0:
        return None
    return float((num / den * 100).quantize(Decimal("0.001")))


def build_meesho_summary(order_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate order rows into a summary dict matching MeeshoSummary ORM fields.
    """
    total_orders = delivered = returned = cancelled = pending = 0

    gross_sales          = Decimal("0")
    customer_paid_total  = Decimal("0")
    returns_value        = Decimal("0")
    cancellations_value  = Decimal("0")
    commission           = Decimal("0")
    shipping_charges     = Decimal("0")
    reverse_shipping     = Decimal("0")
    gst_on_commission    = Decimal("0")
    tcs                  = Decimal("0")
    net_payments         = Decimal("0")

    for row in order_rows:
        status = (row.get("order_status") or "").lower().strip()
        pstatus = (row.get("payment_status") or "").lower().strip()
        cp = _d(row.get("customer_paid"))
        net = _d(row.get("net_payment"))
        mrp = _d(row.get("mrp"))

        total_orders += 1
        customer_paid_total += cp
        gross_sales += mrp if mrp > 0 else cp

        commission        += _d(row.get("commission"))
        shipping_charges  += _d(row.get("shipping_charges"))
        reverse_shipping  += _d(row.get("reverse_shipping"))
        gst_on_commission += _d(row.get("gst_on_commission"))
        tcs               += _d(row.get("tcs"))
        net_payments      += net

        if "return" in status or "rto" in status:
            returned += 1
            returns_value += cp
        elif "cancel" in status:
            cancelled += 1
            cancellations_value += cp
        elif "deliver" in status or "complete" in status:
            delivered += 1
        else:
            pending += 1

    net_sales = customer_paid_total - returns_value - cancellations_value
    total_deductions = commission + shipping_charges + reverse_shipping + gst_on_commission + tcs

    # Determine pending vs paid
    amount_paid = Decimal("0")
    amount_pending = Decimal("0")
    for row in order_rows:
        pstatus = (row.get("payment_status") or "").lower()
        net = _d(row.get("net_payment"))
        if "paid" in pstatus or "credit" in pstatus or "settled" in pstatus:
            amount_paid += net
        else:
            amount_pending += net

    return {
        "gross_sales":             float(gross_sales),
        "customer_paid_total":     float(customer_paid_total),
        "returns_value":           float(returns_value),
        "cancellations_value":     float(cancellations_value),
        "net_sales":               float(net_sales),
        "commission":              float(commission),
        "shipping_charges":        float(shipping_charges),
        "reverse_shipping":        float(reverse_shipping),
        "gst_on_commission":       float(gst_on_commission),
        "tcs":                     float(tcs),
        "other_deductions":        0.0,
        "total_deductions":        float(total_deductions),
        "net_earnings":            float(net_payments),
        "amount_paid":             float(amount_paid),
        "amount_pending":          float(amount_pending),
        "total_orders":            total_orders,
        "delivered_orders":        delivered,
        "returned_orders":         returned,
        "cancelled_orders":        cancelled,
        "pending_orders":          pending,
        "return_rate_pct":         _pct(Decimal(str(returned)), Decimal(str(total_orders))),
        "cancellation_rate_pct":   _pct(Decimal(str(cancelled)), Decimal(str(total_orders))),
        "effective_commission_pct": _pct(abs(commission), customer_paid_total) if customer_paid_total > 0 else None,
    }


def compute_meesho_order_analytics(order_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compute expected_net and payment_variance for each order row.

    expected_net = customer_paid - commission - shipping - reverse_shipping - gst_on_commission - tcs
    payment_variance = net_payment - expected_net
    """
    enriched = []
    for row in order_rows:
        cp    = float(row.get("customer_paid") or 0)
        comm  = float(row.get("commission") or 0)
        ship  = float(row.get("shipping_charges") or 0)
        rev   = float(row.get("reverse_shipping") or 0)
        gst   = float(row.get("gst_on_commission") or 0)
        tcs   = float(row.get("tcs") or 0)
        net   = float(row.get("net_payment") or 0)

        expected_net = cp + comm + ship + rev + gst + tcs  # fees are negative
        variance = round(net - expected_net, 2)

        enriched.append({
            **row,
            "expected_net":     round(expected_net, 2),
            "payment_variance": variance,
        })
    return enriched
