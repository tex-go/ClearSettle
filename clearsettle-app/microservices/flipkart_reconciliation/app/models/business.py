import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReconciliationStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    SHORT_PAID = "SHORT_PAID"
    OVER_PAID = "OVER_PAID"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    MISSING_ORDER = "MISSING_ORDER"
    MISSING_FEE_RECORD = "MISSING_FEE_RECORD"


class OrderFinancials(Base):
    __tablename__ = "order_financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_item_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String(100), index=True)
    sku: Mapped[str | None] = mapped_column(String(200))
    fsn: Mapped[str | None] = mapped_column(String(200))
    product_title: Mapped[str | None] = mapped_column(String(1000))
    order_date: Mapped[date | None] = mapped_column(Date)
    delivery_date: Mapped[date | None] = mapped_column(Date)
    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    marketplace_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    commission_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    other_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    settlement_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    settlement_date: Mapped[date | None] = mapped_column(Date)
    expected_settlement: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    difference: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Stored as VARCHAR(50); ReconciliationStatus used for Python-level type safety
    reconciliation_status: Mapped[str] = mapped_column(String(50), nullable=False)
    last_reconciled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
