"""ORM models for Amazon Settlement Report ingestion."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AmazonReport(Base):
    __tablename__ = "amazon_reports"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id       = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    filename         = Column(String(255), nullable=False)
    original_name    = Column(String(255), nullable=False)
    file_size_bytes  = Column(Integer,     nullable=True)
    file_hash        = Column(String(64),  nullable=True, index=True)
    report_type      = Column(String(30),  nullable=False, default="settlement_report")
    status           = Column(String(50),  nullable=False, default="pending")
    error_message    = Column(Text,        nullable=True)
    # Settlement-specific metadata
    settlement_id         = Column(String(100), nullable=True)
    settlement_start_date = Column(Date,        nullable=True)
    settlement_end_date   = Column(Date,        nullable=True)
    deposit_date          = Column(Date,        nullable=True)
    currency              = Column(String(10),  nullable=True, default="INR")
    total_deposit_amount  = Column(Numeric(18, 2), nullable=True)
    row_count             = Column(Integer,     nullable=True)
    uploaded_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at     = Column(DateTime, nullable=True)

    summary      = relationship("AmazonSummary",    back_populates="report", uselist=False, cascade="all, delete-orphan")
    order_rows   = relationship("AmazonOrderRow",   back_populates="report", cascade="all, delete-orphan")
    recon_issues = relationship("AmazonReconIssue", back_populates="report", cascade="all, delete-orphan")


class AmazonSummary(Base):
    __tablename__ = "amazon_summaries"

    id           = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id    = Column(PG_UUID(as_uuid=True), ForeignKey("amazon_reports.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_id   = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    gross_sales          = Column(Numeric(18, 2), nullable=True)
    refunds              = Column(Numeric(18, 2), nullable=True)
    promotions           = Column(Numeric(18, 2), nullable=True)
    net_sales            = Column(Numeric(18, 2), nullable=True)

    commission           = Column(Numeric(18, 2), nullable=True)
    fba_fees             = Column(Numeric(18, 2), nullable=True)
    shipping_fees        = Column(Numeric(18, 2), nullable=True)
    other_fees           = Column(Numeric(18, 2), nullable=True)
    withheld_tax         = Column(Numeric(18, 2), nullable=True)
    total_fees           = Column(Numeric(18, 2), nullable=True)

    net_earnings         = Column(Numeric(18, 2), nullable=True)
    amount_deposited     = Column(Numeric(18, 2), nullable=True)
    settlement_variance  = Column(Numeric(18, 2), nullable=True)

    total_orders         = Column(Integer, nullable=True)
    total_refunded_orders= Column(Integer, nullable=True)
    total_units          = Column(Integer, nullable=True)

    effective_commission_rate_pct = Column(Numeric(6, 3), nullable=True)
    return_rate_pct               = Column(Numeric(6, 3), nullable=True)
    fee_rate_pct                  = Column(Numeric(6, 3), nullable=True)

    report = relationship("AmazonReport", back_populates="summary")


class AmazonOrderRow(Base):
    __tablename__ = "amazon_order_rows"

    id                    = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id             = Column(PG_UUID(as_uuid=True), ForeignKey("amazon_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id            = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    order_id              = Column(String(100), nullable=True, index=True)
    merchant_order_id     = Column(String(100), nullable=True)
    order_date            = Column(Date,        nullable=True)
    shipment_date         = Column(Date,        nullable=True)
    posted_date           = Column(Date,        nullable=True)
    sku                   = Column(String(200), nullable=True, index=True)
    product_name          = Column(String(500), nullable=True)
    quantity              = Column(Integer,     nullable=True)
    transaction_type      = Column(String(50),  nullable=True)   # Order / Refund / Adjustment

    gross_amount          = Column(Numeric(18, 2), nullable=True)
    commission            = Column(Numeric(18, 2), nullable=True)
    fba_fee               = Column(Numeric(18, 2), nullable=True)
    shipping_fee          = Column(Numeric(18, 2), nullable=True)
    other_fees            = Column(Numeric(18, 2), nullable=True)
    withheld_tax          = Column(Numeric(18, 2), nullable=True)
    promotions            = Column(Numeric(18, 2), nullable=True)
    net_amount            = Column(Numeric(18, 2), nullable=True)
    expected_net          = Column(Numeric(18, 2), nullable=True)
    settlement_variance   = Column(Numeric(18, 2), nullable=True)

    report = relationship("AmazonReport", back_populates="order_rows")


class AmazonReconIssue(Base):
    __tablename__ = "amazon_recon_issues"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id       = Column(PG_UUID(as_uuid=True), ForeignKey("amazon_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id      = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    issue_type      = Column(String(60),  nullable=False, index=True)
    severity        = Column(String(20),  nullable=False)
    order_id        = Column(String(100), nullable=True)
    sku             = Column(String(200), nullable=True)
    expected_amount = Column(Numeric(18, 2), nullable=True)
    actual_amount   = Column(Numeric(18, 2), nullable=True)
    variance        = Column(Numeric(18, 2), nullable=True)
    description     = Column(Text,        nullable=False)
    status          = Column(String(20),  nullable=False, default="open")
    created_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)

    report = relationship("AmazonReport", back_populates="recon_issues")
