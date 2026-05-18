import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class RuleAction(Base):
    """
    An action that fires when the parent Rule's conditions are satisfied.

    action_type: create_discrepancy | create_alert | auto_dispute |
                 recommend_recovery | send_notification | escalate_case
    action_order: execution sequence (lower = first)
    parameters_json: action-specific config (e.g. alert_channel, template_id)
    """
    __tablename__ = "rule_actions"

    id      = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    rule_id = Column(PG_UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    action_type     = Column(String(100), nullable=False, index=True)
    action_order    = Column(Integer,     nullable=False, default=1)
    parameters_json = Column(Text,        default="{}")
    is_enabled      = Column(Boolean,     nullable=False, default=True)

    rule = relationship("Rule", back_populates="actions")
