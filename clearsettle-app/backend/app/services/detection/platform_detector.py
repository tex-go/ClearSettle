"""
Platform Detection Engine.

Takes a FileFingerprint and returns a PlatformDetectionResult with:
  - detected_platform: 'flipkart' | 'amazon' | 'meesho' | 'unknown'
  - confidence_score: 0.0–1.0
  - matched_signals: list of what fired
  - needs_manual_review: True if confidence < threshold

Detection strategy (4 tiers):
  1. Filename pattern matching (fast, high precision)
  2. Sheet name matching
  3. Column/header signal matching
  4. Content token matching (cell VALUES from first 100 rows per sheet)
     ← Critical for Flipkart P&L reports where key identifiers appear as
       row-values, not column names ("Profit & Loss Report", "Earnings on
       Platform", "PNL Summary", "Bank Settlement (Projected)", etc.)

Signals are weighted; raw score is normalised to 0–1 by dividing by the
theoretical max score for each platform.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from app.services.detection.fingerprinter import FileFingerprint

logger = logging.getLogger(__name__)

# Minimum confidence to auto-process without manual review
AUTO_PROCESS_THRESHOLD = 0.55


@dataclass
class PlatformDetectionResult:
    detected_platform:   str                 # flipkart | amazon | meesho | unknown
    confidence_score:    float               # 0.0–1.0
    matched_signals:     List[str]
    runner_up_platform:  str | None = None
    runner_up_score:     float = 0.0
    needs_manual_review: bool = False


# ── Signal catalogue ──────────────────────────────────────────────────────────
# Each signal is (pattern_string, score_weight)
# Matching is substring (lowercase).

_FILENAME_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    "flipkart": [
        ("flipkart",          9),
        ("profit and loss",   9),  # "Profit and Loss Report"
        ("profit_and_loss",   9),
        ("p&l",               8),  # "P&L Report"
        ("pnl",               7),  # "PNL_Report"
        ("fk_",               4),
        ("_fk_",              4),
        ("fk-",               3),
        ("flipkart_pl",       9),
        ("seller_report",     3),
        ("pl_report",         8),
        ("overall_summary",   5),
        # Quarterly payment settlement reports from Flipkart Seller Hub
        ("payment_report",    8),  # "tip_top_payment_report_april2026"
        ("payment report",    8),
        ("settlement_report", 6),
        ("seller_payment",    7),
    ],
    "amazon": [
        ("amazon",            8),
        ("amzn",              6),
        ("settlement",        3),
        ("amazon_settlement", 9),
        ("amz_",              5),
    ],
    "meesho": [
        ("meesho",            10),
        ("meesho_payment",    10),
        ("meesho_report",     10),
    ],
    "myntra": [
        ("myntra",            10),
        ("myntra_order",      10),
        ("myntra_payment",    10),
    ],
    "ajio": [
        ("ajio",              10),
        ("ajio_order",        10),
        ("ajio_payment",      10),
    ],
    "shopify": [
        ("shopify",           10),
        ("shopify_order",     10),
        ("shopify_payout",    10),
    ],
}

_SHEET_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    "flipkart": [
        ("p&l",                  7),   # "SKU-level P&L", "Orders P&L"
        ("sku-level p&l",        9),
        ("sku level p&l",        9),
        ("orders p&l",           8),
        ("order p&l",            8),
        ("sku wise",             5),
        ("order wise",           5),
        ("overall summary",      6),   # P&L summary tab
        ("payment details",      7),
        ("gst details",          7),
        ("gst_details",          7),   # underscore variant in payment reports
        ("commission invoice",   7),
        ("report help",          4),   # P&L has a "Report Help" tab
        ("returns",              2),
        ("neft_summary",         8),   # quarterly payment report
        ("neft summary",         8),
        ("ads",                  3),
        ("tcs_recovery",         7),   # TCS recovery sheet
        ("tds_recovery",         7),
        ("non_order_spf",        6),
        ("summary of report",    7),   # quarterly payment report summary sheet
    ],
    "amazon": [
        ("settlement",           6),
        ("v2 settlement",        7),
        ("other",                1),
    ],
    "meesho": [
        ("meesho",               7),
        ("payment",              2),
        ("orders",               1),
    ],
}

_COLUMN_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    "flipkart": [
        ("fsn",                          9),
        ("seller sku id",                7),
        ("fixed fee",                    7),
        ("reverse shipping fee",         8),
        ("super coin",                   8),
        ("wallet redeem",                8),
        ("seller protection fund",       8),
        ("pick and pack fee",            8),
        ("closing fee",                  6),
        ("flipkart fulfilled",           7),
        ("seller fulfilled",             5),
        ("commission rate",              5),
        ("dispatched quantity",          5),
        ("flipkart assured",             7),
        ("collection fee",               5),
        ("listing id",                   4),
        ("payment details amount",       6),
        ("gst details fee name",         7),
        ("gst details igst",             6),
        ("shipment zone",                5),
        ("return type",                  4),
        ("gross sales",                  5),   # column in P&L reports
        ("net earnings",                 5),
        ("estimated net sales",          6),
        ("earnings on platform",         9),   # unique to Flipkart P&L
        # Quarterly payment settlement report columns (seller hub download)
        ("bank settlement value",        9),   # unique to Flipkart payment report
        ("neft id",                      8),   # NEFT transfer ID
        ("sale amount (rs.)",            8),
        ("tcs (rs.)",                    7),   # tax collected at source
        ("tds (rs.)",                    7),   # tax deducted at source
        ("gst on mp fees (rs.)",         8),
        ("commission (rs.)",             6),
        ("fixed fee  (rs.)",             7),
        ("reverse shipping fee (rs.)",   8),
        ("item return status",           6),
        ("seller sku",                   5),
        ("product sub category",         5),
        ("my share (rs.)",               7),   # seller's offer share column
        ("no cost emi fee",              6),
        ("shopsy",                       5),
    ],
    "amazon": [
        ("amazon-order-id",              10),
        ("shipment-id",                  7),
        ("fulfillment-channel",          7),
        ("fba-per-unit-fulfillment-fee", 9),
        ("referral-fee",                 7),
        ("settlement-id",                7),
        ("total-amount",                 5),
        ("marketplace-name",             6),
        ("safe-t-reimbursement",         8),
        ("asin",                         5),
        ("fnsku",                        6),
        ("warehouse-damage",             6),
        ("disposal-fee",                 5),
        ("amazon-fees",                  6),
        ("principal charges",            4),
        ("promotion principal charges",  5),
    ],
    "meesho": [
        ("sub order number",             9),
        ("supplier order id",            9),
        ("forward shipping charge",      8),
        ("reverse shipping charge",      8),
        ("tds on commission",            8),
        ("supply price",                 7),
        ("customer price",               6),
        ("meesho share",                 9),
        ("penalty amount",               6),
        ("reseller",                     6),
        ("commission rate",              4),
        ("supplier",                     3),
        ("payment cycle",                6),
        ("meesho wallet",                8),
    ],
}

# ── Content signals (match against cell VALUES, not column names) ─────────────
# These fire on what's actually written INSIDE the cells — critical for
# Flipkart P&L reports where the report structure uses row labels.
_CONTENT_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    "flipkart": [
        # Report header / metadata rows
        ("profit & loss report",         10),  # B4: "Profit & Loss Report"
        ("profit and loss report",       10),
        ("profit & loss",                 8),
        # Section labels unique to Flipkart P&L
        ("earnings on platform",         10),  # A53 in Overall Summary
        ("bank settlement (projected)",  10),  # A48
        ("pnl summary",                   9),  # A9
        ("settlement summary",            8),  # A56
        ("estimated net sales",           8),  # A17
        ("accounted net sales",           8),  # A20
        ("returns and cancellations",     8),  # A12
        ("total expenses",                7),  # A21
        ("rewards & other benefits",      7),  # A43
        ("input tax credits",             7),  # A49
        ("net margin",                    6),
        # Fee types that appear as row labels in P&L breakdown
        ("flipkart",                     10),  # if "Flipkart" appears anywhere as a value
        ("wallet redeem",                 9),
        ("seller protection fund",        9),
        ("super coin",                    8),
        ("pick and pack fee",             8),
        ("closing fee",                   7),
        ("reverse shipping fee",          8),
        ("fixed fee",                     7),
        ("collection fee",                6),
        ("shipment zone",                 6),
        ("fsn",                           8),  # SKU identifier
        ("commission invoice",            7),
        ("flipkart assured",              8),
    ],
    "amazon": [
        ("amazon",                       10),
        ("fulfillment by amazon",        10),
        ("seller central",                9),
        ("amazon.in",                     9),
        ("fba",                           7),
        ("asin",                          8),
        ("safe-t",                        8),
        ("amazon order id",              10),
        ("marketplace facilitator",       8),
        ("principal",                     5),
        ("referral fee",                  7),
    ],
    "meesho": [
        ("meesho",                       10),
        ("supplier panel",                9),
        ("meesho share",                  9),
        ("sub order number",              9),
        ("payment cycle",                 8),
        ("forward shipping charge",       8),
        ("tds on commission",             8),
        ("meesho wallet",                 8),
    ],
    "myntra": [
        ("myntra",                       10),
        ("myntra.com",                    9),
    ],
    "ajio": [
        ("ajio",                         10),
        ("ajio.com",                      9),
        ("reliance retail",               8),
    ],
    "shopify": [
        ("shopify",                      10),
        ("shopify.com",                   9),
        ("shopify payments",              8),
    ],
}

# Sheet signals for new platforms
for _p in ("myntra", "ajio", "shopify"):
    if _p not in _SHEET_SIGNALS:
        _SHEET_SIGNALS[_p] = [(_p, 8)]

# Column signals for new platforms
_COLUMN_SIGNALS.setdefault("myntra",  [("myntra order id", 10), ("style id", 7), ("vendor id", 6)])
_COLUMN_SIGNALS.setdefault("ajio",    [("ajio order id", 10), ("site order id", 8), ("courier partner", 6)])
_COLUMN_SIGNALS.setdefault("shopify", [("shopify order", 10), ("variant sku", 7), ("payment gateway", 8)])

# Max theoretical score for each platform (sum of all signal weights across all tiers)
_MAX_SCORES: Dict[str, float] = {
    k: (
        sum(w for _, w in _FILENAME_SIGNALS.get(k, []))
        + sum(w for _, w in _SHEET_SIGNALS.get(k, []))
        + sum(w for _, w in _COLUMN_SIGNALS.get(k, []))
        + sum(w for _, w in _CONTENT_SIGNALS.get(k, []))
    )
    for k in ("flipkart", "amazon", "meesho", "myntra", "ajio", "shopify")
}


_ALL_PLATFORMS = ("flipkart", "amazon", "meesho", "myntra", "ajio", "shopify")


def detect_platform(fp: FileFingerprint) -> PlatformDetectionResult:
    """
    Score a FileFingerprint against all platform signal catalogues.
    Returns the platform with highest normalised confidence score.
    """
    scores: Dict[str, float] = {}
    matched: Dict[str, List[str]] = {p: [] for p in _ALL_PLATFORMS}

    fname_lower        = fp.file_name.lower()
    sheet_names_lower  = [s.sheet_name.lower() for s in fp.sheets]
    cols_lower         = [c.lower() for c in fp.all_column_names]
    tokens_lower       = [t.lower() for t in fp.all_content_tokens]

    for platform in _ALL_PLATFORMS:
        raw = 0.0

        # ── Tier 1: Filename signals ──────────────────────────────────────────
        for pattern, weight in _FILENAME_SIGNALS.get(platform, []):
            if pattern in fname_lower:
                raw += weight
                matched[platform].append(f"filename:{pattern}")

        # ── Tier 2: Sheet name signals ────────────────────────────────────────
        for pattern, weight in _SHEET_SIGNALS.get(platform, []):
            for sname in sheet_names_lower:
                if pattern in sname:
                    raw += weight
                    matched[platform].append(f"sheet:{pattern}")
                    break  # count once per pattern even if in multiple sheets

        # ── Tier 3: Column/header signals ─────────────────────────────────────
        for pattern, weight in _COLUMN_SIGNALS.get(platform, []):
            for col in cols_lower:
                if pattern in col:
                    raw += weight
                    matched[platform].append(f"col:{pattern}")
                    break

        # ── Tier 4: Content token signals (cell values) ───────────────────────
        for pattern, weight in _CONTENT_SIGNALS.get(platform, []):
            for tok in tokens_lower:
                if pattern in tok:
                    raw += weight
                    matched[platform].append(f"content:{pattern}")
                    break

        scores[platform] = raw

    # Normalise to 0–1 using the max theoretical score (for display transparency)
    norm = {
        p: min(1.0, scores[p] / _MAX_SCORES[p]) if _MAX_SCORES.get(p, 0) > 0 else 0.0
        for p in scores
    }

    ranked = sorted(norm.items(), key=lambda x: x[1], reverse=True)
    best_platform, best_score = ranked[0]
    runner_up_platform, runner_up_score = (
        (ranked[1][0], ranked[1][1]) if len(ranked) > 1 else (None, 0.0)
    )

    if best_score < 0.03:
        best_platform = "unknown"

    # Dominance check: winner must hold ≥60% of the total raw signal score
    # AND accumulate at least 20 raw points (prevents noise-only matches).
    # This is more reliable than a fixed normalised threshold because the
    # theoretical max is unreachable — no single file type fires all signals.
    total_raw = sum(scores.values())
    best_raw  = scores.get(best_platform, 0)
    share     = best_raw / total_raw if total_raw > 0 else 0.0
    dominance_ok = (share >= 0.60) and (best_raw >= 20) and (best_platform != "unknown")

    return PlatformDetectionResult(
        detected_platform=best_platform,
        confidence_score=round(best_score, 4),
        matched_signals=matched.get(best_platform, []),
        runner_up_platform=runner_up_platform,
        runner_up_score=round(runner_up_score, 4),
        needs_manual_review=not dominance_ok,
    )
