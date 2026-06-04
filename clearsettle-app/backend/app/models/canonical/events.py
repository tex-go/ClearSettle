"""
Canonical Ledger Event — the immutable contract between every data source
and the ingestion_ledger table.

ARCHITECTURE RULE
-----------------
Every source — manual Excel upload, Amazon SP API, Flipkart API, Meesho API,
Shopify, WooCommerce, ERP, bank statement — MUST produce CanonicalLedgerEvent
objects.  No source may write to ingestion_ledger directly.

The ETL service (ledger_etl.py) reads from ingestion_ledger.  It must never
be changed to accommodate a new source.  Adding a new marketplace = implement
IngestionConnector.fetch_canonical_events().  That is all.

STABILITY CONTRACT
------------------
Fields below the "# FROZEN — ETL reads these" comment must NEVER be renamed,
removed, or have their semantics changed.  Adding new optional fields is fine.
The ETL, dashboard, analytics, and reconciliation layers depend on this contract
at the field level.

TransactionType values are also frozen.  New types may be added; existing types
must keep their meaning.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Frozen enumerations ───────────────────────────────────────────────────────

class SourceType(str, Enum):
    """How the data entered the system.  Stored in ingestion_ledger.source_type."""
    MANUAL_UPLOAD  = "manual_upload"    # Excel / CSV uploaded by user
    AMAZON_API     = "amazon_api"       # Amazon Selling Partner API
    FLIPKART_API   = "flipkart_api"     # Flipkart Seller API
    MEESHO_API     = "meesho_api"       # Meesho Partner API
    SHOPIFY_API    = "shopify_api"      # Shopify Admin API
    WOOCOMMERCE    = "woocommerce"      # WooCommerce REST API
    MYNTRA_API     = "myntra_api"       # Myntra Seller API
    AJIO_API       = "ajio_api"         # AJIO Seller API
    BANK_STATEMENT = "bank_statement"   # Bank reconciliation import
    ERP            = "erp"              # SAP / Tally / Zoho ERP export
    MANUAL_ENTRY   = "manual_entry"     # Human-entered via admin UI


class TransactionType(str, Enum):
    """
    Canonical transaction type taxonomy.

    FROZEN — ETL reads these values.  Do not change existing names or semantics.
    New types may be added at the bottom.

    Mapping reference:
      Amazon:   Order  → SALE, Refund → RETURN, FBA fee → FEE, TCS → TAX
      Flipkart: MY_SHARE → SALE, Return → RETURN, Commission → FEE, TCS → TAX
      Meesho:   Credit → SALE, Debit (return) → RETURN, Fees → FEE
      Payout/settlement row from any platform → PAYOUT
    """
    # Revenue
    SALE         = "sale"          # gross order revenue (positive)
    RETURN       = "return"        # customer return / refund (negative)
    CANCELLATION = "cancellation"  # cancelled order (negative)
    ADJUSTMENT   = "adjustment"    # marketplace credit / debit correction

    # Fees (typically negative amounts)
    FEE               = "fee"               # generic platform fee
    COMMISSION        = "commission"        # referral / commission fee
    FIXED_FEE         = "fixed_fee"         # per-item fixed fee
    SHIPPING_FEE      = "shipping_fee"      # forward shipping
    REVERSE_SHIPPING  = "reverse_shipping"  # return shipping / RTO
    COLLECTION_FEE    = "collection_fee"    # payment collection fee
    STORAGE_FEE       = "storage_fee"       # warehouse / FBA storage

    # Taxes
    TAX = "tax"    # generic tax
    TDS = "tds"    # TDS deducted at source
    TCS = "tcs"    # TCS collected at source
    GST = "gst"    # GST on marketplace fees

    # Settlement / payout
    PAYOUT = "payout"  # actual bank transfer / net settlement amount


# ── Canonical event ───────────────────────────────────────────────────────────

class CanonicalLedgerEvent(BaseModel):
    """
    One normalised transaction row.

    Source connectors yield these objects; the LedgerSyncExecutor writes them
    to ingestion_ledger.  Downstream systems (ETL, dashboard, reconciliation)
    read from ingestion_ledger and must not depend on any field below the
    provenance section.

    Field sections:
      PROVENANCE  — filled by the connector, stored for traceability, not used by ETL
      FROZEN      — ETL contract fields; never rename or change semantics
      EXTENDED    — optional enrichment; downstream systems may use if present
    """
    model_config = {"extra": "ignore"}

    # ── PROVENANCE ─────────────────────────────────────────────────────────────
    source_type:        SourceType
    platform:           str                     # flipkart | amazon | meesho | …
    uploaded_file_id:   Optional[UUID] = None   # set when source_type=manual_upload
    connection_id:      Optional[UUID] = None   # set when source_type=*_api
    sync_job_id:        Optional[UUID] = None   # set when triggered by scheduled sync

    # ── FROZEN — ETL reads these ───────────────────────────────────────────────
    transaction_type:   str                     # TransactionType enum value
    amount:             Decimal

    order_id:           Optional[str] = None
    shipment_id:        Optional[str] = None
    settlement_id:      Optional[str] = None
    invoice_id:         Optional[str] = None

    currency:           str = "INR"
    transaction_date:   Optional[str] = None    # ISO date string YYYY-MM-DD
    settlement_date:    Optional[str] = None

    # ── EXTENDED — optional enrichment ────────────────────────────────────────
    sku:                Optional[str] = None
    product_title:      Optional[str] = None
    category:           Optional[str] = None
    fee_type:           Optional[str] = None
    tax_amount:         Optional[Decimal] = None
    return_status:      Optional[str] = None
    payout_status:      Optional[str] = None
    report_type:        Optional[str] = None
    source_row_number:  Optional[int] = None
    lineage_metadata:   Optional[Dict[str, Any]] = None

    @field_validator("amount", "tax_amount", mode="before")
    @classmethod
    def _coerce_decimal(cls, v):
        if v is None:
            return v
        return Decimal(str(v))

    @field_validator("transaction_type", mode="before")
    @classmethod
    def _normalise_tx_type(cls, v):
        if isinstance(v, TransactionType):
            return v.value
        return str(v).lower()

    @field_validator("platform", mode="before")
    @classmethod
    def _normalise_platform(cls, v):
        return str(v).lower().strip() if v else "unknown"


# ── Connector result ──────────────────────────────────────────────────────────

class ConnectorResult(BaseModel):
    """Summary returned by LedgerSyncExecutor after ingesting events from a connector."""

    source_type:        SourceType
    platform:           str
    events_total:       int = 0
    events_written:     int = 0
    events_skipped:     int = 0
    settlements_created: int = 0
    settlements_updated: int = 0
    payouts_upserted:   int = 0
    errors:             List[str] = Field(default_factory=list)
    warnings:           List[str] = Field(default_factory=list)
    duration_ms:        float = 0.0

    @property
    def success(self) -> bool:
        return not self.errors
