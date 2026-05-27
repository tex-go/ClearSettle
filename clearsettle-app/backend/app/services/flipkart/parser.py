"""
Flipkart P&L Report Excel parser.

Handles multi-sheet Flipkart Seller Hub exports:
  - Overall Summary  (key-value rows → summary KPIs)
  - SKU-level P&L    (tabular → per-SKU metrics)
  - Orders P&L       (tabular → per-order metrics)
  - Report Help      (skipped)

Returns structured dicts ready to be stored in the DB.
"""
from __future__ import annotations

import io
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import pandas as pd
from pandas import DataFrame

logger = logging.getLogger(__name__)

# ── Column alias tables ───────────────────────────────────────────────────────
# Each canonical field maps to ordered list of known Flipkart column names.

SKU_COL_ALIASES: Dict[str, List[str]] = {
    "sku_code": [
        "sku", "sku id", "sku_id", "product id", "product_id", "item id",
        "listing id", "fsn", "product sku", "item sku", "seller sku",
        "seller sku id", "product code",
    ],
    "product_title": [
        "title", "product title", "product name", "product", "name",
        "item name", "item title", "description", "listing title",
    ],
    "category": [
        "category", "product category", "item category", "cat",
        "vertical", "sub category",
    ],
    "selling_price": [
        "selling price", "sp", "sale price", "sold price",
        "effective price", "unit price", "price",
    ],
    "mrp": ["mrp", "maximum retail price", "list price", "max price"],
    "total_orders": [
        "total orders", "orders", "no. of orders", "order count",
        "number of orders", "total order quantity",
    ],
    "qty_sold": [
        "qty sold", "quantity sold", "units sold", "qty",
        "total quantity sold", "sold qty", "net units",
    ],
    "gross_sales": [
        "gross sales", "gross revenue", "gross amount", "total sales",
        "total revenue", "revenue", "sales", "gross mrp sales",
    ],
    "returns_qty": [
        "return qty", "returned qty", "returns qty", "return quantity",
        "returned quantity", "return units", "units returned",
    ],
    "returns_value": [
        "return value", "returns value", "return amount", "returns amount",
        "returned value", "return total", "total returns",
        "return revenue", "returned sales",
    ],
    "cancellations_qty": [
        "cancellation qty", "cancelled qty", "cancel qty",
        "cancellation quantity", "cancelled quantity", "units cancelled",
    ],
    "cancellations_value": [
        "cancellation value", "cancelled value", "cancel value",
        "cancellations value", "cancellation amount", "cancelled sales",
    ],
    "net_sales": [
        "net sales", "net revenue", "net amount", "net",
        "effective sales", "adjusted sales", "net gmv",
    ],
    "commission": [
        "commission", "platform commission", "platform fee",
        "marketplace fee", "marketplace commission", "seller commission",
        "selling fee", "referral fee", "flipkart commission",
    ],
    "shipping_charges": [
        "shipping charges", "shipping", "shipping fee", "forward shipping",
        "logistics charges", "logistics fee", "delivery charges",
        "forward logistics", "shipping cost",
    ],
    "reverse_shipping": [
        "reverse shipping", "return shipping", "reverse logistics",
        "return freight", "reverse freight", "return logistics charges",
        "reverse shipping charges",
    ],
    "other_fees": [
        "other charges", "other fees", "other deductions",
        "miscellaneous", "misc charges", "additional charges",
        "collection fee", "fixed fee", "collection charges",
        "payment gateway fee", "tech fee", "category fee",
    ],
    "net_earnings": [
        "net earnings", "net payout", "net payment", "earnings",
        "payout", "total payout", "net profit", "net income",
        "net proceeds", "total earnings",
    ],
    "margin_pct": [
        "margin %", "profit margin %", "profit margin", "margin",
        "net margin %", "net margin", "margin percentage",
    ],
}

ORDER_COL_ALIASES: Dict[str, List[str]] = {
    "order_id": [
        "order id", "order_id", "order no", "order no.", "order number",
        "order ref", "order reference", "orderid", "sub order no",
        "sub order id",
    ],
    "order_date": [
        "order date", "order_date", "date", "placed date",
        "order placed date", "purchase date", "created date",
    ],
    "sku_code": [
        "sku", "sku id", "product id", "fsn", "listing id", "item id",
        "seller sku", "product code",
    ],
    "product_title": [
        "product title", "title", "product", "product name", "item name",
        "description",
    ],
    "category": ["category", "product category", "vertical"],
    "selling_price": [
        "selling price", "sp", "unit price", "sale price", "effective sp",
    ],
    "quantity": [
        "quantity", "qty", "units", "order qty", "order quantity",
        "quantity ordered",
    ],
    "gross_amount": [
        "gross amount", "gross revenue", "gross", "total amount",
        "order value", "order amount", "gross order value",
    ],
    "commission": [
        "commission", "platform fee", "marketplace fee", "referral fee",
        "commission amount",
    ],
    "shipping_charges": [
        "shipping charges", "shipping", "forward shipping",
        "logistics", "shipping fee", "forward shipping charges",
    ],
    "reverse_shipping": [
        "reverse shipping", "return shipping", "reverse logistics",
        "reverse shipping charges",
    ],
    "other_fees": [
        "other charges", "other fees", "collection fee", "fixed fee",
        "additional charges", "other deductions",
    ],
    "net_earnings": [
        "net earnings", "net payout", "earnings", "net",
        "net amount", "payout amount", "seller earnings",
    ],
    "status": [
        "status", "order status", "fulfilment status", "fulfillment status",
        "shipment status",
    ],
    "settlement_status": [
        "settlement status", "payment status", "settled",
        "remittance status", "payout status",
    ],
    "settlement_amount": [
        "settlement amount", "settled amount", "remittance amount",
        "remitted amount", "actual settlement", "paid amount",
        "amount settled",
    ],
    "settlement_date": [
        "settlement date", "payment date", "remittance date",
        "paid date", "transferred date", "payout date",
    ],
}

SUMMARY_ROW_ALIASES: Dict[str, List[str]] = {
    "gross_sales": [
        "gross sales", "gross revenue", "total sales", "total revenue",
        "gross mrp sales", "total gross sales", "total gmv",
    ],
    "returns": [
        "total returns", "returns", "return value", "return deduction",
        "return amount", "total return value", "returns amount",
    ],
    "cancellations": [
        "total cancellations", "cancellations", "cancellation deduction",
        "cancellation value", "cancelled amount", "cancellation amount",
    ],
    "net_sales": [
        "net sales", "net revenue", "net amount", "effective sales",
        "adjusted revenue", "total net sales", "net gmv",
    ],
    "commission": [
        "platform commission", "commission", "marketplace fee",
        "selling fee", "referral fee", "total commission",
        "flipkart commission",
    ],
    "shipping_charges": [
        "shipping charges", "shipping fee", "forward shipping charges",
        "logistics charges", "total shipping", "logistics fees",
        "forward shipping",
    ],
    "reverse_shipping": [
        "reverse shipping", "return shipping", "reverse logistics charges",
        "reverse shipping charges", "return logistics",
    ],
    "collection_fees": [
        "collection fees", "collection fee", "payment collection fee",
        "collection charges",
    ],
    "fixed_fees": [
        "fixed fees", "fixed fee", "category fee",
        "tech fee", "platform fee",
    ],
    "gst_on_fees": [
        "gst on fees", "gst on services", "gst", "service tax",
        "tax on services", "igst on fees", "gst charges",
    ],
    "tcs": ["tcs", "tax collected at source", "tcs deduction", "tcs amount"],
    "tds": ["tds", "tax deducted at source", "tds deduction", "tds amount"],
    "other_fees": [
        "other deductions", "other charges", "misc charges",
        "miscellaneous deductions", "other fees", "other adjustments",
    ],
    "net_earnings": [
        "net earnings", "net payout", "net payment",
        "total payout", "net proceeds", "total earnings", "seller earnings",
    ],
    "amount_settled": [
        "amount settled", "amount received", "settlement received",
        "total settled", "total received", "settled amount",
        "total remittance",
    ],
    "amount_pending": [
        "amount pending", "pending settlement", "unsettled amount",
        "pending payout", "outstanding amount", "total pending",
    ],
    "total_orders": [
        "total orders", "orders", "no. of orders", "total order count",
        "number of orders", "total shipped orders",
    ],
    "total_returned_orders": [
        "total returned orders", "returned orders", "return orders",
        "total returns (orders)", "returns (orders)",
    ],
    "total_cancelled_orders": [
        "total cancelled orders", "cancelled orders", "cancellation orders",
        "cancellations (orders)", "cancel orders",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_key(s: Any) -> str:
    return str(s).lower().strip().replace("\n", " ").replace("  ", " ")


def _to_decimal(val: Any) -> Optional[Decimal]:
    if val is None:
        return None
    if isinstance(val, float) and (val != val):  # NaN
        return None
    try:
        s = str(val).replace(",", "").replace("₹", "").replace("₹", "").replace(" ", "").strip()
        if s in ("", "-", "—", "N/A", "NA", "nan", "none", "null"):
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _to_int(val: Any) -> Optional[int]:
    d = _to_decimal(val)
    return int(d) if d is not None else None


def _to_date_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, float) and (val != val):
        return None
    try:
        return pd.to_datetime(val, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return None


def _map_columns(df: DataFrame, aliases: Dict[str, List[str]]) -> Dict[str, Optional[str]]:
    """Map canonical field names to actual DataFrame column names."""
    clean_cols = {_clean_key(c): c for c in df.columns}
    mapping: Dict[str, Optional[str]] = {}
    for canonical, alias_list in aliases.items():
        found = None
        for alias in alias_list:
            alias_clean = alias.lower().strip()
            for col_clean, col_real in clean_cols.items():
                if alias_clean == col_clean or alias_clean in col_clean or col_clean in alias_clean:
                    found = col_real
                    break
            if found:
                break
        mapping[canonical] = found
    return mapping


def _get(df: DataFrame, col_map: Dict[str, Optional[str]], field: str, idx: Any) -> Any:
    col = col_map.get(field)
    if not col:
        return None
    try:
        return df.at[idx, col]
    except (KeyError, TypeError):
        return None


# ── Sheet type detection ──────────────────────────────────────────────────────

def _is_summary(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ["overall summary", "p&l summary", "pl summary", "summary", "overall"])


def _is_sku(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ["sku", "product summary", "product p&l", "item-level", "listing", "product-level"])


def _is_orders(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ["order", "transaction", "order p&l", "order details", "orders p&l"])


def _is_help(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ["help", "read me", "readme", "guide", "instruction", "about"])


# ── Sheet parsers ─────────────────────────────────────────────────────────────

def _parse_summary_sheet(df: DataFrame) -> Dict[str, Any]:
    """
    Summary sheets are 2-column key-value tables.
    Robustly find metric names and values regardless of layout.
    """
    result: Dict[str, Any] = {}
    if df.shape[1] < 2:
        return result

    # Find which column has the most numeric values (value column)
    best_val_col = 1
    for c_idx in range(1, min(df.shape[1], 6)):
        numeric_count = sum(
            1 for v in df.iloc[:, c_idx]
            if _to_decimal(v) is not None
        )
        prev_count = sum(
            1 for v in df.iloc[:, best_val_col]
            if _to_decimal(v) is not None
        )
        if numeric_count > prev_count:
            best_val_col = c_idx

    # Build raw {cleaned_key: value} map
    raw: Dict[str, Any] = {}
    for _, row in df.iterrows():
        key = row.iloc[0]
        val = row.iloc[best_val_col]
        if key is None or (isinstance(key, float) and key != key):
            continue
        cleaned = _clean_key(key)
        if cleaned:
            raw[cleaned] = val

    # Map raw keys to canonical fields
    for canonical, alias_list in SUMMARY_ROW_ALIASES.items():
        for alias in alias_list:
            alias_clean = alias.lower().strip()
            for raw_key, raw_val in raw.items():
                if alias_clean == raw_key or alias_clean in raw_key or raw_key in alias_clean:
                    result[canonical] = _to_decimal(raw_val)
                    break
            if canonical in result:
                break

    return result


def _parse_sku_sheet(df: DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    df = df.dropna(how="all").reset_index(drop=True)
    col_map = _map_columns(df, SKU_COL_ALIASES)
    rows = []

    for idx in df.index:
        raw_sku = _get(df, col_map, "sku_code", idx)
        if raw_sku is None or str(raw_sku).strip().lower() in ("", "nan", "sku", "sku id", "product id"):
            continue

        gross = _to_decimal(_get(df, col_map, "gross_sales", idx))
        net   = _to_decimal(_get(df, col_map, "net_sales", idx))
        earn  = _to_decimal(_get(df, col_map, "net_earnings", idx))
        qty_s = _to_decimal(_get(df, col_map, "qty_sold", idx))
        ret_q = _to_decimal(_get(df, col_map, "returns_qty", idx))
        ret_v = _to_decimal(_get(df, col_map, "returns_value", idx))
        can_q = _to_decimal(_get(df, col_map, "cancellations_qty", idx))
        can_v = _to_decimal(_get(df, col_map, "cancellations_value", idx))
        comm  = _to_decimal(_get(df, col_map, "commission", idx))
        ship  = _to_decimal(_get(df, col_map, "shipping_charges", idx))
        rship = _to_decimal(_get(df, col_map, "reverse_shipping", idx))
        other = _to_decimal(_get(df, col_map, "other_fees", idx))

        # Derived: total fees
        fee_vals = [v for v in [comm, ship, rship, other] if v is not None]
        total_fees = sum(abs(v) for v in fee_vals) if fee_vals else None

        # Derived: margin %
        margin = _to_decimal(_get(df, col_map, "margin_pct", idx))
        if margin is None and gross and gross != 0 and earn is not None:
            margin = round((earn / gross) * Decimal("100"), 4)

        # Derived: return rate
        return_rate = None
        if qty_s and qty_s != 0 and ret_q is not None:
            return_rate = round(abs(ret_q) / qty_s * Decimal("100"), 3)
        elif gross and gross != 0 and ret_v is not None:
            return_rate = round(abs(ret_v) / gross * Decimal("100"), 3)

        # Derived: cancellation rate
        cancel_rate = None
        if qty_s and qty_s != 0 and can_q is not None:
            cancel_rate = round(abs(can_q) / qty_s * Decimal("100"), 3)
        elif gross and gross != 0 and can_v is not None:
            cancel_rate = round(abs(can_v) / gross * Decimal("100"), 3)

        rows.append({
            "sku_code":              str(raw_sku).strip(),
            "product_title":         str(_get(df, col_map, "product_title", idx) or "").strip() or None,
            "category":              str(_get(df, col_map, "category", idx) or "").strip() or None,
            "selling_price":         _to_decimal(_get(df, col_map, "selling_price", idx)),
            "mrp":                   _to_decimal(_get(df, col_map, "mrp", idx)),
            "total_orders":          _to_int(_get(df, col_map, "total_orders", idx)),
            "qty_sold":              qty_s,
            "gross_sales":           gross,
            "returns_qty":           ret_q,
            "returns_value":         ret_v,
            "cancellations_qty":     can_q,
            "cancellations_value":   can_v,
            "net_sales":             net,
            "commission":            comm,
            "shipping_charges":      ship,
            "reverse_shipping":      rship,
            "other_fees":            other,
            "total_fees":            total_fees,
            "net_earnings":          earn,
            "margin_pct":            margin,
            "return_rate_pct":       return_rate,
            "cancellation_rate_pct": cancel_rate,
            "is_loss_making":        bool(earn is not None and earn < 0),
            "high_return_rate":      bool(return_rate is not None and return_rate >= Decimal("20")),
        })

    return rows


def _parse_order_sheet(df: DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    df = df.dropna(how="all").reset_index(drop=True)
    col_map = _map_columns(df, ORDER_COL_ALIASES)
    rows = []

    for idx in df.index:
        raw_oid = _get(df, col_map, "order_id", idx)
        if raw_oid is None or str(raw_oid).strip().lower() in ("", "nan", "order id", "order_id", "orderid"):
            continue

        gross  = _to_decimal(_get(df, col_map, "gross_amount", idx))
        comm   = _to_decimal(_get(df, col_map, "commission", idx))
        ship   = _to_decimal(_get(df, col_map, "shipping_charges", idx))
        rship  = _to_decimal(_get(df, col_map, "reverse_shipping", idx))
        other  = _to_decimal(_get(df, col_map, "other_fees", idx))
        earn   = _to_decimal(_get(df, col_map, "net_earnings", idx))
        sett   = _to_decimal(_get(df, col_map, "settlement_amount", idx))

        # Expected settlement = gross - all fees
        fee_sum = sum(abs(v) for v in [comm, ship, rship, other] if v is not None)
        expected = (gross - Decimal(str(fee_sum))) if gross is not None else None
        variance = (expected - sett) if (expected is not None and sett is not None) else None

        rows.append({
            "order_id":           str(raw_oid).strip(),
            "order_date":         _to_date_str(_get(df, col_map, "order_date", idx)),
            "sku_code":           str(_get(df, col_map, "sku_code", idx) or "").strip() or None,
            "product_title":      str(_get(df, col_map, "product_title", idx) or "").strip() or None,
            "category":           str(_get(df, col_map, "category", idx) or "").strip() or None,
            "selling_price":      _to_decimal(_get(df, col_map, "selling_price", idx)),
            "quantity":           _to_decimal(_get(df, col_map, "quantity", idx)),
            "gross_amount":       gross,
            "commission":         comm,
            "shipping_charges":   ship,
            "reverse_shipping":   rship,
            "other_fees":         other,
            "net_earnings":       earn,
            "status":             str(_get(df, col_map, "status", idx) or "").strip().lower() or None,
            "settlement_status":  str(_get(df, col_map, "settlement_status", idx) or "").strip().lower() or None,
            "settlement_amount":  sett,
            "settlement_date":    _to_date_str(_get(df, col_map, "settlement_date", idx)),
            "expected_settlement": expected,
            "settlement_variance": variance,
        })

    return rows


# ── Public API ────────────────────────────────────────────────────────────────

def parse_flipkart_excel(file_bytes: bytes) -> Dict[str, Any]:
    """
    Parse a Flipkart P&L Excel report.

    Returns:
        {
          "sheets_found": [str, ...],
          "summary":      {field: Decimal|int|None, ...},
          "sku_rows":     [{...}, ...],
          "order_rows":   [{...}, ...],
          "errors":       [str, ...],
        }
    """
    out: Dict[str, Any] = {
        "sheets_found": [],
        "summary": {},
        "sku_rows": [],
        "order_rows": [],
        "errors": [],
    }

    try:
        xf = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as exc:
        out["errors"].append(f"Cannot open Excel file: {exc}")
        return out

    out["sheets_found"] = list(xf.sheet_names)

    for sheet_name in xf.sheet_names:
        if _is_help(sheet_name):
            logger.debug("Skipping help sheet: %s", sheet_name)
            continue

        try:
            df = pd.read_excel(xf, sheet_name=sheet_name, header=0, dtype=str)
            df = df.where(pd.notna(df), None)
        except Exception as exc:
            out["errors"].append(f"Failed to read sheet '{sheet_name}': {exc}")
            continue

        if _is_summary(sheet_name):
            out["summary"] = _parse_summary_sheet(df)
            logger.info("Summary sheet '%s': %d fields parsed", sheet_name, len(out["summary"]))

        elif _is_sku(sheet_name):
            rows = _parse_sku_sheet(df)
            out["sku_rows"].extend(rows)
            logger.info("SKU sheet '%s': %d rows parsed", sheet_name, len(rows))

        elif _is_orders(sheet_name):
            rows = _parse_order_sheet(df)
            out["order_rows"].extend(rows)
            logger.info("Orders sheet '%s': %d rows parsed", sheet_name, len(rows))

        else:
            # Auto-detect: check column names
            col_lower = [str(c).lower() for c in df.columns]
            has_order_id = any("order id" in c or c in ("orderid", "order_id") for c in col_lower)
            has_sku = any(c in ("sku", "sku id", "product id", "fsn") for c in col_lower)

            if has_order_id:
                rows = _parse_order_sheet(df)
                out["order_rows"].extend(rows)
                logger.info("Auto-detected orders in '%s': %d rows", sheet_name, len(rows))
            elif has_sku:
                rows = _parse_sku_sheet(df)
                out["sku_rows"].extend(rows)
                logger.info("Auto-detected SKUs in '%s': %d rows", sheet_name, len(rows))
            else:
                # Could be summary-style
                parsed = _parse_summary_sheet(df)
                if parsed and not out["summary"]:
                    out["summary"] = parsed
                    logger.info("Auto-detected summary in '%s': %d fields", sheet_name, len(parsed))

    return out
