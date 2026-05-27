import uuid

from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    Application user.

    Roles (stored as plain string, validated at service layer):
        admin    — full access, account owner
        member   — standard team member
        finance  — read-only financial dashboards
        ca       — chartered accountant / external advisor
        viewer   — read-only, no sensitive data

    Multi-tenancy path:
        Currently one user → one company (companies relationship).
        Prepare for many-to-many by keeping user_companies junction table
        in migration 003 (see alembic/versions/003_*).
    """
    __tablename__ = "users"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    email            = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password  = Column(String(255), nullable=False)
    name             = Column(String(255))
    phone            = Column(String(20), index=True)
    role             = Column(String(50), default="admin", nullable=False)
    is_active        = Column(Boolean, default=True, nullable=False)
    email_verified   = Column(Boolean, default=False, nullable=False)

    # Relationships
    companies      = relationship("Company",      back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
