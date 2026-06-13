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
    RETURN_RECOVERY = "RETURN_RECOVERY"


class OrderFinancials(Base):
    __tablename__ = "order_financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    order_item_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String(100), index=True)
    neft_id: Mapped[str | None] = mapped_column(String(200))
    neft_type: Mapped[str | None] = mapped_column(String(50))

    # Item metadata
    sku: Mapped[str | None] = mapped_column(String(200))
    fsn: Mapped[str | None] = mapped_column(String(200))
    product_title: Mapped[str | None] = mapped_column(String(1000))
    order_date: Mapped[date | None] = mapped_column(Date)
    delivery_date: Mapped[date | None] = mapped_column(Date)
    settlement_date: Mapped[date | None] = mapped_column(Date)

    # Settlement components (from PaymentReports_SettledTransactions)
    sale_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))           # Sale Amount (Rs.)
    total_offer_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))  # Total Offer Amount
    my_share: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))            # Seller-funded discount
    marketplace_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))     # Total MP fee (settlement)
    tcs: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    tds: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    gst_on_mp_fees: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    refund: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    # Invoice components (from Invoices_CommissionInvoiceTransactionDetails)
    invoice_fee_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))   # Sum of fee_amounts
    invoice_gst_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))   # Sum of tax_amounts
    commission_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))       # Commission/Fixed Fee portion
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    other_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    # Reconciliation result
    settlement_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))   # Bank Settlement Value
    expected_settlement: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    difference: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    reconciliation_status: Mapped[str] = mapped_column(String(50), nullable=False)

    last_reconciled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
