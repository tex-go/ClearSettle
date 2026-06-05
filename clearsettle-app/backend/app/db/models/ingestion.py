"""
ORM models for the Intelligent Report Ingestion Engine (migration 031).

Tables:
  uploaded_files           — central file registry (platform-agnostic)
  report_detection_results — auto-detection metadata & confidence scores
  report_schema_versions   — schema catalog: platform × report_type × version
  report_processing_logs   — structured audit trail per file
  ingestion_ledger         — unified canonical transaction record (all platforms)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id                 = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id         = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by        = Column(PG_UUID(as_uuid=True), ForeignKey("users.id",    ondelete="SET NULL"), nullable=True)
    original_file_name = Column(String(512), nullable=False)
    file_hash_sha256   = Column(String(64),  nullable=False, index=True)
    mime_type          = Column(String(100), nullable=True)
    file_size_bytes    = Column(Integer,     nullable=True)
    upload_source      = Column(String(50),  nullable=False, default="web_upload")
    storage_path       = Column(Text,        nullable=True)
    # uploaded | detecting | detected | processing | done | failed | needs_review
    upload_status      = Column(String(30),  nullable=False, default="uploaded", index=True)
    error_message      = Column(Text,        nullable=True)
    uploaded_at        = Column(DateTime,    nullable=False, default=datetime.utcnow)
    processed_at       = Column(DateTime,    nullable=True)

    detection    = relationship("ReportDetectionResult", back_populates="uploaded_file", uselist=False, cascade="all, delete-orphan")
    logs         = relationship("ReportProcessingLog",   back_populates="uploaded_file", cascade="all, delete-orphan")
    ledger_rows  = relationship("IngestionLedger",       back_populates="uploaded_file", cascade="all, delete-orphan")


class ReportDetectionResult(Base):
    __tablename__ = "report_detection_results"

    id                   = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_file_id     = Column(PG_UUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False, unique=True)
    detected_platform    = Column(String(50), nullable=True, index=True)   # flipkart | amazon | meesho | unknown
    detected_report_type = Column(String(50), nullable=True)               # pl_report | payment_report | settlement | tax | returns | …
    schema_version       = Column(String(80), nullable=True)               # e.g. flipkart_pl_v1
    confidence_score     = Column(Numeric(5, 4), nullable=True)
    # JSON: sheet_names, matched_signals, column_count, sample_headers, fingerprint_summary
    detection_metadata   = Column(JSONB, nullable=True)
    parser_name          = Column(String(100), nullable=True)
    needs_manual_review  = Column(Boolean,     nullable=False, default=False)
    reviewed_by          = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at          = Column(DateTime,    nullable=True)
    created_at           = Column(DateTime,    nullable=False, default=datetime.utcnow)

    uploaded_file = relationship("UploadedFile", back_populates="detection")


class ReportSchemaVersion(Base):
    """Known schema catalog. One row per (platform, report_type, version) combination.

    schema_signature is SHA-256 of the sorted, lowercased, stripped column name list.
    When a new file arrives with an unknown signature → schema drift alert.
    """
    __tablename__ = "report_schema_versions"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform         = Column(String(50), nullable=False, index=True)
    report_type      = Column(String(50), nullable=False)
    schema_version   = Column(String(80), nullable=False)
    schema_signature = Column(String(64), nullable=False)
    expected_columns = Column(JSONB, nullable=True)
    optional_columns = Column(JSONB, nullable=True)
    parser_name      = Column(String(100), nullable=True)
    is_active        = Column(Boolean, nullable=False, default=True)
    first_seen_at    = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at       = Column(DateTime, nullable=False, default=datetime.utcnow)


class ReportProcessingLog(Base):
    """Structured audit log for every stage of ingestion processing."""
    __tablename__ = "report_processing_logs"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_file_id = Column(PG_UUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False, index=True)
    level            = Column(String(20), nullable=False)   # info | warning | error
    stage            = Column(String(50), nullable=False)   # fingerprint | detect | normalize | parse | store
    message          = Column(Text, nullable=False)
    context          = Column(JSONB, nullable=True)
    created_at       = Column(DateTime, nullable=False, default=datetime.utcnow)

    uploaded_file = relationship("UploadedFile", back_populates="logs")


class IngestionLedger(Base):
    """Unified canonical transaction record.

    Every normalised record from every source (manual upload, Amazon API,
    Flipkart API, Meesho API, …) lands here via LedgerSyncExecutor.

    PROVENANCE COLUMNS (source_type, connection_id, sync_job_id):
      Set by the connector; used only for traceability and debugging.
      The ETL, dashboard, and analytics layers never read these — they are
      invisible to all financial calculations.

    FROZEN COLUMNS (transaction_type, amount, order_id, …):
      Read by ETL (ledger_etl.py) to produce settlements + payout_events.
      Never rename or change semantics; adding new nullable columns is fine.
    """
    __tablename__ = "ingestion_ledger"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_file_id = Column(PG_UUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id       = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id",    ondelete="CASCADE"), nullable=False, index=True)

    # ── Provenance (migration 036) ─────────────────────────────────────────────
    # manual_upload | amazon_api | flipkart_api | meesho_api | shopify_api | …
    source_type  = Column(String(30), nullable=True, index=True, server_default="manual_upload")
    # Event schema version — "1.0" for original rows, "1.1" for rows with external_event_id
    event_version = Column(String(10), nullable=True, server_default="1.0")
    # Platform-native event identifier.  UNIQUE per (uploaded_file_id, external_event_id).
    # Set by all API connectors.  Manual uploads use "row_{source_row_number}".
    # NULL for legacy rows (pre-1.1).  Used for idempotent INSERT ON CONFLICT DO NOTHING.
    external_event_id = Column(String(500), nullable=True)
    # FK to marketplace_connections.id (null for manual uploads)
    connection_id = Column(PG_UUID(as_uuid=True),
                           ForeignKey("marketplace_connections.id", ondelete="SET NULL"),
                           nullable=True, index=True)
    # FK to marketplace_sync_jobs.id (null for manual uploads)
    sync_job_id   = Column(PG_UUID(as_uuid=True),
                           ForeignKey("marketplace_sync_jobs.id", ondelete="SET NULL"),
                           nullable=True)

    platform         = Column(String(50),  nullable=False, index=True)
    report_type      = Column(String(50),  nullable=True)
    order_id         = Column(String(200), nullable=True, index=True)
    shipment_id      = Column(String(200), nullable=True)
    settlement_id    = Column(String(200), nullable=True)
    invoice_id       = Column(String(200), nullable=True)
    sku              = Column(String(200), nullable=True, index=True)
    product_title    = Column(Text,        nullable=True)
    category         = Column(String(200), nullable=True)
    # sale | return | cancellation | fee | tax | adjustment | payout
    transaction_type = Column(String(50),  nullable=True)
    fee_type         = Column(String(100), nullable=True)
    amount           = Column(Numeric(18, 2), nullable=True)
    tax_amount       = Column(Numeric(18, 2), nullable=True)
    currency         = Column(String(10),  nullable=True, default="INR")
    transaction_date = Column(String(30),  nullable=True)   # ISO date string
    settlement_date  = Column(String(30),  nullable=True)
    return_status    = Column(String(50),  nullable=True)
    payout_status    = Column(String(50),  nullable=True)
    source_row_number = Column(Integer,    nullable=True)
    # {sheet_name, source_columns_used, raw_values_sample}
    lineage_metadata  = Column(JSONB,      nullable=True)
    created_at        = Column(DateTime,   nullable=False, default=datetime.utcnow)

    uploaded_file = relationship("UploadedFile", back_populates="ledger_rows")
