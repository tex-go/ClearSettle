"""
Internal data models for the reconciliation engine.

These dataclasses are the contract between detectors and the engine.
They are never persisted directly — storage.py converts them to ORM rows.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass
class RuleConfig:
    id:          UUID
    rule_type:   str
    rule_name:   str
    severity:    str
    parameters:  dict
    platform:    str | None = None


@dataclass
class DiscrepancyCandidate:
    discrepancy_type: str
    severity:         str
    description:      str
    rule_id:          UUID | None     = None
    transaction_id:   UUID | None     = None
    order_id:         str  | None     = None
    fee_type:         str  | None     = None
    expected_amount:  Decimal | None  = None
    actual_amount:    Decimal | None  = None
    variance_amount:  Decimal | None  = None
    metadata:         dict            = field(default_factory=dict)


@dataclass
class DetectorLog:
    """Per-detector execution record stored in reconciliation_results.metadata_json."""
    rule_type:  str
    rule_name:  str
    fired:      int        # number of discrepancies produced
    elapsed_ms: int        # wall-clock time for this detector
    error:      str | None = None


@dataclass
class ReconciliationRunResult:
    settlement_id:         UUID
    company_id:            UUID
    platform:              str
    status:                str            # clean | warning | critical | error
    discrepancies:         list[DiscrepancyCandidate]
    rules_evaluated:       int
    processing_time_ms:    int
    total_variance_amount: Decimal
    error_message:         str | None         = None
    execution_log:         list[DetectorLog]  = field(default_factory=list)
    loaded_transactions:   int                = 0
    loaded_fees:           int                = 0
