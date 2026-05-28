"""
Report Type Detection Engine.

Given a detected platform + FileFingerprint, classifies the report type:

  Flipkart:
    pl_report          — SKU-wise / Order-wise P&L (seller hub export)
    payment_report     — Quarterly Payment / Settlement report (3-level header)
    tax_report         — GSTR-1 / GSTR-8 tax report
    returns_report     — Returns listing
    commission_invoice — Commission invoice sheet
    fulfillment_report — Fulfilment / pickup / logistics report

  Amazon:
    settlement_report  — V2 Settlement flat file
    safe_t_report      — SAFE-T claims
    fba_inventory      — FBA inventory report
    returns_report     — Customer returns

  Meesho:
    payment_report     — Supplier payment statement
    returns_report     — Return orders
    order_report       — Order listing

Returns a ReportTypeResult with report_type, confidence, and schema_hints
that the schema_detector can use to match a version.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.services.detection.fingerprinter import FileFingerprint

logger = logging.getLogger(__name__)


@dataclass
class ReportTypeResult:
    report_type:   str           # canonical type string
    confidence:    float         # 0.0–1.0
    schema_hints:  Dict[str, Any] = field(default_factory=dict)
    matched_signals: List[str]   = field(default_factory=list)


# ── Flipkart report type rules ────────────────────────────────────────────────

_FLIPKART_TYPE_RULES: List[Tuple[str, List[Tuple[str, int]], str]] = [
    # (report_type, [(signal, weight)], category)
    ("payment_report", [
        ("payment details", 8),
        ("gst details",     8),
        ("payment details amount", 7),
        ("gst details fee name",   7),
        ("total payment",   5),
        ("net payment",     5),
        ("settlement amount", 5),
        ("bank account",    5),
        ("neft",            6),
    ], "sheet_or_col"),
    ("commission_invoice", [
        ("commission invoice", 9),
        ("invoice",            5),
        ("invoice amount",     6),
        ("tax invoice",        6),
        ("hsn",                5),
        ("gst amount",         4),
    ], "sheet_or_col"),
    ("tax_report", [
        ("gstr",               9),
        ("gstr-1",             9),
        ("gstr-8",             9),
        ("section 52",         8),
        ("tcs",                6),
        ("section 194",        7),
        ("taxable value",      5),
        ("integrated tax",     5),
        ("central tax",        5),
    ], "sheet_or_col"),
    ("returns_report", [
        ("return orders",      8),
        ("returns",            5),
        ("return reason",      7),
        ("return id",          7),
        ("reverse logistics",  7),
        ("return shipment",    6),
    ], "sheet_or_col"),
    ("fulfillment_report", [
        ("fulfilment",         7),
        ("pickup",             5),
        ("logistics",          5),
        ("dispatch date",      5),
        ("courier",            5),
        ("tracking id",        5),
    ], "sheet_or_col"),
    ("pl_report", [
        ("profit & loss report",         10),  # content token from cell B4
        ("profit and loss report",       10),
        ("profit & loss",                 8),
        ("pnl summary",                   9),  # section label in Overall Summary
        ("earnings on platform",          9),  # unique to Flipkart P&L
        ("bank settlement (projected)",   9),
        ("estimated net sales",           8),
        ("accounted net sales",           8),
        ("sku-level p&l",                 9),  # sheet name
        ("sku level p&l",                 9),
        ("orders p&l",                    8),
        ("sku wise",                      7),
        ("order wise",                    7),
        ("overall summary",               6),
        ("p&l",                           7),
        ("gross sales",                   5),
        ("net earnings",                  5),
        ("cancellations",                 4),
        ("total orders",                  4),
    ], "sheet_or_col"),
]

# ── Amazon report type rules ──────────────────────────────────────────────────

_AMAZON_TYPE_RULES: List[Tuple[str, List[Tuple[str, int]], str]] = [
    ("settlement_report", [
        ("settlement-id",           9),
        ("amazon-order-id",         8),
        ("shipment-id",             7),
        ("total-amount",            5),
        ("fulfillment-channel",     6),
        ("settlement",              4),
    ], "sheet_or_col"),
    ("safe_t_report", [
        ("safe-t",                  9),
        ("claim",                   5),
        ("reimbursement",           6),
    ], "sheet_or_col"),
    ("fba_inventory", [
        ("fnsku",                   8),
        ("afn-fulfillable-quantity", 9),
        ("inventory",               4),
        ("fba",                     4),
    ], "sheet_or_col"),
    ("returns_report", [
        ("return-date",             8),
        ("asin-title",              6),
        ("return-reason",           8),
    ], "sheet_or_col"),
]

# ── Meesho report type rules ──────────────────────────────────────────────────

_MEESHO_TYPE_RULES: List[Tuple[str, List[Tuple[str, int]], str]] = [
    ("payment_report", [
        ("sub order number",        9),
        ("supplier order id",       9),
        ("forward shipping charge", 7),
        ("meesho share",            8),
        ("payment cycle",           7),
    ], "sheet_or_col"),
    ("returns_report", [
        ("return type",             8),
        ("return reason",           8),
        ("return created at",       7),
    ], "sheet_or_col"),
    ("order_report", [
        ("order date",              5),
        ("delivery status",         6),
        ("customer city",           5),
    ], "sheet_or_col"),
]

_PLATFORM_RULES = {
    "flipkart": _FLIPKART_TYPE_RULES,
    "amazon":   _AMAZON_TYPE_RULES,
    "meesho":   _MEESHO_TYPE_RULES,
}

_PLATFORM_DEFAULT_TYPE = {
    "flipkart": "pl_report",
    "amazon":   "settlement_report",
    "meesho":   "payment_report",
}


def detect_report_type(
    platform: str,
    fp: FileFingerprint,
) -> ReportTypeResult:
    """
    Classify the report type given a known platform.
    Falls back to the platform's default type if nothing scores above 0.
    """
    rules = _PLATFORM_RULES.get(platform)
    if not rules:
        return ReportTypeResult(
            report_type="unknown",
            confidence=0.0,
            matched_signals=[f"no_rules_for_platform:{platform}"],
        )

    sheet_names   = {s.sheet_name.lower() for s in fp.sheets}
    all_cols      = {c.lower() for c in fp.all_column_names}
    all_tokens    = {t.lower() for t in getattr(fp, "all_content_tokens", [])}
    combined      = sheet_names | all_cols | all_tokens

    best_type  = _PLATFORM_DEFAULT_TYPE.get(platform, "unknown")
    best_score = 0
    best_signals: List[str] = []
    max_possible: Dict[str, int] = {}

    for report_type, signals, _ in rules:
        raw  = 0
        hits: List[str] = []
        total_weight = sum(w for _, w in signals)
        max_possible[report_type] = total_weight

        for pattern, weight in signals:
            for token in combined:
                if pattern in token:
                    raw += weight
                    hits.append(f"signal:{pattern}")
                    break

        if raw > best_score:
            best_score   = raw
            best_type    = report_type
            best_signals = hits

    # Normalise score
    max_w = max_possible.get(best_type, 1)
    confidence = min(1.0, best_score / max_w) if max_w > 0 else 0.0

    schema_hints = {
        "sheet_names":   list(sheet_names),
        "col_count":     len(fp.all_column_names),
        "is_multisheet": len(fp.sheets) > 1,
    }

    return ReportTypeResult(
        report_type=best_type,
        confidence=round(confidence, 4),
        schema_hints=schema_hints,
        matched_signals=best_signals,
    )
