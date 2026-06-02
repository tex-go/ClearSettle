"""
Column Name Normalizer.

Maps the many spellings/formats of the same logical field
across Flipkart, Amazon, and Meesho reports to a canonical snake_case name.

Examples:
  "Order ID" → "order_id"
  "amazon-order-id" → "order_id"
  "Sub Order Number" → "order_id"
  "Forward Shipping Charge" → "shipping_fee"
  "FBA Per Unit Fulfillment Fee" → "fulfillment_fee"
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

# ── Canonical name → list of known aliases (all lowercased, stripped) ─────────

_ALIASES: Dict[str, List[str]] = {
    # ── Order identifiers ─────────────────────────────────────────────────────
    "order_id": [
        "order id", "order-id", "amazon-order-id", "merchant-order-id",
        "sub order number", "supplier order id", "order no", "order number",
        "flipkart order id",
    ],
    "order_item_id": [
        "order item id", "order item", "suborder id", "item id",
        "item order id", "line item id",
    ],
    "shipment_id": [
        "shipment id", "shipment-id", "tracking id", "awb number",
        "courier tracking id", "dispatch id",
    ],
    "settlement_id": [
        "settlement id", "settlement-id", "payment id", "neft ref",
        "bank reference", "utr number",
    ],
    "invoice_id": [
        "invoice id", "invoice number", "invoice no", "bill number",
    ],

    # ── Product identifiers ───────────────────────────────────────────────────
    "sku": [
        "sku", "sku id", "seller sku", "seller sku id", "product id",
        "product code", "item sku", "listing id", "fsn", "fnsku", "asin",
        "supplier sku",
    ],
    "product_title": [
        "product title", "title", "product name", "item name", "name",
        "description", "listing title", "asin-title",
    ],
    "category": [
        "category", "product category", "item category", "vertical",
        "sub category", "browse node",
    ],

    # ── Amounts ───────────────────────────────────────────────────────────────
    "gross_amount": [
        "gross amount", "gross sales", "sale amount", "selling price",
        "customer price", "order amount", "total order value",
        "principal charges", "gross revenue", "total-amount",
    ],
    "net_amount": [
        "net amount", "net earnings", "net sales", "net payment",
        "total payment", "net settlement", "bank amount",
    ],
    "settlement_amount": [
        "settlement amount", "total settlement", "paid amount",
        "deposit-date amount", "remitted amount",
    ],
    "commission": [
        "commission", "platform commission", "referral-fee",
        "commission amount", "platform fee",
    ],
    "shipping_fee": [
        "shipping fee", "shipping charge", "shipping charges",
        "forward shipping charge", "forward shipping fee",
        "fulfillment-channel shipping",
    ],
    "reverse_shipping_fee": [
        "reverse shipping fee", "reverse shipping charge",
        "return shipping fee", "return shipping charge",
        "reverse logistics charge",
    ],
    "fixed_fee": [
        "fixed fee", "closing fee", "pick and pack fee",
        "fulfillment fee", "fba-per-unit-fulfillment-fee",
        "tech fee", "platform fixed fee",
    ],
    "collection_fee": [
        "collection fee", "payment gateway fee", "cod fee",
        "payment collection fee",
    ],
    "tcs": [
        "tcs", "tcs igst", "tcs cgst", "tcs sgst",
        "tax collected at source",
    ],
    "tds": [
        "tds", "tds on commission", "tax deducted at source",
        "tds deducted",
    ],
    "gst": [
        "gst", "gst amount", "igst", "cgst", "sgst",
        "gst on fees", "tax amount",
    ],
    "other_fees": [
        "other fees", "other deductions", "miscellaneous fees",
        "other charges", "adjustments",
    ],

    # ── Dates ─────────────────────────────────────────────────────────────────
    "order_date": [
        "order date", "order-date", "purchase date", "order placed date",
        "created at", "order created date",
    ],
    "settlement_date": [
        "settlement date", "payment date", "deposit-date", "paid on",
        "transfer date", "neft date",
    ],
    "dispatch_date": [
        "dispatch date", "shipped date", "shipment date",
        "fulfillment date",
    ],
    "return_date": [
        "return date", "return created at", "return-date",
        "returned on",
    ],

    # ── Status fields ─────────────────────────────────────────────────────────
    "order_status": [
        "status", "order status", "delivery status", "fulfillment status",
        "shipment status",
    ],
    "settlement_status": [
        "settlement status", "payout status", "payment status",
        "bank transfer status",
    ],
    "return_status": [
        "return status", "return reason", "return type",
        "refund status", "return-reason",
    ],

    # ── Quantity ──────────────────────────────────────────────────────────────
    "quantity": [
        "quantity", "qty", "qty sold", "units sold", "quantity sold",
        "quantity-purchased", "order quantity",
    ],
}

# Build reverse lookup: alias → canonical_name
_REVERSE: Dict[str, str] = {}
for canonical, aliases in _ALIASES.items():
    for alias in aliases:
        _REVERSE[alias.lower().strip()] = canonical
    _REVERSE[canonical] = canonical  # self-map


def normalize_column_name(raw: str) -> str:
    """
    Convert any raw column name to its canonical snake_case form.

    Falls back to a slugified version of the raw name if no alias found.
    """
    cleaned = _clean(raw)
    if cleaned in _REVERSE:
        return _REVERSE[cleaned]
    # Try partial match
    for alias, canonical in _REVERSE.items():
        if alias in cleaned or cleaned in alias:
            return canonical
    return _slugify(raw)


def resolve_column(
    row: dict,
    canonical: str,
    *,
    fallback: str | None = None,
) -> Optional[str]:
    """
    Retrieve the value from a row dict by trying the canonical name
    and all its known aliases.

    Returns the first non-None, non-empty string value found.
    """
    aliases_to_try = [canonical] + _ALIASES.get(canonical, [])
    for alias in aliases_to_try:
        # Try exact key
        for key in row:
            if _clean(key) == alias.lower().strip():
                val = row[key]
                if val is not None and str(val).strip():
                    return str(val).strip()
    return fallback


def _clean(col: str) -> str:
    return re.sub(r"[\s\-_]+", " ", col.lower()).strip()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower())
    return slug.strip("_") or "col"
