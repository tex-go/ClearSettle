import uuid

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class RuleCondition(Base):
    """
    One condition expression within a Rule.

    field:      key in the evaluation context dict (e.g. 'fee_rate_pct', 'payout_amount')
    operator:   gt | lt | gte | lte | eq | neq | contains | in | not_in | exists
    value:      string representation of the comparison value
    value_type: number | string | boolean | list
                — controls how 'value' is cast before comparison
    """
    __tablename__ = "rule_conditions"

    id      = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    rule_id = Column(PG_UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    field       = Column(String(100), nullable=False)
    operator    = Column(String(20),  nullable=False)
    value       = Column(String(500), nullable=False)
    value_type  = Column(String(20),  nullable=False, default="number")
    description = Column(String(200))

    rule = relationship("Rule", back_populates="conditions")
