import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SettlementTransaction(Base):
    """
    One row per individual financial event within a settlement.

    transaction_type values
    -----------------------
    shipment        → ShipmentEventList item
    refund          → RefundEventList item
    service_fee     → ServiceFeeEventList item
    adjustment      → AdjustmentEventList item
    guarantee_claim → GuaranteeClaimEventList item
    ads_payment     → ProductAdsPaymentEventList item
    other           → any other event type

    source_hash
    -----------
    SHA-256 of (platform|transaction_type|settlement_external_id|order_id|order_item_id).
    Unique across the table — used as the ON CONFLICT key for upserts.
    """
    __tablename__ = "settlement_transactions"
    __table_args__ = (
        UniqueConstraint("source_hash", name="uq_stxn_source_hash"),
        Index("ix_stxn_settlement_order", "settlement_id", "order_id"),
    )

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    settlement_id = Column(PG_UUID(as_uuid=True), ForeignKey("settlements.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    company_id    = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    platform      = Column(String(50), nullable=False, default="amazon")

    # ── Dedup key ─────────────────────────────────────────────────────────────
    source_hash = Column(String(64), nullable=False)

    # ── Classification ────────────────────────────────────────────────────────
    transaction_type = Column(String(50), nullable=False, index=True)

    # ── Order context ─────────────────────────────────────────────────────────
    order_id      = Column(String(50),  index=True)
    order_item_id = Column(String(255))
    sku           = Column(String(255))
    marketplace   = Column(String(100))
    posted_date   = Column(DateTime,    index=True)
    quantity      = Column(Integer, default=1)

    # ── Amounts ───────────────────────────────────────────────────────────────
    currency         = Column(String(10),     nullable=False, default="INR")
    principal_amount = Column(Numeric(15, 4), default=0)
    shipping_amount  = Column(Numeric(15, 4), default=0)
    gift_wrap_amount = Column(Numeric(15, 4), default=0)
    promotion_amount = Column(Numeric(15, 4), default=0)
    total_amount     = Column(Numeric(15, 4), default=0)  # sum of charges
    fees_total       = Column(Numeric(15, 4), default=0)  # sum of fees (usually negative)
    net_amount       = Column(Numeric(15, 4), default=0)  # total_amount + fees_total

    # ── Raw data ──────────────────────────────────────────────────────────────
    raw_data_json = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    settlement = relationship("Settlement", back_populates="transactions")
    fees       = relationship(
        "Fee",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="raise",
    )
