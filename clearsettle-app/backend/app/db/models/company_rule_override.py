import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class CompanyRuleOverride(Base, TimestampMixin):
    """
    Company-specific override for a global Rule.

    Any field that is not NULL overrides the parent rule's value.
    parameters_json is merged (shallow) on top of the rule's parameters_json.

    Only one override per (rule_id, company_id) pair is allowed.
    """
    __tablename__ = "company_rule_overrides"
    __table_args__ = (
        UniqueConstraint("rule_id", "company_id", name="uq_cro_rule_company"),
    )

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    rule_id    = Column(PG_UUID(as_uuid=True), ForeignKey("rules.id",    ondelete="CASCADE"),
                        nullable=False, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    is_enabled      = Column(Boolean,    nullable=True)   # None → inherit from rule
    severity        = Column(String(20), nullable=True)   # None → inherit from rule
    priority        = Column(Integer,    nullable=True)   # None → inherit from rule
    parameters_json = Column(Text,       nullable=True)   # None → no merge (use rule's)

    rule = relationship("Rule", back_populates="overrides")
