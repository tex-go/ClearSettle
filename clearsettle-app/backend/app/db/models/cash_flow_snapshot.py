import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from app.db.base import Base


class CashFlowSnapshot(Base):
    __tablename__ = "cash_flow_snapshots"
    __table_args__ = (
        UniqueConstraint("company_id", "snapshot_date", "period_type",
                         name="uq_cfs_company_date_type"),
    )

    id           = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id   = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                          nullable=False, index=True)

    snapshot_date = Column(Date,       nullable=False)
    period_type   = Column(String(20), nullable=False)   # daily/weekly/monthly/quarterly

    opening_balance   = Column(Numeric(18, 4), nullable=False, default=0)
    inflows           = Column(Numeric(18, 4), nullable=False, default=0)
    outflows          = Column(Numeric(18, 4), nullable=False, default=0)
    net_cash_flow     = Column(Numeric(18, 4), nullable=False, default=0)
    closing_balance   = Column(Numeric(18, 4), nullable=False, default=0)
    settlements_count = Column(Integer,        nullable=False, default=0)
    fees_total        = Column(Numeric(18, 4), nullable=False, default=0)

    platform_breakdown_json = Column(JSONB, nullable=True)
    currency                = Column(String(10), nullable=False, default="INR")

    ai_insights_json  = Column(JSONB,      nullable=True)
    ai_shortage_risk  = Column(String(20), nullable=True)   # low/medium/high/critical
    ai_generated_at   = Column(DateTime,   nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
