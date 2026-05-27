import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


# ── Source constants (which detection pipeline created this event) ─────────────
SOURCE_SETTLEMENT_RUN = "settlement_run"   # reconciliation/engine.py
SOURCE_VENDOR_RUN     = "vendor_run"       # vendor_recon/engine.py
SOURCE_FILE_PARSE     = "file_parse"       # flipkart/amazon/meesho parser
SOURCE_LEAKAGE_AUDIT  = "leakage_audit"    # commission / returns detectors
SOURCE_MANUAL         = "manual"           # user-created via /disputes/ POST

# ── Workflow state machine ────────────────────────────────────────────────────
#   detected → reviewed → filed → acknowledged → resolved
#                       ↘                       ↘ rejected
#                        dismissed
STATE_DETECTED     = "detected"
STATE_REVIEWED     = "reviewed"
STATE_FILED        = "filed"
STATE_ACKNOWLEDGED = "acknowledged"
STATE_RESOLVED     = "resolved"
STATE_REJECTED     = "rejected"
STATE_DISMISSED    = "dismissed"

OPEN_STATES   = {STATE_DETECTED, STATE_REVIEWED, STATE_FILED, STATE_ACKNOWLEDGED}
CLOSED_STATES = {STATE_RESOLVED, STATE_REJECTED, STATE_DISMISSED}


class DiscrepancyEvent(Base):
    """
    One row per individual discrepancy detected across any pipeline.

    source values:
        settlement_run — created by reconciliation/engine.py
        vendor_run     — created by vendor_recon/engine.py
        file_parse     — created during Flipkart/Amazon/Meesho file parsing
        leakage_audit  — created by commission or returns overcharge detection
        manual         — created directly by user via POST /disputes/

    discrepancy_type values:
        MISSING_PAYOUT           — closed settlement with no payout recorded
        PAYOUT_AMOUNT_MISMATCH   — payout amount differs from expected fund transfer
        OVERCHARGE_REFERRAL_FEE  — referral fee rate exceeds configured threshold
        OVERCHARGE_FBA_FEE       — FBA fee per unit exceeds configured threshold
        DUPLICATE_DEDUCTION      — same fee deducted multiple times for one order item
        UNEXPECTED_FEE           — fee type not in the known/allowed list
        PENALTY_MISMATCH         — service fee exceeds expected penalty threshold
        RETURN_OVERCHARGE        — return deduction exceeds expected amount
        COMMISSION_OVERCHARGE    — commission rate charged above published rate

    workflow_state lifecycle:
        detected → reviewed → filed → acknowledged → resolved | rejected
                 ↘ dismissed
    """
    __tablename__ = "discrepancy_events"

    id             = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    # result_id is nullable: leakage_audit and manual events have no reconciliation run parent
    result_id      = Column(PG_UUID(as_uuid=True), ForeignKey("reconciliation_results.id", ondelete="CASCADE"),
                            nullable=True, index=True)
    settlement_id  = Column(PG_UUID(as_uuid=True), ForeignKey("settlements.id", ondelete="CASCADE"),
                            nullable=True, index=True)
    transaction_id = Column(PG_UUID(as_uuid=True), ForeignKey("settlement_transactions.id", ondelete="SET NULL"),
                            nullable=True, index=True)
    company_id     = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    rule_id        = Column(PG_UUID(as_uuid=True), ForeignKey("reconciliation_rules.id", ondelete="SET NULL"),
                            nullable=True)

    platform          = Column(String(50),  nullable=False, default="amazon")
    discrepancy_type  = Column(String(100), nullable=False, index=True)
    severity          = Column(String(20),  nullable=False, index=True)

    # Phase 1: source + workflow_state (migration 029)
    source         = Column(String(30), nullable=False, default=SOURCE_SETTLEMENT_RUN, index=True)
    workflow_state = Column(String(30), nullable=False, default=STATE_DETECTED, index=True)

    expected_amount = Column(Numeric(15, 4))
    actual_amount   = Column(Numeric(15, 4))
    variance_amount = Column(Numeric(15, 4))

    description   = Column(String(500), nullable=False)
    order_id      = Column(String(50),  index=True)
    fee_type      = Column(String(100))
    sku           = Column(String(200))
    metadata_json = Column(Text)

    # Legacy boolean — kept for backward compat; derived from workflow_state
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(PG_UUID(as_uuid=True))

    # Phase 1: filing metadata (migration 029)
    filed_at = Column(DateTime, nullable=True)
    filed_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    result = relationship("ReconciliationResult", back_populates="discrepancies")

    # ── Helpers ────────────────────────────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        return self.workflow_state in OPEN_STATES

    @property
    def is_closed(self) -> bool:
        return self.workflow_state in CLOSED_STATES
