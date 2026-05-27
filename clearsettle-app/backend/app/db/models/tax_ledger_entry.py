import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class TaxLedgerEntry(Base):
    """
    One row per tax line-item extracted from a settlement.

    entry_type values
    -----------------
    tcs_deducted  — TCS withheld by marketplace (Section 52 CGST Act)
    gst_on_fee    — 18% GST on marketplace fees (IGST; ITC claimable by seller)
    gst_on_sale   — GST on shipment sales (informational; rate varies by HSN)
    gst_on_refund — GST reversal on refunded orders (is_reversal=True)

    supply_type: inter_state → IGST only.  intra_state → equal CGST+SGST split.
    is_reversal: True for refund/credit entries that reduce tax liability.

    Idempotency: all entries for a settlement are deleted and reinserted on
    re-processing, so re-runs produce a clean, consistent ledger.
    """
    __tablename__ = "tax_ledger_entries"
    __table_args__ = (
        Index("ix_tle_company_period", "company_id", "period"),
        Index("ix_tle_settlement",     "settlement_id"),
    )

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    company_id    = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id",  ondelete="CASCADE"),
                           nullable=False, index=True)
    settlement_id = Column(PG_UUID(as_uuid=True), ForeignKey("settlements.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    platform      = Column(String(50), nullable=False, default="amazon")
    period        = Column(String(7),  nullable=False, index=True)   # YYYY-MM
    entry_type    = Column(String(50), nullable=False, index=True)

    # ── Source linkage ────────────────────────────────────────────────────────
    transaction_id = Column(PG_UUID(as_uuid=True),
                            ForeignKey("settlement_transactions.id", ondelete="SET NULL"),
                            nullable=True)
    fee_id         = Column(PG_UUID(as_uuid=True),
                            ForeignKey("fees.id", ondelete="SET NULL"),
                            nullable=True)
    order_id  = Column(String(50))
    fee_type  = Column(String(100))

    # ── Tax computation ───────────────────────────────────────────────────────
    taxable_amount = Column(Numeric(15, 4), nullable=False, default=0)
    tax_rate_pct   = Column(Numeric(6,  4), nullable=False, default=0)   # e.g. 18.0000
    tax_amount     = Column(Numeric(15, 4), nullable=False, default=0)

    igst_amount = Column(Numeric(15, 4), default=0)
    cgst_amount = Column(Numeric(15, 4), default=0)
    sgst_amount = Column(Numeric(15, 4), default=0)
    cess_amount = Column(Numeric(15, 4), default=0)

    # ── Classification ────────────────────────────────────────────────────────
    supply_type = Column(String(20), default="inter_state")
    is_reversal = Column(Boolean,    default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    settlement = relationship("Settlement")
