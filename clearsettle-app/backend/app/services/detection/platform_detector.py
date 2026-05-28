"""
Platform Detection Engine.

Takes a FileFingerprint and returns a PlatformDetectionResult with:
  - detected_platform: 'flipkart' | 'amazon' | 'meesho' | 'unknown'
  - confidence_score: 0.0–1.0
  - matched_signals: list of what fired
  - needs_manual_review: True if confidence < threshold

Detection strategy:
  1. Filename pattern matching (fast, high precision)
  2. Sheet name matching
  3. Column/header signal matching (broadest, most reliable)

Signals are weighted; raw score is normalised to 0–1 by dividing by the
theoretical max score for each platform.
"""
from __future__ import annotations

import logging
import re
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
# Pattern matching is substring (lowercase) unless marked with '^' (prefix) or '$' (suffix)

_FILENAME_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    "flipkart": [
        ("flipkart",    8),
        ("fk_",         4),
        ("_fk_",        4),
        ("fk-",         3),
        ("flipkart_pl", 9),
        ("seller_report", 3),
    ],
    "amazon": [
        ("amazon",      8),
        ("amzn",        6),
        ("settlement",  3),
        ("amazon_settlement", 9),
        ("amz_",        5),
    ],
    "meesho": [
        ("meesho",      10),
        ("meesho_payment", 10),
        ("meesho_report",  10),
    ],
}

_SHEET_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    "flipkart": [
        ("p&l",               5),
        ("sku wise",          5),
        ("order wise",        5),
        ("payment details",   7),
        ("gst details",       7),
        ("commission invoice", 7),
        ("overall summary",   4),
        ("returns",           2),
    ],
    "amazon": [
        ("settlement",        6),
        ("v2 settlement",     7),
        ("other",             1),
    ],
    "meesho": [
        ("meesho",            7),
        ("payment",           2),
        ("orders",            1),
    ],
}

_COLUMN_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    "flipkart": [
        ("fsn",                          8),
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

# Max theoretical score for each platform (sum of all weights)
_MAX_SCORES: Dict[str, float] = {
    k: sum(w for _, w in _FILENAME_SIGNALS[k])
       + sum(w for _, w in _SHEET_SIGNALS[k])
       + sum(w for _, w in _COLUMN_SIGNALS[k])
    for k in ("flipkart", "amazon", "meesho")
}


def detect_platform(fp: FileFingerprint) -> PlatformDetectionResult:
    """
    Score a FileFingerprint against all platform signal catalogues.
    Returns the platform with highest normalised confidence score.
    """
    scores: Dict[str, float] = {}
    matched: Dict[str, List[str]] = {p: [] for p in ("flipkart", "amazon", "meesho")}

    fname_lower = fp.file_name.lower()
    sheet_names_lower = [s.sheet_name.lower() for s in fp.sheets]
    cols_lower = [c.lower() for c in fp.all_column_names]

    for platform in ("flipkart", "amazon", "meesho"):
        raw = 0.0

        # ── Filename signals ─────────────────────────────────────────────────
        for pattern, weight in _FILENAME_SIGNALS[platform]:
            if pattern in fname_lower:
                raw += weight
                matched[platform].append(f"filename:{pattern}")

        # ── Sheet name signals ───────────────────────────────────────────────
        for pattern, weight in _SHEET_SIGNALS[platform]:
            for sname in sheet_names_lower:
                if pattern in sname:
                    raw += weight
                    matched[platform].append(f"sheet:{pattern}")
                    break  # count once per pattern even if in multiple sheets

        # ── Column signals ───────────────────────────────────────────────────
        for pattern, weight in _COLUMN_SIGNALS[platform]:
            for col in cols_lower:
                if pattern in col:
                    raw += weight
                    matched[platform].append(f"col:{pattern}")
                    break

        scores[platform] = raw

    # Normalise to 0-1 using the max theoretical score but cap at 1.0
    norm = {
        p: min(1.0, scores[p] / _MAX_SCORES[p]) if _MAX_SCORES[p] > 0 else 0.0
        for p in scores
    }

    ranked = sorted(norm.items(), key=lambda x: x[1], reverse=True)
    best_platform, best_score = ranked[0]
    runner_up_platform, runner_up_score = (ranked[1][0], ranked[1][1]) if len(ranked) > 1 else (None, 0.0)

    if best_score < 0.05:
        best_platform = "unknown"

    return PlatformDetectionResult(
        detected_platform=best_platform,
        confidence_score=round(best_score, 4),
        matched_signals=matched.get(best_platform, []),
        runner_up_platform=runner_up_platform,
        runner_up_score=round(runner_up_score, 4),
        needs_manual_review=best_score < AUTO_PROCESS_THRESHOLD or best_platform == "unknown",
    )
