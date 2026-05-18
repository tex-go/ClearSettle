import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base import Base


class RuleExecutionLog(Base):
    """
    Audit log for a single rule evaluation attempt.

    One row per (rule × context) evaluation — dry-run and real runs both recorded.
    context_json stores the input context dict so past evaluations can be replayed.
    """
    __tablename__ = "rule_execution_logs"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    rule_id    = Column(PG_UUID(as_uuid=True), ForeignKey("rules.id",    ondelete="CASCADE"),
                        nullable=False, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    settlement_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    context_json  = Column(Text)           # input evaluation context

    matched          = Column(Boolean, nullable=False, default=False)
    actions_executed = Column(Integer, nullable=False, default=0)
    duration_ms      = Column(Integer)
    error_message    = Column(String(500))

    is_dry_run   = Column(Boolean,    nullable=False, default=False)
    triggered_by = Column(String(50), nullable=False, default="manual")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
