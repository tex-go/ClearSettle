"""ORM models for the Vendor Reconciliation Engine (migration 013)."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ReconFile(Base):
    __tablename__ = "recon_files"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id      = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    filename        = Column(String(255), nullable=False)
    original_name   = Column(String(255), nullable=False)
    file_type       = Column(String(50),  nullable=False)
    file_format     = Column(String(10),  nullable=True)
    file_size_bytes = Column(Integer,     nullable=True)
    status          = Column(String(20),  nullable=False, default="pending")
    row_count       = Column(Integer,     nullable=True)
    error_message   = Column(Text,        nullable=True)
    column_map_json = Column(Text,        nullable=True)
    created_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)
    processed_at    = Column(DateTime,    nullable=True)
    # Provenance — added migration 014
    source_type             = Column(String(30),    nullable=True)  # file_upload | api | manual
    ingestion_method        = Column(String(100),   nullable=True)  # csv_upload | xlsx_upload | amazon_sp_api | ...
    document_origin         = Column(String(150),   nullable=True)  # "amazon.in" | "flipkart.com" | filename
    source_confidence_score = Column(Numeric(4, 3), nullable=True)  # 0.000–1.000

    job_files = relationship("ReconJobFile", back_populates="file", cascade="all, delete-orphan")


class ReconJob(Base):
    __tablename__ = "recon_jobs"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id       = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name             = Column(String(200), nullable=False)
    description      = Column(Text,        nullable=True)
    period_start     = Column(Date,        nullable=True)
    period_end       = Column(Date,        nullable=True)
    status           = Column(String(20),  nullable=False, default="draft")
    platform         = Column(String(50),  nullable=True)
    currency         = Column(String(3),   nullable=False, default="INR")
    expected_payout  = Column(Numeric(16, 2), nullable=True)
    actual_payout    = Column(Numeric(16, 2), nullable=True)
    variance_amount  = Column(Numeric(16, 2), nullable=True)
    variance_pct     = Column(Numeric(8,  4),  nullable=True)
    total_leakage    = Column(Numeric(16, 2), nullable=True)
    leakage_count    = Column(Integer,     nullable=True)
    disputable_amount= Column(Numeric(16, 2), nullable=True)
    summary_json     = Column(Text,        nullable=True)
    error_message    = Column(Text,        nullable=True)
    created_at       = Column(DateTime,    nullable=False, default=datetime.utcnow)
    started_at       = Column(DateTime,    nullable=True)
    completed_at     = Column(DateTime,    nullable=True)

    job_files         = relationship("ReconJobFile",        back_populates="job", cascade="all, delete-orphan")
    settlement_lines  = relationship("StgSettlementLine",   back_populates="job", cascade="all, delete-orphan")
    invoice_lines     = relationship("StgInvoiceLine",      back_populates="job", cascade="all, delete-orphan")
    chargeback_lines  = relationship("StgChargebackLine",   back_populates="job", cascade="all, delete-orphan")
    payment_lines     = relationship("StgPaymentLine",      back_populates="job", cascade="all, delete-orphan")
    operational_lines = relationship("StgOperationalLine",  back_populates="job", cascade="all, delete-orphan")
    leakage_events    = relationship("LeakageEvent",        back_populates="job", cascade="all, delete-orphan")
    fact              = relationship("FactReconciliation",   back_populates="job", uselist=False, cascade="all, delete-orphan")


class ReconJobFile(Base):
    __tablename__ = "recon_job_files"
    __table_args__ = (UniqueConstraint("job_id", "file_id", name="uq_recon_job_file"),)

    id        = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id    = Column(PG_UUID(as_uuid=True), ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True)
    file_id   = Column(PG_UUID(as_uuid=True), ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=False)
    file_role = Column(String(50), nullable=False)

    job  = relationship("ReconJob",  back_populates="job_files")
    file = relationship("ReconFile", back_populates="job_files")


class StgSettlementLine(Base):
    __tablename__ = "stg_settlement_lines"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id           = Column(PG_UUID(as_uuid=True), ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True)
    file_id          = Column(PG_UUID(as_uuid=True), ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True)
    settlement_id    = Column(String(100), nullable=True)
    transaction_date = Column(Date,        nullable=True)
    reference_number = Column(String(150), nullable=True)
    invoice_number   = Column(String(150), nullable=True)
    po_number        = Column(String(150), nullable=True)
    deduction_code   = Column(String(100), nullable=True)
    deduction_reason = Column(String(255), nullable=True)
    line_type        = Column(String(50),  nullable=True)
    gross_amount     = Column(Numeric(16, 2), nullable=True)
    deduction_amount = Column(Numeric(16, 2), nullable=True)
    accrual_amount   = Column(Numeric(16, 2), nullable=True)
    reversal_amount  = Column(Numeric(16, 2), nullable=True)
    net_amount       = Column(Numeric(16, 2), nullable=True)
    tax_amount       = Column(Numeric(16, 2), nullable=True)
    currency         = Column(String(3),   nullable=True, default="INR")
    payment_reference= Column(String(150), nullable=True)
    sku              = Column(String(100), nullable=True)
    asin             = Column(String(20),  nullable=True)
    raw_row_json     = Column(Text,        nullable=True)
    created_at       = Column(DateTime,    nullable=False, default=datetime.utcnow)
    # Provenance — added migration 014
    source_type             = Column(String(30),    nullable=True)
    ingestion_method        = Column(String(100),   nullable=True)
    document_origin         = Column(String(150),   nullable=True)
    source_confidence_score = Column(Numeric(4, 3), nullable=True)

    job = relationship("ReconJob", back_populates="settlement_lines")


class StgInvoiceLine(Base):
    __tablename__ = "stg_invoice_lines"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id          = Column(PG_UUID(as_uuid=True), ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True)
    file_id         = Column(PG_UUID(as_uuid=True), ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True)
    invoice_number  = Column(String(150), nullable=True, index=True)
    invoice_date    = Column(Date,        nullable=True)
    po_number       = Column(String(150), nullable=True, index=True)
    sku             = Column(String(100), nullable=True)
    asin            = Column(String(20),  nullable=True)
    quantity        = Column(Numeric(12, 3), nullable=True)
    unit_price      = Column(Numeric(14, 4), nullable=True)
    invoice_total   = Column(Numeric(16, 2), nullable=True)
    tax_amount      = Column(Numeric(16, 2), nullable=True)
    discount_amount = Column(Numeric(16, 2), nullable=True)
    currency        = Column(String(3),   nullable=True, default="INR")
    vendor_code     = Column(String(100), nullable=True)
    raw_row_json    = Column(Text,        nullable=True)
    created_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)
    # Provenance — added migration 014
    source_type             = Column(String(30),    nullable=True)
    ingestion_method        = Column(String(100),   nullable=True)
    document_origin         = Column(String(150),   nullable=True)
    source_confidence_score = Column(Numeric(4, 3), nullable=True)

    job = relationship("ReconJob", back_populates="invoice_lines")


class StgChargebackLine(Base):
    __tablename__ = "stg_chargeback_lines"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id           = Column(PG_UUID(as_uuid=True), ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True)
    file_id          = Column(PG_UUID(as_uuid=True), ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True)
    chargeback_id    = Column(String(150), nullable=True)
    deduction_code   = Column(String(100), nullable=True, index=True)
    deduction_reason = Column(String(255), nullable=True)
    po_number        = Column(String(150), nullable=True)
    invoice_number   = Column(String(150), nullable=True)
    shipment_id      = Column(String(150), nullable=True)
    deduction_amount = Column(Numeric(16, 2), nullable=True)
    dispute_status   = Column(String(50),  nullable=True)
    created_date     = Column(Date,        nullable=True)
    dispute_deadline = Column(Date,        nullable=True)
    raw_row_json     = Column(Text,        nullable=True)
    created_at       = Column(DateTime,    nullable=False, default=datetime.utcnow)
    # Provenance — added migration 014
    source_type             = Column(String(30),    nullable=True)
    ingestion_method        = Column(String(100),   nullable=True)
    document_origin         = Column(String(150),   nullable=True)
    source_confidence_score = Column(Numeric(4, 3), nullable=True)

    job = relationship("ReconJob", back_populates="chargeback_lines")


class StgPaymentLine(Base):
    __tablename__ = "stg_payment_lines"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id          = Column(PG_UUID(as_uuid=True), ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True)
    file_id         = Column(PG_UUID(as_uuid=True), ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True)
    settlement_id   = Column(String(100), nullable=True, index=True)
    bank_reference  = Column(String(150), nullable=True)
    paid_amount     = Column(Numeric(16, 2), nullable=True)
    transfer_date   = Column(Date,        nullable=True)
    payment_method  = Column(String(50),  nullable=True)
    currency        = Column(String(3),   nullable=True, default="INR")
    bank_account    = Column(String(50),  nullable=True)
    raw_row_json    = Column(Text,        nullable=True)
    created_at      = Column(DateTime,    nullable=False, default=datetime.utcnow)
    # Provenance — added migration 014
    source_type             = Column(String(30),    nullable=True)
    ingestion_method        = Column(String(100),   nullable=True)
    document_origin         = Column(String(150),   nullable=True)
    source_confidence_score = Column(Numeric(4, 3), nullable=True)

    job = relationship("ReconJob", back_populates="payment_lines")


class StgOperationalLine(Base):
    __tablename__ = "stg_operational_lines"

    id                = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id            = Column(PG_UUID(as_uuid=True), ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True)
    file_id           = Column(PG_UUID(as_uuid=True), ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True)
    line_category     = Column(String(30),  nullable=False, index=True)
    po_number         = Column(String(150), nullable=True, index=True)
    invoice_number    = Column(String(150), nullable=True)
    shipment_id       = Column(String(150), nullable=True)
    claim_id          = Column(String(150), nullable=True)
    dispute_id        = Column(String(150), nullable=True)
    sku               = Column(String(100), nullable=True)
    asin              = Column(String(20),  nullable=True)
    event_date        = Column(Date,        nullable=True)
    expected_date     = Column(Date,        nullable=True)
    actual_date       = Column(Date,        nullable=True)
    ordered_qty       = Column(Numeric(12, 3), nullable=True)
    shipped_qty       = Column(Numeric(12, 3), nullable=True)
    received_qty      = Column(Numeric(12, 3), nullable=True)
    short_qty         = Column(Numeric(12, 3), nullable=True)
    damaged_qty       = Column(Numeric(12, 3), nullable=True)
    return_qty        = Column(Numeric(12, 3), nullable=True)
    amount            = Column(Numeric(16, 2), nullable=True)
    penalty_amount    = Column(Numeric(16, 2), nullable=True)
    recovered_amount  = Column(Numeric(16, 2), nullable=True)
    compliance_status = Column(String(50),  nullable=True)
    dispute_status    = Column(String(50),  nullable=True)
    fill_rate_pct     = Column(Numeric(6, 3), nullable=True)
    warehouse         = Column(String(100), nullable=True)
    return_reason     = Column(String(255), nullable=True)
    receiver_name     = Column(String(150), nullable=True)
    extra_json        = Column(Text,        nullable=True)
    raw_row_json      = Column(Text,        nullable=True)
    created_at        = Column(DateTime,    nullable=False, default=datetime.utcnow)
    # Provenance — added migration 014
    source_type             = Column(String(30),    nullable=True)
    ingestion_method        = Column(String(100),   nullable=True)
    document_origin         = Column(String(150),   nullable=True)
    source_confidence_score = Column(Numeric(4, 3), nullable=True)

    job = relationship("ReconJob", back_populates="operational_lines")


class FactReconciliation(Base):
    __tablename__ = "fact_reconciliation"

    id                     = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id                 = Column(PG_UUID(as_uuid=True), ForeignKey("recon_jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_invoice_value    = Column(Numeric(16, 2), nullable=True)
    total_agreed_discounts = Column(Numeric(16, 2), nullable=True)
    total_valid_returns    = Column(Numeric(16, 2), nullable=True)
    total_approved_coop    = Column(Numeric(16, 2), nullable=True)
    total_valid_tax_adj    = Column(Numeric(16, 2), nullable=True)
    expected_payout        = Column(Numeric(16, 2), nullable=True)
    actual_payout          = Column(Numeric(16, 2), nullable=True)
    variance_amount        = Column(Numeric(16, 2), nullable=True)
    variance_pct           = Column(Numeric(8,  4),  nullable=True)
    total_deductions       = Column(Numeric(16, 2), nullable=True)
    valid_deductions       = Column(Numeric(16, 2), nullable=True)
    suspicious_deductions  = Column(Numeric(16, 2), nullable=True)
    duplicate_deductions   = Column(Numeric(16, 2), nullable=True)
    disputable_amount      = Column(Numeric(16, 2), nullable=True)
    unrecovered_claims     = Column(Numeric(16, 2), nullable=True)
    total_leakage          = Column(Numeric(16, 2), nullable=True)
    leakage_by_type_json   = Column(Text,           nullable=True)
    computed_at            = Column(DateTime,        nullable=False, default=datetime.utcnow)

    job = relationship("ReconJob", back_populates="fact")


class LeakageEvent(Base):
    __tablename__ = "leakage_events"

    id                      = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id                  = Column(PG_UUID(as_uuid=True), ForeignKey("recon_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    leakage_type            = Column(String(30),  nullable=False, index=True)
    severity                = Column(String(20),  nullable=False)
    reference_type          = Column(String(30),  nullable=True)
    reference_id            = Column(String(200), nullable=True)
    po_number               = Column(String(150), nullable=True)
    invoice_number          = Column(String(150), nullable=True)
    sku                     = Column(String(100), nullable=True)
    deduction_code          = Column(String(100), nullable=True)
    amount                  = Column(Numeric(16, 2), nullable=True)
    description             = Column(Text,        nullable=False)
    root_cause              = Column(Text,        nullable=True)
    is_disputable           = Column(Boolean,     nullable=False, default=False)
    recovery_potential      = Column(Numeric(16, 2), nullable=True)
    recovery_recommendation = Column(Text,        nullable=True)
    evidence_json           = Column(Text,        nullable=True, default="[]")
    status                  = Column(String(20),  nullable=False, default="open")
    resolved_by             = Column(String(100), nullable=True)
    resolution_note         = Column(Text,        nullable=True)
    created_at              = Column(DateTime,    nullable=False, default=datetime.utcnow)
    resolved_at             = Column(DateTime,    nullable=True)

    job = relationship("ReconJob", back_populates="leakage_events")


class DimDeductionCode(Base):
    __tablename__ = "dim_deduction_codes"

    id                 = Column(Integer,     primary_key=True, autoincrement=True)
    code               = Column(String(50),  nullable=False, unique=True)
    name               = Column(String(200), nullable=False)
    category           = Column(String(50),  nullable=False)
    is_dispute_allowed = Column(Boolean,     nullable=False, default=True)
    severity_level     = Column(String(20),  nullable=False, default="warning")
    description        = Column(Text,        nullable=True)
    platform           = Column(String(50),  nullable=True)
    created_at         = Column(DateTime,    nullable=False, default=datetime.utcnow)
