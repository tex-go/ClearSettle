import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DiscrepancyEvent(Base):
    """
    One row per individual discrepancy found during a reconciliation run.

    discrepancy_type values (defined in services/reconciliation/detectors.py):
        MISSING_PAYOUT           — closed settlement with no payout recorded
        PAYOUT_AMOUNT_MISMATCH   — payout amount differs from expected fund transfer
        OVERCHARGE_REFERRAL_FEE  — referral fee rate exceeds configured threshold
        OVERCHARGE_FBA_FEE       — FBA fee per unit exceeds configured threshold
        DUPLICATE_DEDUCTION      — same fee deducted multiple times for one order item
        UNEXPECTED_FEE           — fee type not in the known/allowed list
        PENALTY_MISMATCH         — service fee exceeds expected penalty threshold

    is_resolved / resolved_at / resolved_by track manual review workflow.
    """
    __tablename__ = "discrepancy_events"

    id             = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    result_id      = Column(PG_UUID(as_uuid=True), ForeignKey("reconciliation_results.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    settlement_id  = Column(PG_UUID(as_uuid=True), ForeignKey("settlements.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    transaction_id = Column(PG_UUID(as_uuid=True), ForeignKey("settlement_transactions.id", ondelete="SET NULL"),
                            nullable=True, index=True)
    company_id     = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    rule_id        = Column(PG_UUID(as_uuid=True), ForeignKey("reconciliation_rules.id", ondelete="SET NULL"),
                            nullable=True)

    platform          = Column(String(50),  nullable=False, default="amazon")
    discrepancy_type  = Column(String(100), nullable=False, index=True)
    severity          = Column(String(20),  nullable=False, index=True)

    expected_amount = Column(Numeric(15, 4))
    actual_amount   = Column(Numeric(15, 4))
    variance_amount = Column(Numeric(15, 4))

    description   = Column(String(500), nullable=False)
    order_id      = Column(String(50),  index=True)
    fee_type      = Column(String(100))
    metadata_json = Column(Text)

    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(PG_UUID(as_uuid=True))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    result = relationship("ReconciliationResult", back_populates="discrepancies")
