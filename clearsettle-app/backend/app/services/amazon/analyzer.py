"""
Amazon Settlement Report analyzer.

Computes summary KPIs from the pivoted order rows returned by the parser.
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


def _pct(numerator: Decimal, denominator: Decimal) -> Optional[float]:
    if denominator == 0:
        return None
    return float((numerator / denominator * 100).quantize(Decimal("0.001")))


def build_amazon_summary(meta: Dict[str, Any], order_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate order rows into a summary dict matching AmazonSummary ORM fields.
    """
    total_orders = 0
    total_refunded_orders = 0
    total_units = 0

    gross_sales   = Decimal("0")
    refunds       = Decimal("0")
    promotions    = Decimal("0")
    commission    = Decimal("0")
    fba_fees      = Decimal("0")
    shipping_fees = Decimal("0")
    withheld_tax  = Decimal("0")
    other_fees    = Decimal("0")
    net_total     = Decimal("0")

    for row in order_rows:
        txn = (row.get("transaction_type") or "").lower()
        gross = _d(row.get("gross_amount"))
        net   = _d(row.get("net_amount"))

        if "refund" in txn:
            total_refunded_orders += 1
            refunds += gross
        else:
            total_orders += 1
            gross_sales += gross

        if row.get("quantity"):
            total_units += int(row["quantity"])

        commission    += _d(row.get("commission"))
        fba_fees      += _d(row.get("fba_fee"))
        shipping_fees += _d(row.get("shipping_fee"))
        withheld_tax  += _d(row.get("withheld_tax"))
        other_fees    += _d(row.get("other_fees"))
        promotions    += _d(row.get("promotions"))
        net_total     += net

    net_sales = gross_sales + refunds  # refunds are already negative in settlement
    total_fees = commission + fba_fees + shipping_fees + withheld_tax + other_fees

    # amount_deposited: use meta total_amount if available, else computed net
    amount_deposited = _d(meta.get("total_amount")) or net_total
    settlement_variance = net_total - amount_deposited

    return {
        "gross_sales":                   float(gross_sales),
        "refunds":                        float(refunds),
        "promotions":                     float(promotions),
        "net_sales":                      float(net_sales),
        "commission":                     float(commission),
        "fba_fees":                       float(fba_fees),
        "shipping_fees":                  float(shipping_fees),
        "other_fees":                     float(other_fees),
        "withheld_tax":                   float(withheld_tax),
        "total_fees":                     float(total_fees),
        "net_earnings":                   float(net_total),
        "amount_deposited":               float(amount_deposited),
        "settlement_variance":            float(settlement_variance),
        "total_orders":                   total_orders,
        "total_refunded_orders":          total_refunded_orders,
        "total_units":                    total_units,
        "effective_commission_rate_pct":  _pct(abs(commission), gross_sales) if gross_sales > 0 else None,
        "return_rate_pct":                _pct(Decimal(str(total_refunded_orders)),
                                               Decimal(str(total_orders + total_refunded_orders))) if (total_orders + total_refunded_orders) > 0 else None,
        "fee_rate_pct":                   _pct(abs(total_fees), gross_sales) if gross_sales > 0 else None,
    }


def compute_amazon_order_analytics(order_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    For each order row, compute expected_net and settlement_variance.

    expected_net = gross_amount + commission + fba_fee + shipping_fee + withheld_tax + other_fees
    (all fee fields are typically negative in Amazon settlement)
    settlement_variance = net_amount - expected_net
    """
    enriched = []
    for row in order_rows:
        gross    = float(row.get("gross_amount") or 0)
        comm     = float(row.get("commission") or 0)
        fba      = float(row.get("fba_fee") or 0)
        ship     = float(row.get("shipping_fee") or 0)
        tax      = float(row.get("withheld_tax") or 0)
        other    = float(row.get("other_fees") or 0)
        promo    = float(row.get("promotions") or 0)
        net      = float(row.get("net_amount") or 0)

        expected_net = gross + comm + fba + ship + tax + other + promo
        variance = round(net - expected_net, 2)

        enriched.append({
            **row,
            "expected_net":         round(expected_net, 2),
            "settlement_variance":  variance,
        })
    return enriched
