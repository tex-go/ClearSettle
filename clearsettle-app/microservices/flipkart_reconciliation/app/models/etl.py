import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrdersEtl(Base):
    __tablename__ = "orders_etl"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    raw_id: Mapped[int] = mapped_column(Integer, nullable=False)
    order_item_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String(100))
    sku: Mapped[str | None] = mapped_column(String(200))
    fsn: Mapped[str | None] = mapped_column(String(200))
    product_title: Mapped[str | None] = mapped_column(String(1000))
    quantity: Mapped[int | None] = mapped_column(Integer)
    order_date: Mapped[date | None] = mapped_column(Date)
    dispatch_date: Mapped[date | None] = mapped_column(Date)
    delivery_date: Mapped[date | None] = mapped_column(Date)
    order_item_status: Mapped[str | None] = mapped_column(String(100))
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeesEtl(Base):
    __tablename__ = "fees_etl"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    raw_id: Mapped[int] = mapped_column(Integer, nullable=False)
    order_item_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    fee_name: Mapped[str | None] = mapped_column(String(200))
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    fee_waiver_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sgst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    igst: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    fee_date: Mapped[date | None] = mapped_column(Date)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SettlementsEtl(Base):
    __tablename__ = "settlements_etl"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    raw_id: Mapped[int] = mapped_column(Integer, nullable=False)
    neft_id: Mapped[str | None] = mapped_column(String(200))
    settlement_date: Mapped[date | None] = mapped_column(Date)
    settlement_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    order_id: Mapped[str | None] = mapped_column(String(100))
    order_item_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    marketplace_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    taxes: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    offer_adjustments: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    shipping_charges: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    sku: Mapped[str | None] = mapped_column(String(200))
    fsn: Mapped[str | None] = mapped_column(String(200))
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
