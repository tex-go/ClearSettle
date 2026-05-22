"""ORM models for Flipkart P&L Report ingestion (migration 020)."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class FlipkartReport(Base):
    __tablename__ = "flipkart_reports"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id       = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    filename         = Column(String(255), nullable=False)
    original_name    = Column(String(255), nullable=False)
    file_size_bytes  = Column(Integer,     nullable=True)
    status           = Column(String(20),  nullable=False, default="pending")
    error_message    = Column(Text,        nullable=True)
    report_period    = Column(String(100), nullable=True)
    sheets_parsed    = Column(String(500), nullable=True)
    row_count_summary= Column(Integer,     nullable=True)
    row_count_sku    = Column(Integer,     nullable=True)
    row_count_orders = Column(Integer,     nullable=True)
    uploaded_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)
    processed_at     = Column(DateTime,    nullable=True)

    summary      = relationship("FlipkartSummary",    back_populates="report", uselist=False, cascade="all, delete-orphan")
    sku_rows     = relationship("FlipkartSkuPL",      back_populates="report", cascade="all, delete-orphan")
    order_rows   = relationship("FlipkartOrderPL",    back_populates="report", cascade="all, delete-orphan")
    recon_issues = relationship("FlipkartReconIssue", back_populates="report", cascade="all, delete-orphan")


class FlipkartSummary(Base):
    __tablename__ = "flipkart_summaries"

    id                     = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id              = Column(PG_UUID(as_uuid=True), ForeignKey("flipkart_reports.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_id             = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Revenue
    gross_sales            = Column(Numeric(18, 2), nullable=True)
    returns                = Column(Numeric(18, 2), nullable=True)
    cancellations          = Column(Numeric(18, 2), nullable=True)
    net_sales              = Column(Numeric(18, 2), nullable=True)

    # Fees & Deductions
    commission             = Column(Numeric(18, 2), nullable=True)
    shipping_charges       = Column(Numeric(18, 2), nullable=True)
    reverse_shipping       = Column(Numeric(18, 2), nullable=True)
    collection_fees        = Column(Numeric(18, 2), nullable=True)
    fixed_fees             = Column(Numeric(18, 2), nullable=True)
    gst_on_fees            = Column(Numeric(18, 2), nullable=True)
    tcs                    = Column(Numeric(18, 2), nullable=True)
    tds                    = Column(Numeric(18, 2), nullable=True)
    other_fees             = Column(Numeric(18, 2), nullable=True)
    total_fees             = Column(Numeric(18, 2), nullable=True)

    # Earnings & Settlement
    net_earnings           = Column(Numeric(18, 2), nullable=True)
    amount_settled         = Column(Numeric(18, 2), nullable=True)
    amount_pending         = Column(Numeric(18, 2), nullable=True)

    # Volume KPIs
    total_orders           = Column(Integer,       nullable=True)
    total_returned_orders  = Column(Integer,       nullable=True)
    total_cancelled_orders = Column(Integer,       nullable=True)

    # Rate KPIs
    return_rate_pct        = Column(Numeric(6, 3), nullable=True)
    cancellation_rate_pct  = Column(Numeric(6, 3), nullable=True)
    profit_margin_pct      = Column(Numeric(8, 4), nullable=True)

    report = relationship("FlipkartReport", back_populates="summary")


class FlipkartSkuPL(Base):
    __tablename__ = "flipkart_sku_pl"

    id                    = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id             = Column(PG_UUID(as_uuid=True), ForeignKey("flipkart_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id            = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    sku_code              = Column(String(200), nullable=True, index=True)
    product_title         = Column(String(500), nullable=True)
    category              = Column(String(200), nullable=True)
    selling_price         = Column(Numeric(14, 2), nullable=True)
    mrp                   = Column(Numeric(14, 2), nullable=True)

    total_orders          = Column(Integer,        nullable=True)
    qty_sold              = Column(Numeric(12, 3), nullable=True)
    gross_sales           = Column(Numeric(18, 2), nullable=True)

    returns_qty           = Column(Numeric(12, 3), nullable=True)
    returns_value         = Column(Numeric(18, 2), nullable=True)
    cancellations_qty     = Column(Numeric(12, 3), nullable=True)
    cancellations_value   = Column(Numeric(18, 2), nullable=True)
    net_sales             = Column(Numeric(18, 2), nullable=True)

    commission            = Column(Numeric(18, 2), nullable=True)
    shipping_charges      = Column(Numeric(18, 2), nullable=True)
    reverse_shipping      = Column(Numeric(18, 2), nullable=True)
    other_fees            = Column(Numeric(18, 2), nullable=True)
    total_fees            = Column(Numeric(18, 2), nullable=True)
    net_earnings          = Column(Numeric(18, 2), nullable=True)
    margin_pct            = Column(Numeric(8, 4),  nullable=True)

    return_rate_pct       = Column(Numeric(6, 3),  nullable=True)
    cancellation_rate_pct = Column(Numeric(6, 3),  nullable=True)
    is_loss_making        = Column(Boolean,         nullable=False, default=False)
    high_return_rate      = Column(Boolean,         nullable=False, default=False)

    report = relationship("FlipkartReport", back_populates="sku_rows")


class FlipkartOrderPL(Base):
    __tablename__ = "flipkart_orders_pl"

    id                  = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id           = Column(PG_UUID(as_uuid=True), ForeignKey("flipkart_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id          = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    order_id            = Column(String(100), nullable=True, index=True)
    order_date          = Column(Date,        nullable=True)
    sku_code            = Column(String(200), nullable=True, index=True)
    product_title       = Column(String(500), nullable=True)
    category            = Column(String(200), nullable=True)
    selling_price       = Column(Numeric(14, 2), nullable=True)
    quantity            = Column(Numeric(12, 3), nullable=True)

    gross_amount        = Column(Numeric(18, 2), nullable=True)
    commission          = Column(Numeric(18, 2), nullable=True)
    shipping_charges    = Column(Numeric(18, 2), nullable=True)
    reverse_shipping    = Column(Numeric(18, 2), nullable=True)
    other_fees          = Column(Numeric(18, 2), nullable=True)
    net_earnings        = Column(Numeric(18, 2), nullable=True)

    status              = Column(String(50),  nullable=True)
    settlement_status   = Column(String(50),  nullable=True)
    settlement_amount   = Column(Numeric(18, 2), nullable=True)
    settlement_date     = Column(Date,           nullable=True)
    expected_settlement = Column(Numeric(18, 2), nullable=True)
    settlement_variance = Column(Numeric(18, 2), nullable=True)

    report = relationship("FlipkartReport", back_populates="order_rows")


class FlipkartReconIssue(Base):
    __tablename__ = "flipkart_recon_issues"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id       = Column(PG_UUID(as_uuid=True), ForeignKey("flipkart_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id      = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    issue_type      = Column(String(50),  nullable=False, index=True)
    severity        = Column(String(20),  nullable=False)
    order_id        = Column(String(100), nullable=True)
    sku_code        = Column(String(200), nullable=True)
    expected_amount = Column(Numeric(18, 2), nullable=True)
    actual_amount   = Column(Numeric(18, 2), nullable=True)
    variance        = Column(Numeric(18, 2), nullable=True)
    description     = Column(Text,        nullable=False)
    status          = Column(String(20),  nullable=False, default="open")
    created_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)

    report = relationship("FlipkartReport", back_populates="recon_issues")
