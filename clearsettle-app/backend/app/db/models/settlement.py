import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Settlement(Base, TimestampMixin):
    """
    One row per marketplace settlement period.

    external_id is the platform's identifier:
      Amazon  → FinancialEventGroupId
      Future  → platform-specific ID

    Unique constraint (company_id, platform, external_id) prevents duplicate ingestion.
    raw_data_json stores the full API response for auditability and replay.
    """
    __tablename__ = "settlements"
    __table_args__ = (
        UniqueConstraint("company_id", "platform", "external_id",
                         name="uq_settlement_company_platform_ext"),
    )

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    company_id    = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    connection_id = Column(PG_UUID(as_uuid=True), ForeignKey("platform_connections.id", ondelete="SET NULL"),
                           nullable=True)

    platform    = Column(String(50),  nullable=False, default="amazon", index=True)
    external_id = Column(String(255), nullable=False)
    status      = Column(String(50),  nullable=False, default="processing", index=True)
    # processing | open | closed

    # ── Financial summary ─────────────────────────────────────────────────────
    currency             = Column(String(10),     nullable=False, default="INR")
    total_amount         = Column(Numeric(15, 4), nullable=False, default=0)   # OriginalTotal
    converted_amount     = Column(Numeric(15, 4))                              # ConvertedTotal
    fund_transfer_amount = Column(Numeric(15, 4))                              # FundTransferAmount
    beginning_balance    = Column(Numeric(15, 4))

    # Computed summaries (updated after transactions are stored)
    transactions_count = Column(Integer, default=0)
    fees_total         = Column(Numeric(15, 4), default=0)

    # ── Period ────────────────────────────────────────────────────────────────
    period_start       = Column(DateTime)
    period_end         = Column(DateTime)
    fund_transfer_date = Column(DateTime)
    account_tail       = Column(String(10))   # last 4 digits of bank account

    # ── Raw data ──────────────────────────────────────────────────────────────
    raw_data_json = Column(Text)   # full API group response

    # ── Relationships ─────────────────────────────────────────────────────────
    transactions = relationship(
        "SettlementTransaction",
        back_populates="settlement",
        cascade="all, delete-orphan",
        lazy="raise",       # use explicit selectinload when needed
    )
    fees = relationship(
        "Fee",
        back_populates="settlement",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    payout = relationship(
        "PayoutEvent",
        back_populates="settlement",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="raise",
    )
