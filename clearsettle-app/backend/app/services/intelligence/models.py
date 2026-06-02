"""
Pydantic models for all 14 agent outputs and the aggregated PipelineResult.

Every agent produces one of these typed result objects, which are then
aggregated into a PipelineResult that is stored as JSON in
ReportDetectionResult.detection_metadata and returned by
GET /ingestion/files/{id}/intelligence.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    success = "success"
    warning = "warning"
    error = "error"
    skipped = "skipped"


class AgentResult(BaseModel):
    agent_id: int
    agent_name: str
    status: AgentStatus
    duration_ms: float
    messages: List[str] = []


# ── Agent 1: Intake ───────────────────────────────────────────────────────────

class IntakeResult(AgentResult):
    upload_id: str
    file_hash: str
    file_size_bytes: int
    mime_type: str
    is_corrupt: bool
    encoding: Optional[str]
    supported_format: bool
    format_type: str  # xlsx/xls/csv/tsv/pdf/zip/json/xml


# ── Agent 2: Structure ────────────────────────────────────────────────────────

class StructureResult(AgentResult):
    sheet_count: int
    sheets: List[Dict[str, Any]]  # [{name, row_count, col_count, headers, has_merged_cells}]
    has_multi_section: bool
    has_hidden_sheets: bool
    detected_date_range: Optional[str]
    detected_report_title: Optional[str]
    total_data_rows: int
    blueprint: Dict[str, Any]


# ── Agent 3: Platform ─────────────────────────────────────────────────────────

class PlatformResult(AgentResult):
    platform: str
    confidence: float
    matched_signals: List[str]
    runner_up: Optional[str]
    runner_up_confidence: float
    needs_manual_review: bool
    reason: str


# ── Agent 4: Classification ───────────────────────────────────────────────────

class ClassificationResult(AgentResult):
    report_type: str
    report_type_label: str
    confidence: float
    matched_signals: List[str]
    schema_hints: Dict[str, Any]


# ── Agent 5: Schema ───────────────────────────────────────────────────────────

class FieldMapping(BaseModel):
    source_column: str
    universal_field: str
    confidence: float
    transform: Optional[str]  # e.g. "abs", "negate", "date_parse"


class SchemaResult(AgentResult):
    schema_version: str
    mapped_fields: List[FieldMapping]
    unmapped_columns: List[str]
    mapping_coverage: float  # % of columns mapped
    drift_detected: bool
    drift_details: Optional[Dict[str, Any]]


# ── Agent 6: Quality ──────────────────────────────────────────────────────────

class QualityIssue(BaseModel):
    severity: str  # error/warning/info
    code: str
    message: str
    affected_rows: Optional[int]
    affected_column: Optional[str]


class QualityResult(AgentResult):
    quality_score: float  # 0-100
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    null_critical_fields: int
    type_mismatch_count: int
    is_duplicate_upload: bool
    issues: List[QualityIssue]


# ── Agent 7: Financial ────────────────────────────────────────────────────────

class FinancialField(BaseModel):
    field: str
    value: Decimal
    currency: str = "INR"
    column_source: Optional[str]


class FinancialResult(AgentResult):
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    currency: str
    revenue: FinancialField
    settlement: FinancialField
    total_fees: FinancialField
    commission: FinancialField
    shipping: FinancialField
    returns: FinancialField
    refunds: FinancialField
    tcs: FinancialField
    tds: FinancialField
    gst: FinancialField
    adjustments: FinancialField
    advertising_spend: FinancialField
    net_payout: FinancialField
    fact_model: Dict[str, Any]


# ── Agent 8: Metrics ──────────────────────────────────────────────────────────

class MetricsResult(AgentResult):
    # Sales
    gross_sales: Decimal
    net_sales: Decimal
    average_order_value: Decimal
    total_orders: int
    # Settlement
    expected_settlement: Decimal
    actual_settlement: Decimal
    settlement_efficiency: float  # %
    # Returns
    return_rate: float
    refund_rate: float
    return_value: Decimal
    # Fees
    total_marketplace_fees: Decimal
    total_logistics_fees: Decimal
    fee_percentage: float
    hidden_deductions: Decimal
    # Advertising (if applicable)
    ad_spend: Decimal
    acos: Optional[float]
    roas: Optional[float]


# ── Agent 9: Readiness ────────────────────────────────────────────────────────

class ReconciliationStatus(str, Enum):
    full_ready = "full_reconciliation_ready"
    partial = "partial_reconciliation"
    insufficient = "insufficient_data"
    single_report = "single_report"


class ReadinessResult(AgentResult):
    reconciliation_status: ReconciliationStatus
    readiness_score: float  # 0-100
    uploaded_report_types: List[str]
    missing_report_types: List[str]
    recommended_uploads: List[str]
    can_reconcile_orders: bool
    can_reconcile_settlement: bool
    can_reconcile_returns: bool
    can_reconcile_gst: bool


# ── Agent 10: Reconciliation ──────────────────────────────────────────────────

class Discrepancy(BaseModel):
    type: str  # order_settlement_gap / fee_overcharge / return_not_refunded / etc.
    severity: str  # high/medium/low
    order_id: Optional[str]
    expected_amount: Decimal
    actual_amount: Decimal
    gap: Decimal
    description: str
    recoverable: bool


class ReconciliationResult(AgentResult):
    discrepancy_count: int
    total_leakage: Decimal
    total_recoverable: Decimal
    discrepancies: List[Discrepancy]
    reconciliation_type: str  # order_vs_settlement / fee_audit / return_audit / etc.
    summary: Dict[str, Any]


# ── Agent 11: Insights ────────────────────────────────────────────────────────

class Insight(BaseModel):
    category: str  # revenue / fees / returns / settlement / compliance / opportunity
    severity: str  # info / warning / critical
    title: str
    message: str
    metric_value: Optional[str]
    action: Optional[str]


class InsightsResult(AgentResult):
    insights: List[Insight]
    total_insights: int
    critical_count: int
    opportunity_amount: Decimal  # total recoverable found


# ── Agent 12: Registry ────────────────────────────────────────────────────────

class RegistryResult(AgentResult):
    schema_registered: bool
    schema_version: str
    is_new_schema: bool
    variants_known: int
    registry_id: Optional[str]


# ── Agent 13: Audit ───────────────────────────────────────────────────────────

class AuditResult(AgentResult):
    audit_id: str
    checksum_verified: bool
    lineage_stored: bool
    agent_decisions_logged: int
    storage_path: str
    explainability_score: float  # 0-100


# ── Agent 14: Learning ────────────────────────────────────────────────────────

class LearningResult(AgentResult):
    feedback_applied: bool
    confidence_adjusted: bool
    new_signals_learned: int
    model_version: str
    notes: str


# ── PipelineResult ────────────────────────────────────────────────────────────

class PipelineResult(BaseModel):
    pipeline_id: str
    upload_id: str
    company_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: float = 0.0
    pipeline_status: str  # success/partial/failed/running

    # Agent results
    intake: Optional[IntakeResult] = None
    structure: Optional[StructureResult] = None
    platform: Optional[PlatformResult] = None
    classification: Optional[ClassificationResult] = None
    schema: Optional[SchemaResult] = None
    quality: Optional[QualityResult] = None
    financial: Optional[FinancialResult] = None
    metrics: Optional[MetricsResult] = None
    readiness: Optional[ReadinessResult] = None
    reconciliation: Optional[ReconciliationResult] = None
    insights: Optional[InsightsResult] = None
    registry: Optional[RegistryResult] = None
    audit: Optional[AuditResult] = None
    learning: Optional[LearningResult] = None

    # Aggregated summary
    summary: Dict[str, Any] = {}
    recommended_actions: List[str] = []
    errors: List[str] = []
