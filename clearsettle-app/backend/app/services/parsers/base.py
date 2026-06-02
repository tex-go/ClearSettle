"""
BaseParser abstract class and shared data contracts.

Every platform parser must subclass BaseParser and implement parse().
The parse() method returns a ParseResult containing:
  - ledger_records: list of LedgerRecord (canonical row per transaction)
  - errors: list of non-fatal parse errors
  - warnings: list of schema/data quality warnings
  - raw_summary: platform-specific KPI summary dict

Design rules:
  - Never raise; capture errors into ParseResult.errors
  - Preserve source_row_number for every ledger record
  - Every LedgerRecord must have a non-null platform
  - Parsers must be stateless — no side effects, no DB calls
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class LedgerRecord:
    """Canonical per-transaction record. Maps directly to ingestion_ledger table."""
    platform:         str
    report_type:      str
    order_id:         Optional[str]   = None
    shipment_id:      Optional[str]   = None
    settlement_id:    Optional[str]   = None
    invoice_id:       Optional[str]   = None
    sku:              Optional[str]   = None
    product_title:    Optional[str]   = None
    category:         Optional[str]   = None
    transaction_type: Optional[str]   = None    # sale | return | cancellation | fee | tax | payout
    fee_type:         Optional[str]   = None
    amount:           Optional[Decimal] = None
    tax_amount:       Optional[Decimal] = None
    currency:         str             = "INR"
    transaction_date: Optional[str]   = None    # ISO YYYY-MM-DD
    settlement_date:  Optional[str]   = None
    return_status:    Optional[str]   = None
    payout_status:    Optional[str]   = None
    source_row_number: Optional[int]  = None
    lineage_metadata: Dict[str, Any]  = field(default_factory=dict)


@dataclass
class ParseResult:
    platform:        str
    report_type:     str
    schema_version:  str
    ledger_records:  List[LedgerRecord]     = field(default_factory=list)
    raw_summary:     Dict[str, Any]         = field(default_factory=dict)
    errors:          List[str]              = field(default_factory=list)
    warnings:        List[str]              = field(default_factory=list)
    recon_issues:    List[Dict[str, Any]]   = field(default_factory=list)

    @property
    def record_count(self) -> int:
        return len(self.ledger_records)

    @property
    def is_empty(self) -> bool:
        return not self.ledger_records

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


class BaseParser(abc.ABC):
    """
    Abstract base for all platform parsers.

    Subclasses implement parse(file_bytes, **kwargs) → ParseResult.
    They must:
      1. Call _make_result() to create the result container
      2. Fill result.ledger_records with LedgerRecord instances
      3. Fill result.errors / result.warnings for non-fatal issues
      4. Fill result.raw_summary with platform-specific KPIs
      5. Never raise — capture exceptions into result.errors
    """

    #: Set by subclass — matches parser_name in KNOWN_SCHEMAS and registry
    parser_name: str = "BaseParser"
    platform:    str = "unknown"
    report_type: str = "unknown"

    @abc.abstractmethod
    def parse(self, file_bytes: bytes, **kwargs: Any) -> ParseResult:
        """Parse raw file bytes and return a ParseResult."""

    def _make_result(self, schema_version: str = "unknown") -> ParseResult:
        return ParseResult(
            platform=self.platform,
            report_type=self.report_type,
            schema_version=schema_version,
        )

    def _safe_decimal(self, v: Any) -> Optional[Decimal]:
        from app.services.normalization.value_normalizer import normalize_amount
        return normalize_amount(v)

    def _safe_date(self, v: Any) -> Optional[str]:
        from app.services.normalization.value_normalizer import normalize_date
        return normalize_date(v)

    def _safe_str(self, v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s and s.lower() not in ("nan", "none", "null", "-") else None
