"""
Generic CSV/XLSX Parser.

Handles marketplace reports for platforms without a dedicated parser:
  - Myntra
  - Ajio
  - Shopify
  - Custom CSV uploads

Strategy:
  1. Read the file (CSV or XLSX) into rows
  2. Fuzzy-match column headers to canonical LedgerRecord fields
  3. Emit one LedgerRecord per data row with best-effort mapping
  4. Preserve source_row_number and lineage_metadata for traceability

This parser is intentionally permissive — it never fails on unknown columns;
it maps what it can and emits warnings for unmapped fields.
"""
from __future__ import annotations

import io
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.services.parsers.base import BaseParser, LedgerRecord, ParseResult

logger = logging.getLogger(__name__)

# Canonical field → list of header patterns (lower-cased substrings to match)
_HEADER_MAP: Dict[str, List[str]] = {
    "order_id":         ["order id", "order_id", "order no", "order number", "orderid",
                         "sale order", "so number", "reference id"],
    "shipment_id":      ["shipment id", "shipment_id", "awb", "tracking", "courier"],
    "settlement_id":    ["settlement id", "settlement_id", "payment id", "payout id"],
    "sku":              ["sku", "article", "style code", "item code", "product code", "item id"],
    "product_title":    ["product name", "product title", "item name", "description", "title"],
    "category":         ["category", "department", "subcategory", "product category"],
    "amount":           ["amount", "sale amount", "revenue", "selling price", "net amount",
                         "gross amount", "total amount", "value", "price"],
    "tax_amount":       ["tax", "gst", "igst", "cgst", "sgst", "tds", "tcs"],
    "currency":         ["currency", "curr"],
    "transaction_date": ["date", "order date", "sale date", "transaction date", "created",
                         "invoice date"],
    "settlement_date":  ["settlement date", "payment date", "payout date", "transferred"],
    "transaction_type": ["type", "transaction type", "txn type", "order type"],
    "return_status":    ["return", "return status", "returned"],
    "payout_status":    ["payout status", "payment status", "settlement status"],
}

_AMOUNT_FIELDS  = {"amount", "tax_amount"}
_DATE_FIELDS    = {"transaction_date", "settlement_date"}


def _fuzzy_match(header: str, patterns: List[str]) -> bool:
    h = header.lower().strip()
    return any(p in h for p in patterns)


def _find_best_col(headers: List[str], patterns: List[str]) -> Optional[int]:
    """Return the index of the first header that fuzzy-matches any pattern."""
    for i, h in enumerate(headers):
        if _fuzzy_match(h, patterns):
            return i
    return None


def _build_col_map(headers: List[str]) -> Dict[str, int]:
    """Map canonical field name → column index."""
    col_map: Dict[str, int] = {}
    for field, patterns in _HEADER_MAP.items():
        idx = _find_best_col(headers, patterns)
        if idx is not None:
            col_map[field] = idx
    return col_map


def _safe_amount(v: Any) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        cleaned = str(v).replace(",", "").replace("₹", "").replace("$", "").strip()
        if not cleaned or cleaned in ("-", "—", "N/A", ""):
            return None
        return Decimal(cleaned)
    except Exception:
        return None


def _safe_date(v: Any) -> Optional[str]:
    if v is None:
        return None
    from app.services.normalization.value_normalizer import normalize_date
    return normalize_date(v)


def _safe_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none", "null", "-", "—") else None


def _read_rows(file_bytes: bytes, file_name: str) -> Tuple[List[str], List[List[Any]]]:
    """Read CSV or XLSX into (headers, data_rows)."""
    name_lower = file_name.lower()

    if name_lower.endswith((".xlsx", ".xls")):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            ws = wb.active
            all_rows = list(ws.iter_rows(values_only=True))
        except ImportError:
            import xlrd
            wb = xlrd.open_workbook(file_contents=file_bytes)
            ws = wb.sheet_by_index(0)
            all_rows = [ws.row_values(i) for i in range(ws.nrows)]

        if not all_rows:
            return [], []
        headers    = [str(h or "").strip() for h in all_rows[0]]
        data_rows  = [list(r) for r in all_rows[1:]]
        return headers, data_rows

    # CSV / TSV
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1", errors="replace")

    import csv as _csv
    dialect = _csv.Sniffer().sniff(text[:4096], delimiters=",\t|;")
    reader  = _csv.reader(io.StringIO(text), dialect)
    all_rows = list(reader)
    if not all_rows:
        return [], []
    headers   = [h.strip() for h in all_rows[0]]
    data_rows = all_rows[1:]
    return headers, data_rows


class GenericCSVParser(BaseParser):
    """
    Permissive parser for any tabular marketplace report.
    Registered for: myntra, ajio, shopify, custom, and as a catch-all fallback.
    """
    parser_name = "GenericCSVParser"
    platform    = "custom"
    report_type = "order_report"

    def parse(self, file_bytes: bytes, **kwargs) -> ParseResult:
        file_name     = kwargs.get("file_name", "upload.csv")
        platform_hint = kwargs.get("platform_hint", "custom")
        result = ParseResult(
            platform=platform_hint or self.platform,
            report_type=self.report_type,
            schema_version="generic_v1",
        )

        try:
            headers, data_rows = _read_rows(file_bytes, file_name)
        except Exception as exc:
            result.errors.append(f"Failed to read file: {exc}")
            return result

        if not headers:
            result.errors.append("File has no headers — cannot parse.")
            return result

        col_map = _build_col_map(headers)
        if not col_map:
            result.warnings.append(
                f"No recognizable columns found. Headers: {headers[:10]}"
            )

        unmapped = [h for i, h in enumerate(headers) if i not in col_map.values()]
        if unmapped:
            result.warnings.append(
                f"Unmapped columns (will be stored in lineage_metadata): {unmapped[:10]}"
            )

        for row_idx, row in enumerate(data_rows, start=2):
            def get(field: str) -> Any:
                idx = col_map.get(field)
                if idx is None or idx >= len(row):
                    return None
                return row[idx]

            amt = _safe_amount(get("amount"))
            # Skip entirely blank rows
            if all((v is None or str(v).strip() == "") for v in row):
                continue

            rec = LedgerRecord(
                platform         = platform_hint or self.platform,
                report_type      = self.report_type,
                order_id         = _safe_str(get("order_id")),
                shipment_id      = _safe_str(get("shipment_id")),
                settlement_id    = _safe_str(get("settlement_id")),
                sku              = _safe_str(get("sku")),
                product_title    = _safe_str(get("product_title")),
                category         = _safe_str(get("category")),
                transaction_type = _safe_str(get("transaction_type")) or "sale",
                fee_type         = None,
                amount           = amt,
                tax_amount       = _safe_amount(get("tax_amount")),
                currency         = _safe_str(get("currency")) or "INR",
                transaction_date = _safe_date(get("transaction_date")),
                settlement_date  = _safe_date(get("settlement_date")),
                return_status    = _safe_str(get("return_status")),
                payout_status    = _safe_str(get("payout_status")),
                source_row_number = row_idx,
                lineage_metadata  = {
                    "raw": {
                        h: str(row[i]) if i < len(row) else None
                        for i, h in enumerate(headers)
                        if i not in col_map.values()
                    }
                },
            )
            result.ledger_records.append(rec)

        result.raw_summary = {
            "total_rows":     len(data_rows),
            "parsed_records": len(result.ledger_records),
            "columns_mapped": len(col_map),
            "platform_hint":  platform_hint,
        }
        return result


class MyntraParser(GenericCSVParser):
    parser_name = "MyntraParser"
    platform    = "myntra"
    report_type = "order_report"


class AjioParser(GenericCSVParser):
    parser_name = "AjioParser"
    platform    = "ajio"
    report_type = "order_report"


class ShopifyParser(GenericCSVParser):
    parser_name = "ShopifyParser"
    platform    = "shopify"
    report_type = "order_report"


class CustomCSVParser(GenericCSVParser):
    parser_name = "CustomCSVParser"
    platform    = "custom"
    report_type = "order_report"
