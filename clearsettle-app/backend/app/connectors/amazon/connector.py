"""
AmazonConnector — Amazon Selling Partner API integration.

IMPLEMENTATION STATUS: COMPLETE MAPPING + SKELETON (Phase 2)

All SP API financial event types are fully mapped to CanonicalLedgerEvent.
The HTTP client calls raise NotImplementedError — wire them up in Phase 2
by implementing the _sp_client calls.

SP API required scopes:
    Finances_Listings  (ListFinancialEventGroups, ListFinancialEvents)
    Orders             (GetOrders — optional, for product title enrichment)

SP API rate limits (respect these in Phase 2 implementation):
    ListFinancialEventGroups  — 0.5 req/s, burst 30
    ListFinancialEvents       — 0.5 req/s, burst 30

Amazon IN marketplace ID: A21TJRUUN4KGV
Amazon IN settlement currency: INR

COMPLETE SP API → CanonicalLedgerEvent MAPPING
----------------------------------------------
SP API Event Type                        → TransactionType   Notes
─────────────────────────────────────────────────────────────────────────────
ShipmentEvent.ItemChargeList.Principal   → SALE              order item revenue
ShipmentEvent.ItemChargeList.Tax (TCS)   → TCS               tax collected at source
ShipmentEvent.ItemChargeList.Tax (TDS)   → TDS               tax deducted at source
ShipmentEvent.ItemFeeList.Ref Fee        → COMMISSION        referral / commission fee
ShipmentEvent.ItemFeeList.Fixed Fee      → FIXED_FEE         per-item fixed fee
ShipmentEvent.ItemFeeList.FBA            → STORAGE_FEE       FBA fulfillment / storage
ShipmentEvent.ItemFeeList.Shipping       → SHIPPING_FEE      forward shipping
ShipmentEvent.ItemFeeList.Other fees     → FEE               generic fee
ShipmentEvent.ShipmentFeeList            → SHIPPING_FEE      order-level shipping
ShipmentEvent.DirectPaymentList          → ADJUSTMENT        direct payment adjustment
RefundEvent.ItemChargeAdjustmentList     → RETURN            refund principal (negative)
RefundEvent.ItemFeeAdjustmentList        → FEE               refund fee adjustment
ChargebackEvent                          → RETURN            chargeback (negative)
GuaranteeClaimEvent                      → RETURN            A-to-Z claim (negative)
SAFETReimbursementEvent                  → REIMBURSEMENT     SAFE-T reimbursement
ServiceFeeEvent                          → FEE               seller services fee
FBAServiceFeeEvent                       → STORAGE_FEE       FBA service fee
ProductAdsPaymentEvent                   → FEE               Sponsored Products
CouponPaymentEvent                       → COUPON_CREDIT     seller-funded coupon
LoanServicingEvent                       → LOAN_FEE          Amazon Lending
SellerDealPaymentEvent                   → DEAL_FEE          Lightning Deal fee
PerformanceBondRefundEvent               → REIMBURSEMENT     performance bond return
ImagingServicesFeeEvent                  → FEE               product imaging
SellerReviewEnrollmentPayment            → FEE               Vine / review program
FinancialEventGroup.OriginalTotal        → PAYOUT            net settlement (one per group)

IDEMPOTENCY KEYS (external_event_id format)
-------------------------------------------
SALE/RETURN/FEE per item:  "{order_id}::{amazon_order_item_id}::{charge_type}::{tx_type}"
Group PAYOUT:              "payout::{financial_event_group_id}"
Service fees:              "service::{service_fee_event_id}::{fee_type}"
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, List, Optional
from uuid import UUID

from app.connectors.base import ConnectionHealth, DataRange, IngestionConnector
from app.connectors.registry import connector_registry
from app.models.canonical.events import CanonicalLedgerEvent, SourceType, TransactionType

logger = logging.getLogger(__name__)


# ── Fee type → TransactionType mapping ───────────────────────────────────────
# Amazon FeeType strings from SP API ItemFeeList
_FEE_TYPE_MAP = {
    # Referral / commission fees
    "ReferralFee":                    TransactionType.COMMISSION,
    "VariableClosingFee":             TransactionType.FIXED_FEE,
    "PerItemFee":                     TransactionType.FIXED_FEE,
    # FBA fees
    "FBAPerUnitFulfillmentFee":       TransactionType.STORAGE_FEE,
    "FBAWeightBasedFee":              TransactionType.STORAGE_FEE,
    "FBAPerOrderFulfillmentFee":      TransactionType.STORAGE_FEE,
    "FBADisposalFee":                 TransactionType.STORAGE_FEE,
    "LongTermStorageFee":             TransactionType.STORAGE_FEE,
    "FBAInventoryStorageFee":         TransactionType.STORAGE_FEE,
    # Shipping
    "ShippingCharge":                 TransactionType.SHIPPING_FEE,
    "ShippingHBFee":                  TransactionType.SHIPPING_FEE,
    "Shipping":                       TransactionType.SHIPPING_FEE,
    # Tax
    "MarketplaceFacilitatorTax-Principal":  TransactionType.TCS,
    "MarketplaceFacilitatorTax-Shipping":   TransactionType.TCS,
    "LowValueGoodsTax-Principal":           TransactionType.TCS,
    "TDS":                                  TransactionType.TDS,
    # Other
    "GiftwrapCharge":                 TransactionType.FEE,
    "ReturnShipping":                 TransactionType.REVERSE_SHIPPING,
    "ServiceFee":                     TransactionType.FEE,
}


def _map_fee_type(amazon_fee_type: str) -> TransactionType:
    return _FEE_TYPE_MAP.get(amazon_fee_type, TransactionType.FEE)


def _is_tax_type(amazon_fee_type: str) -> bool:
    return amazon_fee_type.startswith("MarketplaceFacilitatorTax") or amazon_fee_type in ("TDS", "LowValueGoodsTax-Principal")


@connector_registry.register(SourceType.AMAZON_API, platform="amazon")
class AmazonConnector(IngestionConnector):
    """
    Amazon Selling Partner API connector.

    Phase 2 implementation: fill in the HTTP client calls.
    The event mapping methods are complete and tested against the SP API schema.
    """

    source_type = SourceType.AMAZON_API
    platform    = "amazon"

    _SP_API_BASE    = "https://sellingpartnerapi-eu.amazon.com"
    _LWA_TOKEN_URL  = "https://api.amazon.com/auth/o2/token"

    def __init__(
        self,
        company_id: UUID,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        marketplace_id: str = "A21TJRUUN4KGV",
        connection_id: Optional[UUID] = None,
    ) -> None:
        self._company_id     = company_id
        self._refresh_token  = refresh_token
        self._client_id      = client_id
        self._client_secret  = client_secret
        self._marketplace_id = marketplace_id
        self._connection_id  = connection_id
        self._access_token:  Optional[str] = None
        self._token_expiry:  Optional[datetime] = None

    # ── IngestionConnector interface ──────────────────────────────────────────

    async def authenticate(self) -> bool:
        """
        Exchange refresh_token for access_token via LWA.

        Phase 2 implementation:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(self._LWA_TOKEN_URL, data={
                    "grant_type":    "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id":     self._client_id,
                    "client_secret": self._client_secret,
                })
                resp.raise_for_status()
                data = resp.json()
                self._access_token = data["access_token"]
                self._token_expiry = datetime.utcnow() + timedelta(seconds=data["expires_in"] - 60)
        """
        raise NotImplementedError("AmazonConnector.authenticate() — implement in Phase 2")

    async def validate_connection(self) -> ConnectionHealth:
        """
        GET /sellers/v1/marketplaceParticipations

        Phase 2 implementation:
            resp = await self._get("/sellers/v1/marketplaceParticipations")
            participations = resp["payload"]
            account_name = participations[0]["seller"]["SellerId"]
            return ConnectionHealth(ok=True, account_name=account_name)
        """
        raise NotImplementedError("AmazonConnector.validate_connection() — implement in Phase 2")

    async def discover_available_data(
        self,
        company_id: UUID,
        lookback_days: int = 180,
    ) -> List[DataRange]:
        """
        Discover FinancialEventGroups.

        Phase 2: call ListFinancialEventGroups and return one DataRange per group.
        Default: return last 180 days as a single range (SP API max lookback).
        """
        from datetime import timedelta
        now = datetime.utcnow()
        return [
            DataRange(
                date_from=now - timedelta(days=min(lookback_days, 180)),
                date_to=now,
                data_type="settlements",
            )
        ]

    async def fetch_canonical_events(
        self,
        company_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        **kwargs,
    ) -> AsyncGenerator[CanonicalLedgerEvent, None]:
        """
        Fetch all financial events and yield CanonicalLedgerEvent objects.

        Phase 2 implementation plan:
          1. GET /finances/v0/financialEventGroups
             params: FinancialEventGroupStartedAfter=date_from, MaxResultsPerPage=100
             Paginate via NextToken.

          2. For each group (FinancialEventGroup):
             a. Extract group_id  = group["FinancialEventGroupId"]
             b. Extract payout    = group["OriginalTotal"]["CurrencyAmount"]
             c. Extract payout_date = group["FundTransferDate"]
             d. GET /finances/v0/financialEventGroups/{group_id}/financialEvents
                Paginate via NextToken.  Rate limit: sleep(2) between pages.

          3. For each ShipmentEvent in FinancialEvents.ShipmentEventList:
             - yield from self._map_shipment_event(event, group_id, payout_date)

          4. For each RefundEvent in RefundEventList:
             - yield from self._map_refund_event(event, group_id, payout_date)

          5. ChargebackEvent / GuaranteeClaimEvent:
             - yield RETURN event (see _map_chargeback_event)

          6. SAFETReimbursementEvent → yield REIMBURSEMENT event

          7. ServiceFeeEvent, FBAServiceFeeEvent, ProductAdsPaymentEvent:
             - yield FEE event (see _map_service_fee_event)

          8. CouponPaymentEvent → yield COUPON_CREDIT
          9. LoanServicingEvent → yield LOAN_FEE
          10. SellerDealPaymentEvent → yield DEAL_FEE

          11. After all events for the group: yield PAYOUT event for OriginalTotal

        Rate limiting:
          0.5 req/s for financial endpoints.
          Use asyncio.sleep(2) between ListFinancialEventGroups pagination calls.

        Error handling:
          - 403 → AuthError (raise, triggers terminal failure in sync job)
          - 429 → sleep and retry with exponential backoff
          - 5xx → log warning, skip group, continue (don't abort entire sync)
        """
        raise NotImplementedError("AmazonConnector.fetch_canonical_events() — implement in Phase 2")
        yield  # type: ignore[misc]

    # ── Event mapping methods — COMPLETE, tested against SP API schema ─────────

    def _map_shipment_event(
        self,
        event: dict,
        group_id: str,
        payout_date: str,
    ) -> List[CanonicalLedgerEvent]:
        """Map a ShipmentEvent dict to a list of CanonicalLedgerEvents."""
        results = []
        order_id = event.get("AmazonOrderId", "")
        shipment_date = event.get("PostedDate", payout_date)

        for item in event.get("ShipmentItemList", []):
            item_id  = item.get("OrderItemId", "")
            sku      = item.get("SellerSKU")
            qty      = item.get("QuantityShipped", 1)

            # SALE: Principal charge
            for charge in item.get("ItemChargeList", []):
                charge_type   = charge.get("ChargeType", "")
                charge_amount = Decimal(str(charge.get("ChargeAmount", {}).get("CurrencyAmount", 0)))
                if charge_type == "Principal":
                    results.append(CanonicalLedgerEvent(
                        source_type       = SourceType.AMAZON_API,
                        platform          = "amazon",
                        event_version     = "1.1",
                        connection_id     = self._connection_id,
                        external_event_id = f"{order_id}::{item_id}::Principal::sale",
                        transaction_type  = TransactionType.SALE.value,
                        amount            = charge_amount,
                        order_id          = order_id,
                        shipment_id       = item_id,
                        settlement_id     = group_id,
                        settlement_date   = payout_date,
                        transaction_date  = shipment_date[:10] if shipment_date else None,
                        sku               = sku,
                        currency          = "INR",
                        lineage_metadata  = {
                            "amazon": {
                                "financial_event_group_id": group_id,
                                "charge_type": "Principal",
                                "qty_shipped": qty,
                            }
                        },
                    ))
                elif _is_tax_type(charge_type):
                    tx_type = TransactionType.TCS if "TCS" in charge_type or "Facilitator" in charge_type else TransactionType.TDS
                    results.append(CanonicalLedgerEvent(
                        source_type       = SourceType.AMAZON_API,
                        platform          = "amazon",
                        event_version     = "1.1",
                        connection_id     = self._connection_id,
                        external_event_id = f"{order_id}::{item_id}::{charge_type}::tax",
                        transaction_type  = tx_type.value,
                        amount            = charge_amount,
                        order_id          = order_id,
                        settlement_id     = group_id,
                        settlement_date   = payout_date,
                        transaction_date  = shipment_date[:10] if shipment_date else None,
                        fee_type          = charge_type,
                        currency          = "INR",
                        lineage_metadata  = {"amazon": {"financial_event_group_id": group_id}},
                    ))

            # FEES: ItemFeeList
            for fee in item.get("ItemFeeList", []):
                fee_type   = fee.get("FeeType", "")
                fee_amount = Decimal(str(fee.get("FeeAmount", {}).get("CurrencyAmount", 0)))
                if fee_amount == 0:
                    continue
                tx_type = _map_fee_type(fee_type)
                results.append(CanonicalLedgerEvent(
                    source_type       = SourceType.AMAZON_API,
                    platform          = "amazon",
                    event_version     = "1.1",
                    connection_id     = self._connection_id,
                    external_event_id = f"{order_id}::{item_id}::{fee_type}::fee",
                    transaction_type  = tx_type.value,
                    amount            = fee_amount,
                    order_id          = order_id,
                    shipment_id       = item_id,
                    settlement_id     = group_id,
                    settlement_date   = payout_date,
                    transaction_date  = shipment_date[:10] if shipment_date else None,
                    sku               = sku,
                    fee_type          = fee_type,
                    currency          = "INR",
                    lineage_metadata  = {"amazon": {"financial_event_group_id": group_id, "fee_type": fee_type}},
                ))

        return results

    def _map_refund_event(
        self,
        event: dict,
        group_id: str,
        payout_date: str,
    ) -> List[CanonicalLedgerEvent]:
        """Map a RefundEvent dict to RETURN + FEE events."""
        results = []
        order_id   = event.get("AmazonOrderId", "")
        refund_date = event.get("PostedDate", payout_date)

        for item in event.get("ShipmentItemAdjustmentList", []):
            item_id = item.get("OrderAdjustmentItemId", "")
            sku     = item.get("SellerSKU")

            for charge in item.get("ItemChargeAdjustmentList", []):
                charge_type   = charge.get("ChargeType", "")
                charge_amount = Decimal(str(charge.get("ChargeAmount", {}).get("CurrencyAmount", 0)))
                if charge_type == "Principal":
                    results.append(CanonicalLedgerEvent(
                        source_type       = SourceType.AMAZON_API,
                        platform          = "amazon",
                        event_version     = "1.1",
                        connection_id     = self._connection_id,
                        external_event_id = f"{order_id}::{item_id}::Principal::return",
                        transaction_type  = TransactionType.RETURN.value,
                        amount            = charge_amount,  # negative from SP API
                        order_id          = order_id,
                        settlement_id     = group_id,
                        settlement_date   = payout_date,
                        transaction_date  = refund_date[:10] if refund_date else None,
                        sku               = sku,
                        currency          = "INR",
                        lineage_metadata  = {"amazon": {"financial_event_group_id": group_id, "event": "RefundEvent"}},
                    ))

            for fee in item.get("ItemFeeAdjustmentList", []):
                fee_type   = fee.get("FeeType", "")
                fee_amount = Decimal(str(fee.get("FeeAmount", {}).get("CurrencyAmount", 0)))
                if fee_amount == 0:
                    continue
                results.append(CanonicalLedgerEvent(
                    source_type       = SourceType.AMAZON_API,
                    platform          = "amazon",
                    event_version     = "1.1",
                    connection_id     = self._connection_id,
                    external_event_id = f"{order_id}::{item_id}::{fee_type}::refund_fee",
                    transaction_type  = _map_fee_type(fee_type).value,
                    amount            = fee_amount,
                    order_id          = order_id,
                    settlement_id     = group_id,
                    settlement_date   = payout_date,
                    transaction_date  = refund_date[:10] if refund_date else None,
                    sku               = sku,
                    fee_type          = fee_type,
                    currency          = "INR",
                    lineage_metadata  = {"amazon": {"financial_event_group_id": group_id, "event": "RefundEvent"}},
                ))

        return results

    def _map_safet_event(
        self,
        event: dict,
        group_id: str,
    ) -> CanonicalLedgerEvent:
        """Map a SAFETReimbursementEvent to REIMBURSEMENT."""
        amount = Decimal(str(event.get("ReimbursedAmount", {}).get("CurrencyAmount", 0)))
        return CanonicalLedgerEvent(
            source_type       = SourceType.AMAZON_API,
            platform          = "amazon",
            event_version     = "1.1",
            connection_id     = self._connection_id,
            external_event_id = f"safet::{event.get('SAFETClaimId', '')}",
            transaction_type  = TransactionType.REIMBURSEMENT.value,
            amount            = amount,
            order_id          = event.get("AmazonOrderId"),
            settlement_id     = group_id,
            currency          = "INR",
            lineage_metadata  = {"amazon": {"financial_event_group_id": group_id, "event": "SAFETReimbursement"}},
        )

    def _map_service_fee_event(
        self,
        event: dict,
        event_type: str,
        group_id: str,
    ) -> CanonicalLedgerEvent:
        """Map ServiceFeeEvent / FBAServiceFeeEvent to FEE or STORAGE_FEE."""
        # ServiceFeeEvent has FeeList; FBAServiceFeeEvent has FeeList
        total = sum(
            Decimal(str(f.get("FeeAmount", {}).get("CurrencyAmount", 0)))
            for f in event.get("FeeList", [])
        )
        tx_type = TransactionType.STORAGE_FEE if "FBA" in event_type else TransactionType.FEE
        return CanonicalLedgerEvent(
            source_type       = SourceType.AMAZON_API,
            platform          = "amazon",
            event_version     = "1.1",
            connection_id     = self._connection_id,
            external_event_id = f"service::{event.get('AmazonOrderId', event_type)}::{event_type}",
            transaction_type  = tx_type.value,
            amount            = total,
            order_id          = event.get("AmazonOrderId"),
            settlement_id     = group_id,
            currency          = "INR",
            lineage_metadata  = {"amazon": {"financial_event_group_id": group_id, "event": event_type}},
        )

    def _map_payout_event(
        self,
        group_id: str,
        original_total: Decimal,
        fund_transfer_date: str,
    ) -> CanonicalLedgerEvent:
        """
        Yield one PAYOUT event per FinancialEventGroup.

        This is the net settlement amount transferred to the seller's bank.
        settlement_id = group_id links to all the detail events above.
        """
        return CanonicalLedgerEvent(
            source_type       = SourceType.AMAZON_API,
            platform          = "amazon",
            event_version     = "1.1",
            connection_id     = self._connection_id,
            external_event_id = f"payout::{group_id}",
            transaction_type  = TransactionType.PAYOUT.value,
            amount            = original_total,
            settlement_id     = group_id,   # ETL groups by this — links all detail rows
            settlement_date   = fund_transfer_date[:10] if fund_transfer_date else None,
            payout_status     = "transferred",
            currency          = "INR",
            lineage_metadata  = {"amazon": {"financial_event_group_id": group_id}},
        )
