import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Fee(Base):
    """
    One row per fee line-item within a settlement transaction.

    Common Amazon fee_type values
    ------------------------------
    ReferralFee, FBAPerUnitFulfillmentFee, FBAWeightBasedFee,
    VariableClosingFee, PerItemFee, Commission, Shipping

    settlement_id is denormalised from transaction → settlement to allow
    direct settlement → fees queries without joining settlement_transactions.

    amount is typically negative (fees are deducted from seller proceeds).
    """
    __tablename__ = "fees"

    id             = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    transaction_id = Column(PG_UUID(as_uuid=True),
                            ForeignKey("settlement_transactions.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    settlement_id  = Column(PG_UUID(as_uuid=True),
                            ForeignKey("settlements.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    company_id     = Column(PG_UUID(as_uuid=True),
                            ForeignKey("companies.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    platform       = Column(String(50), nullable=False, default="amazon")

    fee_type        = Column(String(100), nullable=False)
    fee_description = Column(String(255))
    currency        = Column(String(10),     nullable=False, default="INR")
    amount          = Column(Numeric(15, 4), nullable=False)   # negative for deductions

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    transaction = relationship("SettlementTransaction", back_populates="fees")
    settlement  = relationship("Settlement",            back_populates="fees")
