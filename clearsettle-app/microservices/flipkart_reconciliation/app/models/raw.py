import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class _RawMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)


class OrdersRaw(_RawMixin, Base):
    __tablename__ = "orders_raw"


class FeesRaw(_RawMixin, Base):
    __tablename__ = "fees_raw"


class SettlementsRaw(_RawMixin, Base):
    __tablename__ = "settlements_raw"
