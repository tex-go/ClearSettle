import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Role(Base):
    __tablename__ = "roles"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    scope       = Column(String(20), nullable=False, default="tenant")
    is_active   = Column(Boolean, nullable=False, default=True)
    is_custom   = Column(Boolean, nullable=False, default=False)
    company_id  = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
                         nullable=True, index=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )


class Permission(Base):
    __tablename__ = "permissions"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), unique=True, nullable=False, index=True)
    module      = Column(String(50), nullable=True)
    action      = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id       = Column(Integer, ForeignKey("roles.id",       ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class UserRole(Base):
    """Maps a user to a role within a specific company (tenant) and optionally a branch."""
    __tablename__ = "user_roles"

    user_id    = Column(PG_UUID(as_uuid=True), ForeignKey("users.id",       ondelete="CASCADE"), primary_key=True)
    role_id    = Column(Integer,               ForeignKey("roles.id",        ondelete="CASCADE"), primary_key=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id",   ondelete="CASCADE"), primary_key=True,
                        nullable=True)
    branch_id  = Column(PG_UUID(as_uuid=True), ForeignKey("branches.id",    ondelete="CASCADE"), nullable=True)
    granted_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id",       ondelete="SET NULL"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("Role", lazy="selectin")


class UserPermission(Base):
    """Direct permission grant/deny for a user, bypassing role hierarchy."""
    __tablename__ = "user_permissions"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(PG_UUID(as_uuid=True), ForeignKey("users.id",       ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer,               ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    company_id    = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id",   ondelete="CASCADE"), nullable=True)
    branch_id     = Column(PG_UUID(as_uuid=True), ForeignKey("branches.id",    ondelete="CASCADE"), nullable=True)
    granted       = Column(Boolean, nullable=False, default=True)
    granted_by    = Column(PG_UUID(as_uuid=True), ForeignKey("users.id",       ondelete="SET NULL"), nullable=True)
    granted_at    = Column(DateTime(timezone=True), server_default=func.now())

    permission = relationship("Permission", lazy="selectin")


class BranchUser(Base):
    """Assigns a user to a branch."""
    __tablename__ = "branch_users"

    branch_id  = Column(PG_UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), primary_key=True)
    user_id    = Column(PG_UUID(as_uuid=True), ForeignKey("users.id",    ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    branch = relationship("Branch", back_populates="branch_users")
