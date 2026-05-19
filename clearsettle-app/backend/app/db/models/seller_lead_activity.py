from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.db.base import Base


class SellerLeadActivity(Base):
    """
    Immutable audit log entry for a seller lead.

    activity_type values:
      note | follow_up | call_log | email_log | whatsapp_log
      tag | status_change | classify | score | outreach
    """
    __tablename__ = "seller_lead_activity"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    lead_id       = Column(PG_UUID(as_uuid=True), ForeignKey("seller_leads.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    activity_type = Column(String(50),  nullable=False)
    content       = Column(Text,        nullable=True)
    metadata_json = Column(JSONB,       nullable=True)
    created_by    = Column(String(100), nullable=False)
    created_at    = Column(DateTime,    nullable=False, default=datetime.utcnow)
