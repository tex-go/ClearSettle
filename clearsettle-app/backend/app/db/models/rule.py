import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Rule(Base, TimestampMixin):
    """
    Generic, configurable rule that can be evaluated against any context dict.

    Global rules (company_id IS NULL) apply to all companies.
    Company rules apply only to that company.

    condition_logic: 'all' — all conditions must match; 'any' — at least one must match.
    category:  fees | payout | tax | returns | risk | custom
    rule_type: commission_overcharge | missing_payout | duplicate_deduction | tcs_mismatch |
               penalty_overcharge | high_return_rate | payout_delay | gst_discrepancy | custom
    severity:  info | warning | critical
    priority:  lower number = evaluated first
    """
    __tablename__ = "rules"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=True, index=True)   # NULL → global rule

    name            = Column(String(255), nullable=False)
    description     = Column(String(1000))
    category        = Column(String(100), nullable=False, index=True)
    rule_type       = Column(String(100), nullable=False, index=True)
    severity        = Column(String(20),  nullable=False, default="warning")
    priority        = Column(Integer,     nullable=False, default=100)
    platform        = Column(String(50),  nullable=True)   # NULL → all platforms
    is_enabled      = Column(Boolean,     nullable=False, default=True)
    condition_logic = Column(String(10),  nullable=False, default="all")   # all | any

    parameters_json        = Column(Text, default="{}")
    recovery_metadata_json = Column(Text, default="{}")

    # Playbook / legal context (added in migration 012)
    verdict          = Column(String(50),    nullable=True)
    legal_basis      = Column(Text,          nullable=True)
    evidence_json    = Column(Text,          default="[]")
    dispute_window   = Column(String(100),   nullable=True)
    success_rate_pct = Column(Numeric(5, 1), nullable=True)
    recovery_min     = Column(Numeric(12, 2), nullable=True)
    recovery_max     = Column(Numeric(12, 2), nullable=True)
    auto_raise       = Column(Boolean,       nullable=False, default=False)
    playbook_notes   = Column(Text,          nullable=True)

    conditions = relationship(
        "RuleCondition", back_populates="rule",
        cascade="all, delete-orphan", lazy="raise",
    )
    actions = relationship(
        "RuleAction", back_populates="rule",
        cascade="all, delete-orphan", lazy="raise",
        order_by="RuleAction.action_order",
    )
    overrides = relationship(
        "CompanyRuleOverride", back_populates="rule",
        cascade="all, delete-orphan", lazy="raise",
    )
