import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class PayoutEvent(Base, TimestampMixin):
    """
    One row per fund transfer from marketplace to seller's bank account.

    Amazon creates one payout per closed FinancialEventGroup.
    status values: pending | transferred | failed

    UNIQUE on settlement_id: one payout per settlement.
    """
    __tablename__ = "payout_events"
    __table_args__ = (
        UniqueConstraint("settlement_id", name="uq_payout_settlement"),
    )

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    settlement_id = Column(PG_UUID(as_uuid=True), ForeignKey("settlements.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    company_id    = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    connection_id = Column(PG_UUID(as_uuid=True), ForeignKey("platform_connections.id", ondelete="SET NULL"),
                           nullable=True)

    platform     = Column(String(50),  nullable=False, default="amazon")
    external_id  = Column(String(255))   # platform-provided transfer reference (if available)
    status       = Column(String(50),  nullable=False, default="pending", index=True)
    # pending | transferred | failed

    currency      = Column(String(10),     nullable=False, default="INR")
    amount        = Column(Numeric(15, 4), nullable=False)
    transfer_date = Column(DateTime)
    account_tail  = Column(String(10))   # last 4 digits of bank account

    # ── Relationships ─────────────────────────────────────────────────────────
    settlement = relationship("Settlement", back_populates="payout")
