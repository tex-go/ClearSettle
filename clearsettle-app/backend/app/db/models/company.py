import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
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

    # Extended seller profile (added in migration 021)
    phone                = Column(String(20))
    pan                  = Column(String(15))
    state                = Column(String(100))
    state_code           = Column(String(5))
    pincode              = Column(String(10))
    address              = Column(Text)
    website              = Column(String(255))
    active_platforms     = Column(JSONB, default=list)
    bank_name            = Column(String(100))
    bank_account_number  = Column(String(50))
    bank_ifsc            = Column(String(20))
    bank_account_name    = Column(String(255))
    monthly_gmv_range    = Column(String(50))
    registration_completed = Column(Boolean, default=False)

    # Relationships
    user        = relationship("User",               back_populates="companies")
    connections = relationship("PlatformConnection", back_populates="company", cascade="all, delete-orphan", lazy="selectin")
    # Marketplace Integration Framework connections
    mkt_connections = relationship(
        "MarketplaceConnection",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="raise",
        foreign_keys="[MarketplaceConnection.company_id]",
    )
