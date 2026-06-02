"""
Schema Version Detector.

Compares a file's column fingerprint against known schema versions
in the report_schema_versions catalogue.

If no match is found:
  - generates a SchemaDriftAlert
  - records the unknown schema for admin review
  - falls back to the most recent active version for the platform+report_type

The KNOWN_SCHEMAS dict below is the static baseline. Production schemas
are also stored in report_schema_versions DB table and loaded at runtime.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.detection.fingerprinter import FileFingerprint

logger = logging.getLogger(__name__)

# Minimum Jaccard similarity (intersection / union) to consider a schema match
SCHEMA_MATCH_THRESHOLD = 0.60


@dataclass
class SchemaMatchResult:
    schema_version:   str
    parser_name:      str
    match_confidence: float             # Jaccard similarity
    missing_columns:  List[str]         # expected but not found
    extra_columns:    List[str]         # found but not in expected
    is_exact_match:   bool


@dataclass
class SchemaDriftAlert:
    platform:        str
    report_type:     str
    schema_signature: str               # SHA-256 of actual columns
    missing_columns: List[str]
    extra_columns:   List[str]
    nearest_version: str | None
    nearest_similarity: float
    message:         str


@dataclass
class SchemaDetectionResult:
    schema_version:   str               # matched version string or 'unknown'
    parser_name:      str               # parser class name to use
    match_confidence: float
    drift_alert:      SchemaDriftAlert | None = None


# ── Known schema catalogue ────────────────────────────────────────────────────
# Structure: platform → report_type → version → {expected_columns, optional_columns, parser_name}

KNOWN_SCHEMAS: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {
    "flipkart": {
        "pl_report": {
            "flipkart_pl_v1": {
                "expected": [
                    "sku", "product title", "category", "selling price", "mrp",
                    "total orders", "qty sold", "gross sales",
                    "returns qty", "returns value",
                    "cancellations qty", "cancellations value",
                    "net sales", "commission", "shipping charges",
                    "reverse shipping", "other fees", "net earnings",
                ],
                "optional": ["margin pct", "return rate pct", "cancellation rate pct"],
                "parser": "FlipkartPLParser",
            },
        },
        "payment_report": {
            "flipkart_payment_v1": {
                "expected": [
                    "order item id", "order date", "sku", "product title",
                    "sale amount", "commission", "fixed fee",
                    "shipping fee", "reverse shipping fee",
                    "collection fee", "settlement amount",
                ],
                "optional": [
                    "tcs igst", "tcs cgst", "tcs sgst",
                    "tds", "wallet redeem", "super coin cashback",
                ],
                "parser": "FlipkartPaymentParser",
            },
        },
        "returns_report": {
            "flipkart_returns_v1": {
                "expected": [
                    "order id", "return id", "return date", "sku",
                    "product title", "return reason", "return status",
                ],
                "optional": ["refund amount", "reverse shipping charge"],
                "parser": "FlipkartPLParser",
            },
        },
    },
    "amazon": {
        "settlement_report": {
            "amazon_settlement_v2": {
                "expected": [
                    "settlement-id", "settlement-start-date", "settlement-end-date",
                    "deposit-date", "total-amount", "currency",
                    "transaction-type", "order-id", "shipment-id",
                    "amazon-order-id", "fulfillment-channel", "type",
                    "amount-type", "amount-description", "amount",
                ],
                "optional": [
                    "quantity-purchased", "merchant-order-id", "sku",
                    "promotion-id", "marketplace-name",
                ],
                "parser": "AmazonSettlementParser",
            },
        },
    },
    "meesho": {
        "payment_report": {
            "meesho_payment_v1": {
                "expected": [
                    "sub order number", "supplier order id",
                    "order date", "product name",
                    "supply price", "customer price",
                    "forward shipping charge", "reverse shipping charge",
                    "tds on commission", "meesho share", "payment cycle",
                ],
                "optional": [
                    "penalty amount", "meesho wallet", "sku",
                    "product category",
                ],
                "parser": "MeeshoPaymentParser",
            },
        },
    },
}


def detect_schema_version(
    platform: str,
    report_type: str,
    fp: FileFingerprint,
) -> SchemaDetectionResult:
    """
    Match fp.all_column_names against known schemas for (platform, report_type).
    Returns the best matching version or flags a drift alert.
    """
    known_for_type = KNOWN_SCHEMAS.get(platform, {}).get(report_type, {})

    if not known_for_type:
        # No known schemas → flag as drift and use generic fallback parser
        alert = SchemaDriftAlert(
            platform=platform,
            report_type=report_type,
            schema_signature=fp.schema_signature,
            missing_columns=[],
            extra_columns=list(fp.all_column_names),
            nearest_version=None,
            nearest_similarity=0.0,
            message=(
                f"No known schema for platform='{platform}' report_type='{report_type}'. "
                "File will require manual review or a new schema version to be registered."
            ),
        )
        return SchemaDetectionResult(
            schema_version="unknown",
            parser_name=_default_parser(platform, report_type),
            match_confidence=0.0,
            drift_alert=alert,
        )

    actual_cols = {_clean(c) for c in fp.all_column_names}
    best_version:    Optional[str]   = None
    best_similarity: float           = 0.0
    best_missing:    List[str]       = []
    best_extra:      List[str]       = []
    best_parser:     str             = ""

    for version, spec in known_for_type.items():
        expected   = {_clean(c) for c in spec.get("expected", [])}
        optional_s = {_clean(c) for c in spec.get("optional", [])}
        relevant   = expected | optional_s

        # Use Jaccard similarity against the required + optional set
        if not relevant:
            continue
        intersection = actual_cols & relevant
        union        = actual_cols | relevant
        similarity   = len(intersection) / len(union) if union else 0.0

        if similarity > best_similarity:
            best_similarity = similarity
            best_version    = version
            best_parser     = spec.get("parser", _default_parser(platform, report_type))
            best_missing    = sorted(expected - actual_cols)
            best_extra      = sorted(actual_cols - relevant)

    if best_version and best_similarity >= SCHEMA_MATCH_THRESHOLD:
        return SchemaDetectionResult(
            schema_version=best_version,
            parser_name=best_parser,
            match_confidence=round(best_similarity, 4),
            drift_alert=None,
        )

    # Below threshold — raise drift alert, still use nearest version as fallback
    alert = SchemaDriftAlert(
        platform=platform,
        report_type=report_type,
        schema_signature=fp.schema_signature,
        missing_columns=best_missing,
        extra_columns=best_extra[:30],
        nearest_version=best_version,
        nearest_similarity=round(best_similarity, 4),
        message=(
            f"Schema drift detected for {platform}/{report_type}. "
            f"Nearest match '{best_version}' has similarity {best_similarity:.2%}. "
            f"Missing: {best_missing[:5]}. "
            "Verify parser compatibility before processing."
        ),
    )
    logger.warning("Schema drift: %s", alert.message)

    return SchemaDetectionResult(
        schema_version=best_version or "unknown",
        parser_name=best_parser or _default_parser(platform, report_type),
        match_confidence=round(best_similarity, 4),
        drift_alert=alert,
    )


def compute_schema_signature(columns: List[str]) -> str:
    canonical = "|".join(sorted(_clean(c) for c in columns))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _clean(col: str) -> str:
    return " ".join(col.lower().strip().split())


def _default_parser(platform: str, report_type: str) -> str:
    defaults = {
        ("flipkart", "pl_report"):         "FlipkartPLParser",
        ("flipkart", "payment_report"):    "FlipkartPaymentParser",
        ("flipkart", "returns_report"):    "FlipkartPLParser",
        ("amazon",   "settlement_report"): "AmazonSettlementParser",
        ("meesho",   "payment_report"):    "MeeshoPaymentParser",
        ("myntra",   "order_report"):      "MyntraParser",
        ("ajio",     "order_report"):      "AjioParser",
        ("shopify",  "order_report"):      "ShopifyParser",
        ("custom",   "order_report"):      "CustomCSVParser",
    }
    # Generic CSV parser is the fallback for all other known platforms
    generic_platforms = {"myntra", "ajio", "shopify", "custom"}
    if platform in generic_platforms:
        return defaults.get((platform, report_type), "GenericCSVParser")
    return defaults.get((platform, report_type), "GenericCSVParser")
