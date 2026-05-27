import uuid

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class ReconciliationResult(Base, TimestampMixin):
    """
    One row per reconciliation engine run for a given settlement.

    Multiple runs are allowed (no unique constraint on settlement_id) to
    preserve an audit trail. The most recent row for a settlement_id is
    the authoritative result.

    status values: clean | warning | critical | error
    """
    __tablename__ = "reconciliation_results"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    settlement_id = Column(PG_UUID(as_uuid=True), ForeignKey("settlements.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    company_id    = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    platform      = Column(String(50), nullable=False, default="amazon")

    status               = Column(String(20), nullable=False, default="clean", index=True)
    total_discrepancies  = Column(Integer,        nullable=False, default=0)
    warning_count        = Column(Integer,        nullable=False, default=0)
    critical_count       = Column(Integer,        nullable=False, default=0)
    info_count           = Column(Integer,        nullable=False, default=0)
    total_variance_amount = Column(Numeric(15, 4), nullable=False, default=0)
    rules_evaluated      = Column(Integer,        nullable=False, default=0)
    processing_time_ms   = Column(Integer)
    error_message        = Column(String(500))
    metadata_json        = Column(Text)

    discrepancies = relationship(
        "DiscrepancyEvent",
        back_populates="result",
        cascade="all, delete-orphan",
        lazy="raise",
    )
