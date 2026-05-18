import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base import Base, TimestampMixin


class ReconciliationRule(Base, TimestampMixin):
    """
    Defines a single detection rule for the reconciliation engine.

    Global rules (company_id IS NULL) apply to all companies.
    Company-specific rules apply only to that company and can augment global rules.

    rule_type must match a key in DETECTOR_REGISTRY (services/reconciliation/engine.py).
    parameters_json holds rule-specific thresholds as a JSON object.

    severity values: info | warning | critical
    """
    __tablename__ = "reconciliation_rules"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=True, index=True)   # NULL → global rule
    platform   = Column(String(50), nullable=True)   # NULL → all platforms

    rule_type       = Column(String(100), nullable=False, index=True)
    rule_name       = Column(String(255), nullable=False)
    description     = Column(String(500))
    parameters_json = Column(Text, default="{}")
    severity        = Column(String(20), nullable=False, default="warning")
    is_active       = Column(Boolean, nullable=False, default=True)
