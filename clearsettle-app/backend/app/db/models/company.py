import uuid

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Company(Base, TimestampMixin, SoftDeleteMixin):
    """
    Seller company — the primary multi-tenant boundary.

    Every PlatformConnection and future financial record belongs to a Company.
    Multiple users can share a company once UserCompany junction is introduced.
    """
    __tablename__ = "companies"

    id       = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id  = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name     = Column(String(255), nullable=False)
    gstin    = Column(String(20))
    city     = Column(String(100))
    industry = Column(String(100))

    # Relationships
    user        = relationship("User",               back_populates="companies")
    connections = relationship("PlatformConnection", back_populates="company", cascade="all, delete-orphan", lazy="selectin")
