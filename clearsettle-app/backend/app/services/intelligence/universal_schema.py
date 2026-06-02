"""
Universal Field Mapping.

Maps platform-specific column names to canonical ClearSettle field names.

Key: normalized column name (lowercase, stripped)
Value: (universal_field, transform)

Transforms:
  None       — use value as-is
  "abs"      — take absolute value (some platforms report fees as negative)
  "negate"   — negate the value
  "date_parse" — parse as date string
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

# (universal_field, transform)
_FieldSpec = Tuple[str, Optional[str]]

UNIVERSAL_FIELD_MAP: Dict[str, Dict[str, _FieldSpec]] = {
    "flipkart": {
        "order id": ("order_id", None),
        "order item id": ("order_item_id", None),
        "order item no": ("order_item_id", None),
        "sub order no": ("order_item_id", None),
        "settlement id": ("settlement_id", None),
        "neft id": ("settlement_id", None),
        "order date": ("order_date", "date_parse"),
        "payment date": ("settlement_date", "date_parse"),
        "sale amount (rs.)": ("gross_amount", None),
        "my share (rs.)": ("gross_amount", None),
        "bank settlement value (rs.) = sum(j:r)": ("net_settlement", None),
        "bank settlement value": ("net_settlement", None),
        "commission (rs.)": ("commission", "abs"),
        "marketplace fee (rs.)": ("commission", "abs"),
        "shipping fee (rs.)": ("shipping_fee", "abs"),
        "reverse shipping fee (rs.)": ("return_shipping", "abs"),
        "tcs (rs.)": ("tcs", "abs"),
        "tds (rs.)": ("tds", "abs"),
        "gst on mp fees (rs.)": ("gst_on_fees", "abs"),
        "seller sku": ("sku", None),
        "seller sku id": ("sku", None),
        "fsn": ("platform_product_id", None),
        "product title": ("product_name", None),
        "category": ("category", None),
        "quantity": ("quantity", None),
        "return type": ("return_type", None),
        "gross sales": ("gross_amount", None),
        "net earnings": ("net_settlement", None),
        "commission": ("commission", "abs"),
        "shipping charges": ("shipping_fee", "abs"),
        "reverse shipping": ("return_shipping", "abs"),
        "total orders": ("total_orders", None),
        "qty sold": ("quantity", None),
        "returns qty": ("return_quantity", None),
        "returns value": ("return_value", "abs"),
        "cancellations qty": ("cancel_quantity", None),
        "cancellations value": ("cancel_value", "abs"),
        "net sales": ("net_sales", None),
        "other fees": ("other_fees", "abs"),
        "fixed fee": ("fixed_fee", "abs"),
        "collection fee": ("collection_fee", "abs"),
        "pick and pack fee": ("pick_pack_fee", "abs"),
        "closing fee": ("closing_fee", "abs"),
        "super coin cashback": ("super_coin", None),
        "wallet redeem": ("wallet_redeem", None),
        "settlement amount": ("net_settlement", None),
        "estimated net sales": ("estimated_net_sales", None),
        "bank settlement (projected)": ("projected_settlement", None),
    },
    "amazon": {
        "settlement-id": ("settlement_id", None),
        "amazon-order-id": ("order_id", None),
        "shipment-id": ("shipment_id", None),
        "transaction-type": ("transaction_type", None),
        "order-id": ("order_id", None),
        "sku": ("sku", None),
        "quantity": ("quantity", None),
        "marketplace-name": ("marketplace", None),
        "amount-type": ("fee_type", None),
        "amount-description": ("fee_description", None),
        "amount": ("amount", None),
        "fulfillment-id": ("fulfillment_id", None),
        "posted-date": ("transaction_date", "date_parse"),
        "price-type": ("price_type", None),
        "price-amount": ("gross_amount", None),
        "principal": ("gross_amount", None),
        "commission": ("commission", "negate"),
        "fba-per-unit-fulfillment-fee": ("fulfillment_fee", "negate"),
        "shipping": ("shipping_fee", None),
        "total-amount": ("net_settlement", None),
        "settlement-start-date": ("period_start", "date_parse"),
        "settlement-end-date": ("period_end", "date_parse"),
        "deposit-date": ("settlement_date", "date_parse"),
        "currency": ("currency", None),
        "fulfillment-channel": ("fulfillment_channel", None),
        "referral-fee": ("commission", "negate"),
        "asin": ("platform_product_id", None),
        "fnsku": ("platform_product_id", None),
        "safe-t-reimbursement": ("reimbursement", None),
        "quantity-purchased": ("quantity", None),
        "promotion-id": ("promotion_id", None),
    },
    "meesho": {
        "sub order number": ("order_item_id", None),
        "supplier order id": ("order_id", None),
        "order date": ("order_date", "date_parse"),
        "product name": ("product_name", None),
        "sku": ("sku", None),
        "quantity": ("quantity", None),
        "selling price": ("gross_amount", None),
        "supply price": ("cost_price", None),
        "customer price": ("gross_amount", None),
        "commission": ("commission", "abs"),
        "shipping charges": ("shipping_fee", "abs"),
        "forward shipping charge": ("shipping_fee", "abs"),
        "reverse shipping charge": ("return_shipping", "abs"),
        "settlement amount": ("net_settlement", None),
        "payment date": ("settlement_date", "date_parse"),
        "return type": ("return_type", None),
        "meesho share": ("commission", "abs"),
        "tds on commission": ("tds", "abs"),
        "penalty amount": ("penalty", "abs"),
        "meesho wallet": ("wallet_credit", None),
        "payment cycle": ("settlement_id", None),
        "product category": ("category", None),
        "delivery status": ("delivery_status", None),
        "customer city": ("customer_city", None),
    },
    "myntra": {
        "myntra order id": ("order_id", None),
        "style id": ("platform_product_id", None),
        "vendor id": ("seller_id", None),
        "order date": ("order_date", "date_parse"),
        "payment date": ("settlement_date", "date_parse"),
        "amount": ("gross_amount", None),
        "commission": ("commission", "abs"),
        "shipping fee": ("shipping_fee", "abs"),
        "net settlement": ("net_settlement", None),
        "return reason": ("return_type", None),
    },
    "ajio": {
        "ajio order id": ("order_id", None),
        "site order id": ("order_id", None),
        "courier partner": ("courier", None),
        "order date": ("order_date", "date_parse"),
        "amount": ("gross_amount", None),
        "commission": ("commission", "abs"),
        "logistics fee": ("shipping_fee", "abs"),
        "settlement amount": ("net_settlement", None),
    },
    "shopify": {
        "shopify order": ("order_id", None),
        "variant sku": ("sku", None),
        "payment gateway": ("payment_method", None),
        "gross sales": ("gross_amount", None),
        "discounts": ("discount", "abs"),
        "returns": ("return_value", "abs"),
        "net sales": ("net_sales", None),
        "taxes": ("gst", None),
        "total sales": ("gross_amount", None),
        "payout date": ("settlement_date", "date_parse"),
    },
    "generic": {
        "order_id": ("order_id", None),
        "order id": ("order_id", None),
        "amount": ("amount", None),
        "gross_amount": ("gross_amount", None),
        "net_amount": ("net_settlement", None),
        "fee": ("commission", "abs"),
        "date": ("order_date", "date_parse"),
        "sku": ("sku", None),
        "product": ("product_name", None),
        "quantity": ("quantity", None),
        "settlement": ("net_settlement", None),
        "shipping": ("shipping_fee", "abs"),
        "tax": ("gst", "abs"),
        "return": ("return_type", None),
    },
}


def get_field_map(platform: str) -> Dict[str, _FieldSpec]:
    """Return the field map for a platform, falling back to generic."""
    return UNIVERSAL_FIELD_MAP.get(platform.lower(), UNIVERSAL_FIELD_MAP["generic"])


def map_column(platform: str, column_name: str) -> Optional[_FieldSpec]:
    """
    Map a single platform-specific column name to its universal field spec.
    Returns None if no mapping found.
    """
    field_map = get_field_map(platform)
    normalized = " ".join(column_name.lower().strip().split())
    # Exact match first
    if normalized in field_map:
        return field_map[normalized]
    # Substring match as fallback
    for key, spec in field_map.items():
        if key in normalized or normalized in key:
            return spec
    return None
