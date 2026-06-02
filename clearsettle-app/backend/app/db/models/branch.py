import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.db.base import Base


class Branch(Base):
    __tablename__ = "branches"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    name       = Column(String(255), nullable=False)
    city       = Column(String(100))
    state      = Column(String(100))
    address    = Column(Text())
    gstin      = Column(String(20))
    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company      = relationship("Company", back_populates="branches")
    branch_users = relationship("BranchUser", back_populates="branch", cascade="all, delete-orphan")
