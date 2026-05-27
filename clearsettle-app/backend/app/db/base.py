"""
Declarative base and shared model mixins.

All ORM models import from here to ensure a single metadata registry.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Adds created_at / updated_at to every model."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Adds deleted_at for soft-delete support.

    Queries must filter WHERE deleted_at IS NULL explicitly (or use a
    session-level event / hybrid property).  We intentionally keep this
    opt-in rather than automatic to stay transparent.
    """
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


def new_uuid() -> uuid.UUID:
    """Default factory for UUID primary keys."""
    return uuid.uuid4()
