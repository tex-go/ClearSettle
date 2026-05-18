"""
Pydantic v2 response schemas for settlement APIs.

All monetary amounts are floats (INR). UUIDs are native UUID objects.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ── Payout ────────────────────────────────────────────────────────────────────

class PayoutOut(BaseModel):
    id: UUID
    status: str
    amount: float
    transfer_date: Optional[datetime] = None
    account_tail:  Optional[str]      = None
    external_id:   Optional[str]      = None


# ── Fee breakdown ─────────────────────────────────────────────────────────────

class FeeLineItemOut(BaseModel):
    fee_type:     str
    label:        str
    total_amount: float   # negative for deductions
    count:        int


class FeeBreakdownOut(BaseModel):
    gross_amount:  float                  # sum of shipment principal amounts
    referral_fees: float                  # ReferralFee + Commission
    fba_fees:      float                  # FBA fulfillment fees
    closing_fees:  float                  # Variable Closing + Per Item
    shipping_fees: float                  # Shipping charges
    tcs_taxes:     float                  # Marketplace Facilitator Tax
    service_fees:  float                  # Service fee transactions (penalties)
    other_fees:    float                  # Uncategorised fees
    refund_total:  float                  # Total from refund transactions
    net_payout:    float                  # Effective payout to seller
    fee_items:     list[FeeLineItemOut]


# ── Settlement list ───────────────────────────────────────────────────────────

class SettlementListItemOut(BaseModel):
    id:                    UUID
    external_id:           str
    platform:              str
    platform_label:        str
    status:                str
    status_label:          str
    period_start:          Optional[datetime] = None
    period_end:            Optional[datetime] = None
    period_label:          str
    currency:              str
    total_amount:          float
    fees_total:            float
    fund_transfer_amount:  Optional[float]    = None
    net_amount:            float              # fund_transfer_amount or total+fees
    transactions_count:    int
    fund_transfer_date:    Optional[datetime] = None
    account_tail:          Optional[str]      = None
    payout_status:         Optional[str]      = None
    reconciliation_status: Optional[str]      = None
    created_at:            datetime


class SettlementSummaryOut(BaseModel):
    total_settlements: int
    closed_count:      int
    open_count:        int
    processing_count:  int
    total_gross:       float
    total_fees:        float
    total_net:         float
    pending_amount:    float
    total_transactions: int


class SettlementListResponse(BaseModel):
    items:       list[SettlementListItemOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int
    summary:     SettlementSummaryOut


# ── Settlement detail ─────────────────────────────────────────────────────────

class SettlementDetailOut(BaseModel):
    id:                    UUID
    external_id:           str
    platform:              str
    platform_label:        str
    status:                str
    status_label:          str
    period_start:          Optional[datetime] = None
    period_end:            Optional[datetime] = None
    period_label:          str
    currency:              str
    total_amount:          float
    fees_total:            float
    fund_transfer_amount:  Optional[float]    = None
    beginning_balance:     Optional[float]    = None
    transactions_count:    int
    fund_transfer_date:    Optional[datetime] = None
    account_tail:          Optional[str]      = None
    created_at:            datetime
    updated_at:            datetime
    payout:                Optional[PayoutOut]  = None
    fee_breakdown:         FeeBreakdownOut
    reconciliation_status: Optional[str]      = None


# ── Transactions ──────────────────────────────────────────────────────────────

class TransactionItemOut(BaseModel):
    id:               UUID
    transaction_type: str
    order_id:         Optional[str]      = None
    order_item_id:    Optional[str]      = None
    sku:              Optional[str]      = None
    marketplace:      Optional[str]      = None
    posted_date:      Optional[datetime] = None
    quantity:         int
    currency:         str
    principal_amount: float
    shipping_amount:  float
    total_amount:     float
    fees_total:       float
    net_amount:       float
    created_at:       datetime


class TransactionTypeSummaryOut(BaseModel):
    transaction_type: str
    count:            int
    total_amount:     float
    fees_total:       float
    net_amount:       float


class TransactionListResponse(BaseModel):
    items:       list[TransactionItemOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int
    by_type:     list[TransactionTypeSummaryOut]


# ── Payouts ───────────────────────────────────────────────────────────────────

class PayoutItemOut(BaseModel):
    id:                      UUID
    settlement_id:           UUID
    settlement_external_id:  str
    platform:                str
    platform_label:          str
    status:                  str
    amount:                  float
    transfer_date:           Optional[datetime] = None
    account_tail:            Optional[str]      = None


class PayoutListResponse(BaseModel):
    items:            list[PayoutItemOut]
    total:            int
    total_transferred: float
    total_pending:    float
    total_failed:     float
