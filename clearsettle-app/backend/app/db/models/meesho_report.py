"""ORM models for Meesho Payment Report ingestion."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MeeshoReport(Base):
    __tablename__ = "meesho_reports"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id       = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    filename         = Column(String(255), nullable=False)
    original_name    = Column(String(255), nullable=False)
    file_size_bytes  = Column(Integer,     nullable=True)
    file_hash        = Column(String(64),  nullable=True, index=True)
    report_type      = Column(String(30),  nullable=False, default="payment_report")
    status           = Column(String(50),  nullable=False, default="pending")
    error_message    = Column(Text,        nullable=True)
    report_period    = Column(String(100), nullable=True)
    row_count        = Column(Integer,     nullable=True)
    uploaded_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)
    processed_at     = Column(DateTime,    nullable=True)

    summary      = relationship("MeeshoSummary",    back_populates="report", uselist=False, cascade="all, delete-orphan")
    order_rows   = relationship("MeeshoOrderRow",   back_populates="report", cascade="all, delete-orphan")
    recon_issues = relationship("MeeshoReconIssue", back_populates="report", cascade="all, delete-orphan")


class MeeshoSummary(Base):
    __tablename__ = "meesho_summaries"

    id           = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id    = Column(PG_UUID(as_uuid=True), ForeignKey("meesho_reports.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_id   = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    gross_sales          = Column(Numeric(18, 2), nullable=True)
    customer_paid_total  = Column(Numeric(18, 2), nullable=True)
    returns_value        = Column(Numeric(18, 2), nullable=True)
    cancellations_value  = Column(Numeric(18, 2), nullable=True)
    net_sales            = Column(Numeric(18, 2), nullable=True)

    commission           = Column(Numeric(18, 2), nullable=True)
    shipping_charges     = Column(Numeric(18, 2), nullable=True)
    reverse_shipping     = Column(Numeric(18, 2), nullable=True)
    gst_on_commission    = Column(Numeric(18, 2), nullable=True)
    tcs                  = Column(Numeric(18, 2), nullable=True)
    other_deductions     = Column(Numeric(18, 2), nullable=True)
    total_deductions     = Column(Numeric(18, 2), nullable=True)

    net_earnings         = Column(Numeric(18, 2), nullable=True)
    amount_paid          = Column(Numeric(18, 2), nullable=True)
    amount_pending       = Column(Numeric(18, 2), nullable=True)

    total_orders         = Column(Integer, nullable=True)
    delivered_orders     = Column(Integer, nullable=True)
    returned_orders      = Column(Integer, nullable=True)
    cancelled_orders     = Column(Integer, nullable=True)
    pending_orders       = Column(Integer, nullable=True)

    return_rate_pct         = Column(Numeric(6, 3), nullable=True)
    cancellation_rate_pct   = Column(Numeric(6, 3), nullable=True)
    effective_commission_pct = Column(Numeric(6, 3), nullable=True)

    report = relationship("MeeshoReport", back_populates="summary")


class MeeshoOrderRow(Base):
    __tablename__ = "meesho_order_rows"

    id                  = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id           = Column(PG_UUID(as_uuid=True), ForeignKey("meesho_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id          = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    order_id            = Column(String(100), nullable=True, index=True)
    sub_order_id        = Column(String(100), nullable=True)
    order_date          = Column(Date,        nullable=True)
    payment_date        = Column(Date,        nullable=True)
    product_name        = Column(String(500), nullable=True)
    sku                 = Column(String(200), nullable=True, index=True)
    category            = Column(String(200), nullable=True)
    quantity            = Column(Integer,     nullable=True)

    selling_price       = Column(Numeric(14, 2), nullable=True)
    mrp                 = Column(Numeric(14, 2), nullable=True)
    customer_paid       = Column(Numeric(18, 2), nullable=True)
    order_amount        = Column(Numeric(18, 2), nullable=True)

    commission_rate     = Column(Numeric(6, 3),  nullable=True)
    commission          = Column(Numeric(18, 2), nullable=True)
    shipping_charges    = Column(Numeric(18, 2), nullable=True)
    reverse_shipping    = Column(Numeric(18, 2), nullable=True)
    gst_on_commission   = Column(Numeric(18, 2), nullable=True)
    tcs                 = Column(Numeric(18, 2), nullable=True)
    other_deductions    = Column(Numeric(18, 2), nullable=True)
    net_payment         = Column(Numeric(18, 2), nullable=True)
    expected_net        = Column(Numeric(18, 2), nullable=True)
    payment_variance    = Column(Numeric(18, 2), nullable=True)

    order_status        = Column(String(50),  nullable=True)
    payment_status      = Column(String(50),  nullable=True)

    report = relationship("MeeshoReport", back_populates="order_rows")


class MeeshoReconIssue(Base):
    __tablename__ = "meesho_recon_issues"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id       = Column(PG_UUID(as_uuid=True), ForeignKey("meesho_reports.id", ondelete="CASCADE"), nullable=False, index=True)
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

    report = relationship("MeeshoReport", back_populates="recon_issues")
