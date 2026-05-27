"""
File ingestion layer — parse uploaded CSV/XLSX/TXT files into staging tables.

Each file type has a column mapping spec that normalises whatever the user
uploaded into the canonical staging schema. Users can override the mapping via
column_map_json on the ReconFile record.
"""
from __future__ import annotations

import io
import json
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

# ── canonical column aliases ──────────────────────────────────────────────────
# Maps canonical field name → list of common source column names (case-insensitive).
# First match wins.

SETTLEMENT_ALIASES: dict[str, list[str]] = {
    "settlement_id":    ["settlement_id", "settlement id", "settlementid"],
    "transaction_date": ["transaction_date", "date", "settlement_date", "payment_date"],
    "reference_number": ["reference_number", "ref", "reference", "order_id", "order id"],
    "invoice_number":   ["invoice_number", "invoice_no", "invoice", "invoice#"],
    "po_number":        ["po_number", "po", "po_no", "purchase_order"],
    "deduction_code":   ["deduction_code", "code", "charge_type", "fee_type", "deduction type"],
    "deduction_reason": ["deduction_reason", "reason", "description", "charge_description"],
    "line_type":        ["line_type", "type", "transaction_type"],
    "gross_amount":     ["gross_amount", "gross", "invoice_amount", "billed_amount"],
    "deduction_amount": ["deduction_amount", "deduction", "amount_deducted", "charged_amount"],
    "accrual_amount":   ["accrual_amount", "accrual"],
    "reversal_amount":  ["reversal_amount", "reversal", "credit_amount"],
    "net_amount":       ["net_amount", "net", "net_payment", "payment_amount"],
    "tax_amount":       ["tax_amount", "tax", "gst", "tcs"],
    "currency":         ["currency", "ccy"],
    "payment_reference":["payment_reference", "payment_ref", "bank_ref", "utr"],
    "sku":              ["sku", "seller_sku", "item_code"],
    "asin":             ["asin"],
}

INVOICE_ALIASES: dict[str, list[str]] = {
    "invoice_number":  ["invoice_number", "invoice_no", "invoice", "bill_no"],
    "invoice_date":    ["invoice_date", "date", "bill_date"],
    "po_number":       ["po_number", "po", "purchase_order", "po_no"],
    "sku":             ["sku", "item_code", "seller_sku"],
    "asin":            ["asin"],
    "quantity":        ["quantity", "qty", "units", "ordered_qty"],
    "unit_price":      ["unit_price", "price", "rate", "cost_price"],
    "invoice_total":   ["invoice_total", "total", "amount", "gross_amount"],
    "tax_amount":      ["tax_amount", "tax", "gst", "igst"],
    "discount_amount": ["discount_amount", "discount"],
    "currency":        ["currency", "ccy"],
    "vendor_code":     ["vendor_code", "vendor_id", "supplier_code"],
}

CHARGEBACK_ALIASES: dict[str, list[str]] = {
    "chargeback_id":    ["chargeback_id", "cb_id", "id", "claim_id"],
    "deduction_code":   ["deduction_code", "code", "type", "charge_type"],
    "deduction_reason": ["deduction_reason", "reason", "description"],
    "po_number":        ["po_number", "po", "po_no"],
    "invoice_number":   ["invoice_number", "invoice", "invoice_no"],
    "shipment_id":      ["shipment_id", "shipment", "asn_id"],
    "deduction_amount": ["deduction_amount", "amount", "chargeback_amount"],
    "dispute_status":   ["dispute_status", "status", "resolution_status"],
    "created_date":     ["created_date", "date", "chargeback_date"],
    "dispute_deadline": ["dispute_deadline", "deadline", "dispute_window_end"],
}

PAYMENT_ALIASES: dict[str, list[str]] = {
    "settlement_id":  ["settlement_id", "settlement", "payment_id"],
    "bank_reference": ["bank_reference", "bank_ref", "utr", "neft_ref"],
    "paid_amount":    ["paid_amount", "amount", "payment_amount", "credit_amount"],
    "transfer_date":  ["transfer_date", "date", "payment_date", "credit_date"],
    "payment_method": ["payment_method", "method", "mode"],
    "currency":       ["currency", "ccy"],
    "bank_account":   ["bank_account", "account", "account_no"],
}

OPERATIONAL_ALIASES: dict[str, dict[str, list[str]]] = {
    "po": {
        "po_number":    ["po_number", "po", "purchase_order"],
        "sku":          ["sku", "item_code"],
        "asin":         ["asin"],
        "ordered_qty":  ["ordered_qty", "quantity", "qty"],
        "event_date":   ["po_date", "date"],
        "expected_date":["expected_delivery_date", "delivery_date"],
        "warehouse":    ["warehouse", "fulfillment_center"],
    },
    "asn": {
        "shipment_id":  ["shipment_id", "asn_id"],
        "po_number":    ["po_number", "po"],
        "sku":          ["sku"],
        "shipped_qty":  ["shipped_qty", "quantity"],
        "event_date":   ["dispatch_date", "date"],
    },
    "pod": {
        "shipment_id":  ["shipment_id"],
        "received_qty": ["received_qty", "quantity"],
        "actual_date":  ["delivery_date", "date"],
        "warehouse":    ["warehouse"],
        "receiver_name":["receiver_name", "receiver"],
    },
    "receiving": {
        "shipment_id":  ["shipment_id"],
        "sku":          ["sku"],
        "received_qty": ["received_qty", "quantity"],
        "actual_date":  ["warehouse_received_date", "date"],
        "warehouse":    ["warehouse"],
    },
    "otif": {
        "po_number":        ["po_number", "po"],
        "expected_date":    ["requested_delivery_date", "delivery_date"],
        "actual_date":      ["actual_delivery_date"],
        "fill_rate_pct":    ["fill_rate", "fill_rate_pct"],
        "compliance_status":["compliance_status", "status"],
        "penalty_amount":   ["penalty_amount", "penalty"],
    },
    "return": {
        "sku":         ["sku", "item_code"],
        "return_qty":  ["return_qty", "quantity"],
        "amount":      ["refund_amount", "amount"],
        "return_reason":["return_reason", "reason"],
        "event_date":  ["return_date", "date"],
    },
    "damage": {
        "sku":         ["sku"],
        "damaged_qty": ["damaged_qty", "quantity"],
        "amount":      ["damage_amount", "amount"],
        "warehouse":   ["warehouse"],
        "event_date":  ["date"],
    },
    "shortage": {
        "claim_id":      ["claim_id", "id"],
        "invoice_number":["invoice_number", "invoice"],
        "short_qty":     ["short_qty", "quantity"],
        "amount":        ["claim_amount", "amount"],
        "dispute_status":["status", "dispute_status"],
        "event_date":    ["date"],
    },
    "dispute_recovery": {
        "dispute_id":      ["dispute_id", "id"],
        "recovered_amount":["recovered_amount", "amount"],
        "actual_date":     ["recovery_date", "date"],
        "dispute_status":  ["dispute_status", "status"],
    },
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_col_map(df_columns: list[str], aliases: dict[str, list[str]]) -> dict[str, str]:
    """Return {canonical_name: actual_df_column} for all aliases that match."""
    lower = {c.lower().strip(): c for c in df_columns}
    mapping: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        for cand in candidates:
            if cand.lower() in lower:
                mapping[canonical] = lower[cand.lower()]
                break
    return mapping


def _safe_decimal(val: Any) -> Decimal | None:
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").strip()
        if s in ("", "nan", "NaN", "None"):
            return None
        return Decimal(s)
    except InvalidOperation:
        return None


def _safe_date(val: Any) -> date | None:
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        import pandas as pd
        ts = pd.to_datetime(str(val), dayfirst=True, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


def _safe_str(val: Any, maxlen: int = 200) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if s in ("nan", "None", ""):
        return None
    return s[:maxlen]


def _read_file(content: bytes, filename: str, fmt: str | None) -> "pd.DataFrame":
    """Parse bytes → DataFrame, auto-detect format from filename if fmt is None."""
    import pandas as pd

    fmt = (fmt or "").lower()
    name_lower = filename.lower()

    if fmt == "xlsx" or name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        return pd.read_excel(io.BytesIO(content), dtype=str)
    elif fmt == "txt" or name_lower.endswith(".txt"):
        # Try tab-separated, fall back to comma
        try:
            return pd.read_csv(io.BytesIO(content), sep="\t", dtype=str)
        except Exception:
            return pd.read_csv(io.BytesIO(content), dtype=str)
    else:
        return pd.read_csv(io.BytesIO(content), dtype=str)


# ── public parsers ────────────────────────────────────────────────────────────

def parse_settlement(
    content: bytes, filename: str, fmt: str | None,
    user_col_map: dict | None = None,
) -> tuple[list[dict], int]:
    """Returns (list_of_row_dicts, row_count)."""
    import pandas as pd
    df = _read_file(content, filename, fmt)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = _build_col_map(list(df.columns), SETTLEMENT_ALIASES)
    if user_col_map:
        col_map.update(user_col_map)

    rows = []
    for _, row in df.iterrows():
        raw = {k: (None if (str(v).strip() in ("nan", "None", "")) else str(v).strip())
               for k, v in row.items()}
        r: dict[str, Any] = {"raw_row_json": json.dumps(raw)}

        def g(field: str) -> Any:
            col = col_map.get(field)
            return row[col] if col and col in row.index else None

        r["settlement_id"]    = _safe_str(g("settlement_id"), 100)
        r["transaction_date"] = _safe_date(g("transaction_date"))
        r["reference_number"] = _safe_str(g("reference_number"), 150)
        r["invoice_number"]   = _safe_str(g("invoice_number"), 150)
        r["po_number"]        = _safe_str(g("po_number"), 150)
        r["deduction_code"]   = _safe_str(g("deduction_code"), 100)
        r["deduction_reason"] = _safe_str(g("deduction_reason"), 255)
        r["line_type"]        = _safe_str(g("line_type"), 50)
        r["gross_amount"]     = _safe_decimal(g("gross_amount"))
        r["deduction_amount"] = _safe_decimal(g("deduction_amount"))
        r["accrual_amount"]   = _safe_decimal(g("accrual_amount"))
        r["reversal_amount"]  = _safe_decimal(g("reversal_amount"))
        r["net_amount"]       = _safe_decimal(g("net_amount"))
        r["tax_amount"]       = _safe_decimal(g("tax_amount"))
        r["currency"]         = _safe_str(g("currency"), 3) or "INR"
        r["payment_reference"]= _safe_str(g("payment_reference"), 150)
        r["sku"]              = _safe_str(g("sku"), 100)
        r["asin"]             = _safe_str(g("asin"), 20)
        rows.append(r)
    return rows, len(rows)


def parse_invoice(
    content: bytes, filename: str, fmt: str | None,
    user_col_map: dict | None = None,
) -> tuple[list[dict], int]:
    import pandas as pd
    df = _read_file(content, filename, fmt)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = _build_col_map(list(df.columns), INVOICE_ALIASES)
    if user_col_map:
        col_map.update(user_col_map)

    rows = []
    for _, row in df.iterrows():
        raw = {k: (None if str(v).strip() in ("nan", "None", "") else str(v).strip())
               for k, v in row.items()}

        def g(field: str) -> Any:
            col = col_map.get(field)
            return row[col] if col and col in row.index else None

        r: dict[str, Any] = {"raw_row_json": json.dumps(raw)}
        r["invoice_number"]  = _safe_str(g("invoice_number"), 150)
        r["invoice_date"]    = _safe_date(g("invoice_date"))
        r["po_number"]       = _safe_str(g("po_number"), 150)
        r["sku"]             = _safe_str(g("sku"), 100)
        r["asin"]            = _safe_str(g("asin"), 20)
        r["quantity"]        = _safe_decimal(g("quantity"))
        r["unit_price"]      = _safe_decimal(g("unit_price"))
        r["invoice_total"]   = _safe_decimal(g("invoice_total"))
        r["tax_amount"]      = _safe_decimal(g("tax_amount"))
        r["discount_amount"] = _safe_decimal(g("discount_amount"))
        r["currency"]        = _safe_str(g("currency"), 3) or "INR"
        r["vendor_code"]     = _safe_str(g("vendor_code"), 100)
        rows.append(r)
    return rows, len(rows)


def parse_chargeback(
    content: bytes, filename: str, fmt: str | None,
    user_col_map: dict | None = None,
) -> tuple[list[dict], int]:
    df = _read_file(content, filename, fmt)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = _build_col_map(list(df.columns), CHARGEBACK_ALIASES)
    if user_col_map:
        col_map.update(user_col_map)

    rows = []
    for _, row in df.iterrows():
        raw = {k: (None if str(v).strip() in ("nan", "None", "") else str(v).strip())
               for k, v in row.items()}

        def g(field: str) -> Any:
            col = col_map.get(field)
            return row[col] if col and col in row.index else None

        r: dict[str, Any] = {"raw_row_json": json.dumps(raw)}
        r["chargeback_id"]    = _safe_str(g("chargeback_id"), 150)
        r["deduction_code"]   = _safe_str(g("deduction_code"), 100)
        r["deduction_reason"] = _safe_str(g("deduction_reason"), 255)
        r["po_number"]        = _safe_str(g("po_number"), 150)
        r["invoice_number"]   = _safe_str(g("invoice_number"), 150)
        r["shipment_id"]      = _safe_str(g("shipment_id"), 150)
        r["deduction_amount"] = _safe_decimal(g("deduction_amount"))
        r["dispute_status"]   = _safe_str(g("dispute_status"), 50)
        r["created_date"]     = _safe_date(g("created_date"))
        r["dispute_deadline"] = _safe_date(g("dispute_deadline"))
        rows.append(r)
    return rows, len(rows)


def parse_payment(
    content: bytes, filename: str, fmt: str | None,
    user_col_map: dict | None = None,
) -> tuple[list[dict], int]:
    df = _read_file(content, filename, fmt)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = _build_col_map(list(df.columns), PAYMENT_ALIASES)
    if user_col_map:
        col_map.update(user_col_map)

    rows = []
    for _, row in df.iterrows():
        raw = {k: (None if str(v).strip() in ("nan", "None", "") else str(v).strip())
               for k, v in row.items()}

        def g(field: str) -> Any:
            col = col_map.get(field)
            return row[col] if col and col in row.index else None

        r: dict[str, Any] = {"raw_row_json": json.dumps(raw)}
        r["settlement_id"]  = _safe_str(g("settlement_id"), 100)
        r["bank_reference"] = _safe_str(g("bank_reference"), 150)
        r["paid_amount"]    = _safe_decimal(g("paid_amount"))
        r["transfer_date"]  = _safe_date(g("transfer_date"))
        r["payment_method"] = _safe_str(g("payment_method"), 50)
        r["currency"]       = _safe_str(g("currency"), 3) or "INR"
        r["bank_account"]   = _safe_str(g("bank_account"), 50)
        rows.append(r)
    return rows, len(rows)


def parse_operational(
    content: bytes, filename: str, fmt: str | None,
    line_category: str,
    user_col_map: dict | None = None,
) -> tuple[list[dict], int]:
    """Parse PO/ASN/POD/OTIF/shortage/return/damage/dispute_recovery files."""
    df = _read_file(content, filename, fmt)
    df.columns = [str(c).strip() for c in df.columns]
    aliases = OPERATIONAL_ALIASES.get(line_category, {})
    col_map = _build_col_map(list(df.columns), aliases)
    if user_col_map:
        col_map.update(user_col_map)

    rows = []
    for _, row in df.iterrows():
        raw = {k: (None if str(v).strip() in ("nan", "None", "") else str(v).strip())
               for k, v in row.items()}

        def g(field: str) -> Any:
            col = col_map.get(field)
            return row[col] if col and col in row.index else None

        r: dict[str, Any] = {
            "line_category": line_category,
            "raw_row_json":  json.dumps(raw),
        }
        r["po_number"]         = _safe_str(g("po_number"), 150)
        r["invoice_number"]    = _safe_str(g("invoice_number"), 150)
        r["shipment_id"]       = _safe_str(g("shipment_id"), 150)
        r["claim_id"]          = _safe_str(g("claim_id"), 150)
        r["dispute_id"]        = _safe_str(g("dispute_id"), 150)
        r["sku"]               = _safe_str(g("sku"), 100)
        r["asin"]              = _safe_str(g("asin"), 20)
        r["event_date"]        = _safe_date(g("event_date"))
        r["expected_date"]     = _safe_date(g("expected_date"))
        r["actual_date"]       = _safe_date(g("actual_date"))
        r["ordered_qty"]       = _safe_decimal(g("ordered_qty"))
        r["shipped_qty"]       = _safe_decimal(g("shipped_qty"))
        r["received_qty"]      = _safe_decimal(g("received_qty"))
        r["short_qty"]         = _safe_decimal(g("short_qty"))
        r["damaged_qty"]       = _safe_decimal(g("damaged_qty"))
        r["return_qty"]        = _safe_decimal(g("return_qty"))
        r["amount"]            = _safe_decimal(g("amount"))
        r["penalty_amount"]    = _safe_decimal(g("penalty_amount"))
        r["recovered_amount"]  = _safe_decimal(g("recovered_amount"))
        r["compliance_status"] = _safe_str(g("compliance_status"), 50)
        r["dispute_status"]    = _safe_str(g("dispute_status"), 50)
        r["fill_rate_pct"]     = _safe_decimal(g("fill_rate_pct"))
        r["warehouse"]         = _safe_str(g("warehouse"), 100)
        r["return_reason"]     = _safe_str(g("return_reason"), 255)
        r["receiver_name"]     = _safe_str(g("receiver_name"), 150)
        rows.append(r)
    return rows, len(rows)


# ── file_type → parser + line_category routing ────────────────────────────────
OPERATIONAL_FILE_TYPES = {"po", "asn", "pod", "receiving", "otif", "return", "damage", "shortage", "dispute_recovery"}

def route_parse(
    content: bytes,
    filename: str,
    fmt: str | None,
    file_type: str,
    user_col_map: dict | None = None,
) -> tuple[str, list[dict], int]:
    """
    Returns (staging_table_name, rows, row_count).
    staging_table_name is one of:
        settlement / invoice / chargeback / payment / operational
    """
    ft = file_type.lower()
    if ft == "settlement":
        rows, n = parse_settlement(content, filename, fmt, user_col_map)
        return "settlement", rows, n
    if ft == "invoice":
        rows, n = parse_invoice(content, filename, fmt, user_col_map)
        return "invoice", rows, n
    if ft in ("chargeback", "deduction_dict"):
        rows, n = parse_chargeback(content, filename, fmt, user_col_map)
        return "chargeback", rows, n
    if ft == "payment_advice":
        rows, n = parse_payment(content, filename, fmt, user_col_map)
        return "payment", rows, n
    if ft in OPERATIONAL_FILE_TYPES:
        rows, n = parse_operational(content, filename, fmt, ft, user_col_map)
        return "operational", rows, n
    # custom / sku_master → try settlement parser as generic fallback
    rows, n = parse_settlement(content, filename, fmt, user_col_map)
    return "settlement", rows, n
