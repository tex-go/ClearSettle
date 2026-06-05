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

STABILITY CONTRACT (v1.0 — locked 2026-06-05)
------------------
Fields marked FROZEN must NEVER be renamed, removed, or have semantics changed.
The ETL, dashboard, analytics, and reconciliation layers depend on these at the
field level.

TransactionType values: existing values are frozen. New values may be appended.

VERSIONING
----------
event_version tracks the schema version of this event object.
  1.0 — initial frozen contract (2026-06-05)

When fields are added (always optional / backward-compatible):
  - bump event_version to 1.N
  - add migration to ingestion_ledger
  - ETL remains unchanged (it reads only FROZEN fields)

IDEMPOTENCY
-----------
external_event_id is the platform-native event identifier.
LedgerSyncExecutor uses it for INSERT ... ON CONFLICT DO NOTHING.
Connectors MUST set this for API sources.  Manual uploads use source_row_number.

Contract:
  Amazon:   external_event_id = "{order_id}::{charge_component_id}::{tx_type}"
  Flipkart: external_event_id = "{order_item_id}::{tx_type}"
  Meesho:   external_event_id = "{sub_order_id}::{tx_type}"
  Manual:   external_event_id = f"row_{source_row_number}"  (set by ManualUploadConnector)
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
    UNICOMMERCE    = "unicommerce"      # Unicommerce OMS export
    EASYELCOM      = "easyecom"         # EasyEcom OMS export


class TransactionType(str, Enum):
    """
    Canonical transaction type taxonomy.

    FROZEN (v1.0) — existing values must never be renamed or have semantics changed.
    New values may be appended.  The ETL reads:
        SALE, RETURN, CANCELLATION, FEE, COMMISSION, FIXED_FEE, SHIPPING_FEE,
        REVERSE_SHIPPING, COLLECTION_FEE, STORAGE_FEE, TAX, TDS, TCS, GST, PAYOUT
    All other types are passed through as-is and treated as ADJUSTMENT by ETL.

    Platform mappings:
      Amazon SP API:
        ShipmentEvent.Principal         → SALE
        ShipmentEvent.ItemFee           → COMMISSION / FIXED_FEE / SHIPPING_FEE
        ShipmentEvent.ItemTax (TCS)     → TCS
        ShipmentEvent.ItemTax (TDS)     → TDS
        RefundEvent.Principal           → RETURN
        RefundEvent.ItemFee             → FEE (negative)
        ChargebackEvent                 → RETURN
        GuaranteeClaimEvent             → RETURN
        SAFETReimbursementEvent         → REIMBURSEMENT
        ServiceFeeEvent                 → FEE
        FBAServiceFeeEvent              → STORAGE_FEE
        ProductAdsPaymentEvent          → FEE
        CouponPaymentEvent              → COUPON_CREDIT
        LoanServicingEvent              → LOAN_FEE
        PerformanceBondRefundEvent      → REIMBURSEMENT
        SellerReviewEnrollmentPayment   → FEE
        FinancialEventGroup.Original    → PAYOUT (one per settlement group)

      Flipkart Seller API:
        ORDER_CREDIT / MY_SHARE        → SALE
        RETURN_DEBIT                   → RETURN
        COMMISSION                     → COMMISSION
        FIXED_FEE                      → FIXED_FEE
        SHIPPING_FORWARD               → SHIPPING_FEE
        SHIPPING_REVERSE               → REVERSE_SHIPPING
        COLLECTION_FEE                 → COLLECTION_FEE
        TCS_DEBIT                      → TCS
        TDS_DEBIT                      → TDS
        GST_ON_FEES                    → GST
        PENALTY                        → PENALTY
        WALLET_REDEEM                  → WALLET_REDEEM
        TECH_CHARGE                    → FEE
        NEFT_CREDIT                    → PAYOUT

      Meesho Partner API:
        FORWARD order credit           → SALE
        REVERSE order debit            → RETURN
        COMMISSION                     → COMMISSION
        SHIPPING                       → SHIPPING_FEE
        REVERSE_PICKUP                 → REVERSE_SHIPPING
        TCS_AMOUNT                     → TCS
        NEFT_CREDIT settlement         → PAYOUT
    """
    # ── Revenue (FROZEN v1.0) ────────────────────────────────────────────────
    SALE         = "sale"          # gross order revenue (positive)
    RETURN       = "return"        # customer return / refund (negative)
    CANCELLATION = "cancellation"  # cancelled order (negative)
    ADJUSTMENT   = "adjustment"    # marketplace credit / debit correction

    # ── Fees (FROZEN v1.0) — typically negative amounts ──────────────────────
    FEE              = "fee"              # generic platform fee
    COMMISSION       = "commission"       # referral / commission fee
    FIXED_FEE        = "fixed_fee"        # per-item fixed fee
    SHIPPING_FEE     = "shipping_fee"     # forward shipping
    REVERSE_SHIPPING = "reverse_shipping" # return shipping / RTO
    COLLECTION_FEE   = "collection_fee"   # payment collection fee
    STORAGE_FEE      = "storage_fee"      # warehouse / FBA storage

    # ── Taxes (FROZEN v1.0) ───────────────────────────────────────────────────
    TAX = "tax"    # generic tax
    TDS = "tds"    # TDS deducted at source
    TCS = "tcs"    # TCS collected at source
    GST = "gst"    # GST on marketplace fees

    # ── Settlement / payout (FROZEN v1.0) ────────────────────────────────────
    PAYOUT = "payout"  # actual bank transfer / net settlement amount

    # ── Extended types (added v1.1 — ETL treats as ADJUSTMENT) ───────────────
    PENALTY         = "penalty"         # SLA / policy violation charge (Flipkart)
    REIMBURSEMENT   = "reimbursement"   # SAFE-T / lost & damaged claim payout (Amazon)
    WALLET_REDEEM   = "wallet_redeem"   # Flipkart wallet credit redemption
    COUPON_CREDIT   = "coupon_credit"   # Seller-funded coupon discount (Amazon)
    LOAN_FEE        = "loan_fee"        # Amazon Lending fee
    INVENTORY_ADJ   = "inventory_adj"   # FBA inventory adjustment
    SUBSCRIPTION    = "subscription"    # Platform subscription / membership fee
    BANK_CREDIT     = "bank_credit"     # Bank statement credit (bank_statement source)
    BANK_DEBIT      = "bank_debit"      # Bank statement debit (bank_statement source)
    JOURNAL_ENTRY   = "journal_entry"   # ERP general ledger entry
    DEAL_FEE        = "deal_fee"        # Lightning Deal / promotion fee (Amazon)


# ── Canonical event ───────────────────────────────────────────────────────────

class CanonicalLedgerEvent(BaseModel):
    """
    One normalised transaction row.  Version 1.1.

    Source connectors yield these objects; the LedgerSyncExecutor writes them
    to ingestion_ledger.  Downstream systems (ETL, dashboard, reconciliation)
    read from ingestion_ledger and must not depend on any field outside the
    FROZEN section.

    Field sections:
      PROVENANCE  — filled by the connector, for traceability only, not used by ETL
      FROZEN      — ETL contract fields; never rename or change semantics
      IDEMPOTENCY — deduplication key; MUST be set by all API connectors
      EXTENDED    — optional enrichment; safe to add, never remove
    """
    model_config = {"extra": "ignore"}

    # ── PROVENANCE ─────────────────────────────────────────────────────────────
    source_type:       SourceType
    platform:          str                     # flipkart | amazon | meesho | …
    event_version:     str = "1.1"             # schema version for forward compat
    uploaded_file_id:  Optional[UUID] = None   # set when source_type=manual_upload
    connection_id:     Optional[UUID] = None   # set when source_type=*_api
    sync_job_id:       Optional[UUID] = None   # set when triggered by scheduled sync

    # ── IDEMPOTENCY ────────────────────────────────────────────────────────────
    # Platform-native event ID.  LedgerSyncExecutor uses this for
    # INSERT ... ON CONFLICT (uploaded_file_id, external_event_id) DO NOTHING.
    # MUST be set for all API connectors.  Manual: "row_{source_row_number}".
    # Format contract per platform — see module docstring.
    external_event_id: Optional[str] = None

    # ── FROZEN — ETL reads these (v1.0 — never change) ────────────────────────
    transaction_type:  str                     # TransactionType enum value
    amount:            Decimal

    order_id:          Optional[str] = None
    shipment_id:       Optional[str] = None
    settlement_id:     Optional[str] = None    # MUST be set for PAYOUT events
    invoice_id:        Optional[str] = None

    currency:          str = "INR"
    transaction_date:  Optional[str] = None    # ISO date string YYYY-MM-DD
    settlement_date:   Optional[str] = None

    # ── EXTENDED — optional enrichment (safe to add new fields) ───────────────
    sku:               Optional[str] = None
    product_title:     Optional[str] = None
    category:          Optional[str] = None
    fee_type:          Optional[str] = None
    tax_amount:        Optional[Decimal] = None
    return_status:     Optional[str] = None
    payout_status:     Optional[str] = None
    report_type:       Optional[str] = None
    source_row_number: Optional[int] = None
    # Connector-specific raw data / enrichment.  Keys are namespaced by source:
    #   {"amazon": {"financial_event_group_id": "...", "charge_type": "..."}}
    #   {"flipkart": {"order_item_id": "...", "charge_category": "..."}}
    lineage_metadata:  Optional[Dict[str, Any]] = None

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
