"""
Amazon Settlement Report parser.

Handles Amazon Seller Central Settlement Reports:
  - Flat File V2 (.txt, tab-separated) — standard format
  - Excel (.xlsx/.xls) — alternate download format

The settlement flat file contains one row per transaction line item.
Key column groups:
  settlement-id, settlement-start-date, settlement-end-date, deposit-date,
  total-amount, currency, transaction-type (Order/Refund/Transfer/Adjustment),
  order-id, merchant-order-id, shipment-id, marketplace-name,
  amount-type (ItemPrice/ItemFees/ItemWithheldTax/Promotion),
  amount-description (Principal/Commission/FBAPerUnitFulfillmentFee/
                      ShippingHB/Tax/MarketplaceFacilitatorTax-Principal/etc.),
  amount, sku, quantity-purchased, posted-date-time

Returns structured dicts: meta, order_rows, errors.
"""
from __future__ import annotations

import io
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ── Column alias tables ────────────────────────────────────────────────────────
# Maps canonical field name → list of known column header variants (lowercased)

_META_ALIASES: Dict[str, List[str]] = {
    "settlement_id":         ["settlement-id", "settlement id", "settlementid"],
    "settlement_start_date": ["settlement-start-date", "settlement start date", "start date"],
    "settlement_end_date":   ["settlement-end-date", "settlement end date", "end date"],
    "deposit_date":          ["deposit-date", "deposit date", "depositdate"],
    "total_amount":          ["total-amount", "total amount", "totalamount"],
    "currency":              ["currency", "currency code"],
}

_ROW_ALIASES: Dict[str, List[str]] = {
    "transaction_type":      ["transaction-type", "transaction type", "type"],
    "order_id":              ["order-id", "order id", "orderid", "amazon-order-id", "amazon order id"],
    "merchant_order_id":     ["merchant-order-id", "merchant order id", "seller order id"],
    "shipment_id":           ["shipment-id", "shipment id"],
    "posted_date":           ["posted-date-time", "posted date time", "posted-date", "posted date", "transaction date"],
    "sku":                   ["sku", "seller-sku", "seller sku", "msku", "merchant sku"],
    "product_name":          ["product name", "item name", "description", "product-name"],
    "quantity":              ["quantity-purchased", "quantity purchased", "quantity", "qty"],
    "amount_type":           ["amount-type", "amount type"],
    "amount_description":    ["amount-description", "amount description"],
    "amount":                ["amount", "transaction amount"],
    "shipment_date":         ["shipment-date", "shipment date", "ship date"],
    "order_date":            ["order date", "order-date", "purchase date"],
    "fulfillment_id":        ["fulfillment-id", "fulfillment id", "fulfillment channel", "fulfillment-channel"],
    "marketplace":           ["marketplace-name", "marketplace name", "marketplace"],
    "promotion_id":          ["promotion-id", "promotion id"],
}

# Amazon amount-description values that map to specific fee fields
_AMT_DESC_COMMISSION     = {"commission", "referral fee", "referralfee", "variable closing fee", "seller fee"}
_AMT_DESC_FBA            = {"fbaperunitfulfillmentfee", "fba per unit fulfillment fee", "fulfillment fee",
                            "weight handling", "pick pack fee", "fba fulfillment fee"}
_AMT_DESC_SHIPPING       = {"shippinghb", "shipping", "shipping fee", "shipping charge", "standard shipping"}
_AMT_DESC_WITHHELD_TAX   = {"marketplacefacilitator", "tcs", "tax collected at source",
                             "marketplacefacilitatortax-principal",
                             "marketplacefacilitatorvar-principal", "withheld tax"}
_AMT_DESC_PROMOTIONS     = {"promotion", "promo", "discount", "lightning deal fee"}
_AMT_DESC_PRINCIPAL      = {"principal", "itempriceadjustment", "item price"}


def _col(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    """Return first column name that matches any alias (case-insensitive)."""
    norm = {c.lower().strip(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in norm:
            return norm[alias.lower()]
    return None


def _d(v: Any) -> Decimal:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return Decimal("0")
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _parse_date_val(v: Any) -> Optional[date]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (date, datetime)):
        return v.date() if isinstance(v, datetime) else v
    s = str(v).strip()[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:len(fmt)], fmt).date()
        except ValueError:
            continue
    return None


def _str(v: Any) -> Optional[str]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s else None


def _extract_meta(df: pd.DataFrame) -> Dict[str, Any]:
    """Extract settlement-level metadata from the first data rows."""
    meta: Dict[str, Any] = {}
    for field, aliases in _META_ALIASES.items():
        col = _col(df, aliases)
        if col and len(df) > 0:
            val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if field in ("settlement_id",):
                meta[field] = _str(val)
            elif field in ("settlement_start_date", "settlement_end_date", "deposit_date"):
                meta[field] = _parse_date_val(val)
            elif field == "total_amount":
                meta[field] = _d(val)
            else:
                meta[field] = _str(val)
    return meta


def _pivot_to_order_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Pivot the transaction-level flat file into per-order summary rows.

    Each order-id gets one aggregated row with:
      gross_amount      = sum of Principal amounts for Order transactions
      commission        = sum of Commission amounts
      fba_fee           = sum of FBA fee amounts
      shipping_fee      = sum of Shipping amounts
      withheld_tax      = sum of WithheldTax/TCS amounts
      promotions        = sum of Promotion amounts
      net_amount        = total of all amounts for that order
    """
    t_col    = _col(df, _ROW_ALIASES["transaction_type"])
    o_col    = _col(df, _ROW_ALIASES["order_id"])
    mo_col   = _col(df, _ROW_ALIASES["merchant_order_id"])
    at_col   = _col(df, _ROW_ALIASES["amount_type"])
    ad_col   = _col(df, _ROW_ALIASES["amount_description"])
    amt_col  = _col(df, _ROW_ALIASES["amount"])
    sku_col  = _col(df, _ROW_ALIASES["sku"])
    pn_col   = _col(df, _ROW_ALIASES["product_name"])
    qty_col  = _col(df, _ROW_ALIASES["quantity"])
    pd_col   = _col(df, _ROW_ALIASES["posted_date"])
    sd_col   = _col(df, _ROW_ALIASES["shipment_date"])
    od_col   = _col(df, _ROW_ALIASES["order_date"])

    if amt_col is None:
        return []

    order_buckets: Dict[str, Dict[str, Any]] = {}

    for _, row in df.iterrows():
        order_id = _str(row[o_col]) if o_col else None
        if not order_id:
            continue

        txn_type = (_str(row[t_col]) or "").lower() if t_col else ""
        amt_desc = (_str(row[ad_col]) or "").lower() if ad_col else ""
        amt_type = (_str(row[at_col]) or "").lower() if at_col else ""
        amount   = _d(row[amt_col])

        if order_id not in order_buckets:
            sku  = _str(row[sku_col])  if sku_col  else None
            name = _str(row[pn_col])   if pn_col   else None
            qty  = row[qty_col]        if qty_col  else None
            posted = _parse_date_val(row[pd_col]) if pd_col else None
            ship   = _parse_date_val(row[sd_col]) if sd_col else None
            odate  = _parse_date_val(row[od_col]) if od_col else None
            merchant_oid = _str(row[mo_col]) if mo_col else None

            order_buckets[order_id] = {
                "order_id":          order_id,
                "merchant_order_id": merchant_oid,
                "sku":               sku,
                "product_name":      name,
                "quantity":          int(qty) if qty and not (isinstance(qty, float) and pd.isna(qty)) else None,
                "posted_date":       posted,
                "shipment_date":     ship,
                "order_date":        odate,
                "transaction_type":  txn_type.title() if txn_type else "Order",
                "gross_amount":      Decimal("0"),
                "commission":        Decimal("0"),
                "fba_fee":           Decimal("0"),
                "shipping_fee":      Decimal("0"),
                "withheld_tax":      Decimal("0"),
                "promotions":        Decimal("0"),
                "other_fees":        Decimal("0"),
                "net_amount":        Decimal("0"),
            }
        else:
            # Prefer first non-null values
            if not order_buckets[order_id]["sku"] and sku_col:
                order_buckets[order_id]["sku"] = _str(row[sku_col])
            if not order_buckets[order_id]["product_name"] and pn_col:
                order_buckets[order_id]["product_name"] = _str(row[pn_col])

        b = order_buckets[order_id]

        # Accumulate into the right bucket based on amount_description
        if amt_desc in _AMT_DESC_PRINCIPAL or amt_type == "itemprice":
            b["gross_amount"] += amount
        elif amt_desc in _AMT_DESC_COMMISSION or "commission" in amt_desc or "referral" in amt_desc:
            b["commission"] += amount
        elif amt_desc in _AMT_DESC_FBA or "fba" in amt_desc or "fulfillment" in amt_desc:
            b["fba_fee"] += amount
        elif amt_desc in _AMT_DESC_SHIPPING or "shipping" in amt_desc:
            b["shipping_fee"] += amount
        elif amt_desc in _AMT_DESC_WITHHELD_TAX or "withheld" in amt_desc or "tcs" in amt_desc or "facilitator" in amt_desc:
            b["withheld_tax"] += amount
        elif amt_desc in _AMT_DESC_PROMOTIONS or "promo" in amt_desc:
            b["promotions"] += amount
        else:
            b["other_fees"] += amount

        b["net_amount"] += amount

    rows = list(order_buckets.values())
    for r in rows:
        r["gross_amount"] = float(r["gross_amount"])
        r["commission"]   = float(r["commission"])
        r["fba_fee"]      = float(r["fba_fee"])
        r["shipping_fee"] = float(r["shipping_fee"])
        r["withheld_tax"] = float(r["withheld_tax"])
        r["promotions"]   = float(r["promotions"])
        r["other_fees"]   = float(r["other_fees"])
        r["net_amount"]   = float(r["net_amount"])
    return rows


def parse_amazon_settlement(file_bytes: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Parse an Amazon Settlement Report file.

    Returns:
      {
        "meta":       { settlement_id, settlement_start_date, ... },
        "order_rows": [ { order_id, sku, gross_amount, commission, ... }, ... ],
        "errors":     [ str, ... ],
        "row_count":  int,
      }
    """
    errors: List[str] = []
    fname_lower = filename.lower()

    df: Optional[pd.DataFrame] = None

    # ── Try reading the file ───────────────────────────────────────────────────
    if fname_lower.endswith((".xlsx", ".xls")):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str, keep_default_na=False)
        except Exception as exc:
            errors.append(f"Excel read error: {exc}")
    else:
        # Tab-separated flat file (.txt or unknown extension)
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    sep="\t",
                    encoding=enc,
                    dtype=str,
                    keep_default_na=False,
                    on_bad_lines="skip",
                )
                break
            except Exception as exc:
                errors.append(f"TSV parse error ({enc}): {exc}")

    if df is None or df.empty:
        errors.append("File appears empty or could not be parsed.")
        return {"meta": {}, "order_rows": [], "errors": errors, "row_count": 0}

    # Normalise column names (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]

    # Replace blank strings with None for numerics
    df = df.replace("", None)

    meta = _extract_meta(df)
    order_rows = _pivot_to_order_rows(df)
    raw_count = len(df)

    if not order_rows:
        errors.append("Could not extract any order rows. Check that this is an Amazon Settlement Report.")

    logger.info(
        "Amazon parser: %d raw rows → %d order rows; settlement_id=%s",
        raw_count, len(order_rows), meta.get("settlement_id"),
    )

    return {
        "meta":       meta,
        "order_rows": order_rows,
        "errors":     errors,
        "row_count":  raw_count,
    }
