import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base import Base


class MonthlyTaxSummary(Base):
    """
    Aggregated GST/TCS data for one (company, platform, period) bucket.

    period format: YYYY-MM (e.g. "2026-04").

    Rebuilt from scratch whenever process-batch runs for the period — not
    append-only.  is_finalized=True means the month is locked against GSTR-2A
    and should not be recomputed automatically.

    ITC claimable = GST paid on marketplace fees (gst_on_fees).
    TCS credit    = TCS deducted by marketplace (GSTR-2A reconciliation).
    """
    __tablename__ = "monthly_tax_summaries"
    __table_args__ = (
        UniqueConstraint("company_id", "platform", "period",
                         name="uq_mts_company_platform_period"),
    )

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    platform   = Column(String(50), nullable=False, default="amazon")
    period     = Column(String(7),  nullable=False)   # YYYY-MM

    # ── Sales summary ─────────────────────────────────────────────────────────
    gross_sales   = Column(Numeric(15, 4), default=0)
    refund_amount = Column(Numeric(15, 4), default=0)
    net_sales     = Column(Numeric(15, 4), default=0)   # gross_sales - refund_amount

    # ── TCS (Tax Collected at Source — deducted by marketplace) ───────────────
    tcs_deducted  = Column(Numeric(15, 4), default=0)
    tcs_igst      = Column(Numeric(15, 4), default=0)
    tcs_cgst      = Column(Numeric(15, 4), default=0)
    tcs_sgst      = Column(Numeric(15, 4), default=0)

    # ── GST on marketplace fees (Input Tax Credit) ────────────────────────────
    total_fees    = Column(Numeric(15, 4), default=0)   # absolute fee base
    gst_on_fees   = Column(Numeric(15, 4), default=0)   # 18% IGST component
    igst_on_fees  = Column(Numeric(15, 4), default=0)
    cgst_on_fees  = Column(Numeric(15, 4), default=0)
    sgst_on_fees  = Column(Numeric(15, 4), default=0)

    # ── Refund GST reversals ──────────────────────────────────────────────────
    gst_on_refunds = Column(Numeric(15, 4), default=0)

    # ── Processing metadata ───────────────────────────────────────────────────
    settlements_processed = Column(Integer, default=0)
    transactions_count    = Column(Integer, default=0)
    fees_count            = Column(Integer, default=0)

    # ── Derived totals ────────────────────────────────────────────────────────
    net_tcs_credit = Column(Numeric(15, 4), default=0)   # TCS credit claim
    itc_claimable  = Column(Numeric(15, 4), default=0)   # GST ITC on fees

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    is_finalized = Column(Boolean,  default=False, nullable=False)
    finalized_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
