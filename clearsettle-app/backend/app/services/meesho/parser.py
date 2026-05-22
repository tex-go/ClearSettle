"""
Meesho Payment Report parser.

Handles Meesho Supplier Panel Payment Report downloads:
  - Excel (.xlsx/.xls) — primary format from Meesho Supplier Panel
  - CSV fallback

Key columns in Meesho Payment Report:
  Order ID, Sub Order ID, Order Date, Order Completion Date / Payment Date,
  Customer Paid Amount, Commission Rate (%), Commission,
  Shipping Charges, Reverse Shipping Charges, GST on Commission, TCS,
  Net Payment to Supplier, Payment Status, Order Status,
  Product Name, SKU, Category, Quantity, MRP

Returns structured dicts ready for DB insertion.
"""
from __future__ import annotations

import io
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Column alias tables ────────────────────────────────────────────────────────

_COL_ALIASES: Dict[str, List[str]] = {
    "order_id": [
        "order id", "order_id", "orderid", "order no", "order number",
        "meesho order id", "meesho_order_id",
    ],
    "sub_order_id": [
        "sub order id", "sub_order_id", "suborderid", "sub-order id",
        "meesho sub order id", "sub order number",
    ],
    "order_date": [
        "order date", "order_date", "order placed date", "date of order",
        "created date", "order creation date",
    ],
    "payment_date": [
        "payment date", "payment_date", "order completion date",
        "settlement date", "payout date", "credited date",
    ],
    "product_name": [
        "product name", "product_name", "item name", "item description",
        "product title", "product description", "name",
    ],
    "sku": [
        "sku", "sku id", "sku_id", "product sku", "seller sku",
        "meesho sku", "item sku", "variant id",
    ],
    "category": [
        "category", "product category", "item category", "sub category",
        "subcategory", "cat",
    ],
    "quantity": [
        "quantity", "qty", "units", "order quantity", "item quantity",
        "no of items", "number of items",
    ],
    "mrp": [
        "mrp", "maximum retail price", "list price", "max retail price",
        "market price",
    ],
    "customer_paid": [
        "customer paid amount", "customer_paid_amount", "customer paid",
        "amount paid by customer", "selling price", "sale price",
        "total customer paid", "customer amount",
    ],
    "commission_rate": [
        "commission rate", "commission_rate", "commission rate %",
        "commission %", "commission percentage", "rate %",
    ],
    "commission": [
        "commission", "commission amount", "platform commission",
        "meesho commission", "commission (rs)", "commission charged",
        "marketplace commission",
    ],
    "shipping_charges": [
        "shipping charges", "shipping_charges", "forward shipping",
        "logistics charges", "delivery charges", "shipping fee",
        "forward logistics", "shipping amount",
    ],
    "reverse_shipping": [
        "reverse shipping charges", "reverse_shipping", "return shipping",
        "reverse logistics", "return logistics charges",
        "reverse shipping fee", "rto charges",
    ],
    "gst_on_commission": [
        "gst on commission", "gst_on_commission", "gst on platform fee",
        "tax on commission", "gst on fees", "igst on commission",
        "cgst + sgst on commission",
    ],
    "tcs": [
        "tcs", "tax collected at source", "tcs amount", "tcs deducted",
        "tcs on sales", "tax at source",
    ],
    "net_payment": [
        "net payment to supplier", "net_payment", "net payment",
        "amount to be paid", "total payment to seller",
        "net amount payable", "net settlement amount",
        "settlement amount", "net payout",
    ],
    "order_status": [
        "order status", "order_status", "status", "shipment status",
        "delivery status",
    ],
    "payment_status": [
        "payment status", "payment_status", "payout status",
        "settlement status", "payment flag",
    ],
}


def _col(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    norm = {c.lower().strip(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in norm:
            return norm[alias.lower()]
    return None


def _d(v: Any) -> Optional[float]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    if not s or s == "-":
        return None
    try:
        return float(Decimal(s).quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        return None


def _parse_date_val(v: Any) -> Optional[date]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (date, datetime)):
        return v.date() if isinstance(v, datetime) else v
    s = str(v).strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s[:10], fmt[:len(s[:10])]).date()
        except ValueError:
            continue
    return None


def _str(v: Any) -> Optional[str]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s else None


def parse_meesho_report(file_bytes: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Parse a Meesho Payment Report file.

    Returns:
      {
        "order_rows": [ { order_id, sub_order_id, customer_paid, commission, ... }, ... ],
        "errors":     [ str, ... ],
        "row_count":  int,
        "report_period": str | None,
      }
    """
    errors: List[str] = []
    fname_lower = filename.lower()

    df: Optional[pd.DataFrame] = None

    if fname_lower.endswith(".csv"):
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=enc,
                    dtype=str,
                    keep_default_na=False,
                    on_bad_lines="skip",
                )
                break
            except Exception as exc:
                errors.append(f"CSV parse error ({enc}): {exc}")
    else:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str, keep_default_na=False)
        except Exception as exc:
            # Try all sheets
            try:
                xl = pd.ExcelFile(io.BytesIO(file_bytes))
                for sheet in xl.sheet_names:
                    try:
                        candidate = xl.parse(sheet, dtype=str, keep_default_na=False)
                        if len(candidate.columns) >= 5:
                            df = candidate
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            if df is None:
                errors.append(f"Excel read error: {exc}")

    if df is None or df.empty:
        errors.append("File appears empty or could not be parsed.")
        return {"order_rows": [], "errors": errors, "row_count": 0, "report_period": None}

    df.columns = [str(c).strip() for c in df.columns]
    df = df.replace("", None)

    # Map columns
    get = lambda key: _col(df, _COL_ALIASES[key])
    c = {key: get(key) for key in _COL_ALIASES}

    if c["order_id"] is None:
        errors.append("Could not find Order ID column. Ensure this is a Meesho Payment Report.")
        return {"order_rows": [], "errors": errors, "row_count": len(df), "report_period": None}

    order_rows: List[Dict[str, Any]] = []
    dates_seen: List[date] = []

    for _, row in df.iterrows():
        oid = _str(row[c["order_id"]]) if c["order_id"] else None
        if not oid:
            continue

        odate = _parse_date_val(row[c["order_date"]]) if c["order_date"] else None
        pdate = _parse_date_val(row[c["payment_date"]]) if c["payment_date"] else None
        if odate:
            dates_seen.append(odate)

        order_rows.append({
            "order_id":        oid,
            "sub_order_id":    _str(row[c["sub_order_id"]]) if c["sub_order_id"] else None,
            "order_date":      odate,
            "payment_date":    pdate,
            "product_name":    _str(row[c["product_name"]]) if c["product_name"] else None,
            "sku":             _str(row[c["sku"]]) if c["sku"] else None,
            "category":        _str(row[c["category"]]) if c["category"] else None,
            "quantity":        int(float(row[c["quantity"]])) if c["quantity"] and row[c["quantity"]] not in (None, "") else None,
            "mrp":             _d(row[c["mrp"]]) if c["mrp"] else None,
            "customer_paid":   _d(row[c["customer_paid"]]) if c["customer_paid"] else None,
            "commission_rate": _d(row[c["commission_rate"]]) if c["commission_rate"] else None,
            "commission":      _d(row[c["commission"]]) if c["commission"] else None,
            "shipping_charges": _d(row[c["shipping_charges"]]) if c["shipping_charges"] else None,
            "reverse_shipping": _d(row[c["reverse_shipping"]]) if c["reverse_shipping"] else None,
            "gst_on_commission": _d(row[c["gst_on_commission"]]) if c["gst_on_commission"] else None,
            "tcs":             _d(row[c["tcs"]]) if c["tcs"] else None,
            "net_payment":     _d(row[c["net_payment"]]) if c["net_payment"] else None,
            "order_status":    _str(row[c["order_status"]]) if c["order_status"] else None,
            "payment_status":  _str(row[c["payment_status"]]) if c["payment_status"] else None,
        })

    # Derive report period string
    report_period: Optional[str] = None
    if dates_seen:
        min_d, max_d = min(dates_seen), max(dates_seen)
        if min_d == max_d:
            report_period = min_d.strftime("%b %Y")
        else:
            report_period = f"{min_d.strftime('%d %b')} – {max_d.strftime('%d %b %Y')}"

    logger.info(
        "Meesho parser: %d raw rows → %d order rows; period=%s",
        len(df), len(order_rows), report_period,
    )

    return {
        "order_rows":    order_rows,
        "errors":        errors,
        "row_count":     len(df),
        "report_period": report_period,
    }
