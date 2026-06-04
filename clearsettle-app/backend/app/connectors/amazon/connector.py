"""
AmazonConnector — Amazon Selling Partner API integration.

IMPLEMENTATION STATUS: SKELETON (Phase 2)

This file defines the complete interface contract.  Wire up the actual SP API
client in Phase 2.  Every method has a docstring explaining exactly what must
be implemented.

SP API Scope required:
    Finances_Listings  (ListFinancialEventGroups, ListFinancialEvents)
    Orders             (GetOrders — for order metadata enrichment)
    Reports            (future: settlement reports as file download)

SP API rate limits:
    ListFinancialEventGroups — 0.5 req/s, burst 30
    ListFinancialEvents      — 0.5 req/s, burst 30
    GetOrders                — 0.0167 req/s, burst 20

All amounts from SP API are in USD by default; the connector must convert to
the currency stored in PlatformConnection (INR for Indian sellers using
IN marketplace).

CANONICAL MAPPING
-----------------
SP API FinancialEvent types → CanonicalLedgerEvent.transaction_type:
  ShipmentEvent  (Principal) → SALE
  RefundEvent    (Principal) → RETURN
  ChargebackEvent            → RETURN (negative)
  FBAServiceFeeEvent         → FEE
  ProductAdsPaymentEvent     → FEE
  ServiceFeeEvent            → FEE
  TaxWithheldComponent (TCS) → TCS
  TaxWithheldComponent (TDS) → TDS
  PayWithAmazonEvent         → PAYOUT
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, Optional
from uuid import UUID

from app.connectors.base import ConnectionHealth, IngestionConnector
from app.connectors.registry import connector_registry
from app.models.canonical.events import CanonicalLedgerEvent, SourceType, TransactionType

logger = logging.getLogger(__name__)


@connector_registry.register(SourceType.AMAZON_API, platform="amazon")
class AmazonConnector(IngestionConnector):
    """
    Amazon Selling Partner API connector.

    Constructor parameters (all come from PlatformConnection / MarketplaceCredentials):
        company_id          : UUID for tenant isolation
        refresh_token       : SP API refresh token (Fernet-encrypted in DB)
        client_id           : LWA app client ID
        client_secret       : LWA app client secret
        marketplace_id      : e.g. "A21TJRUUN4KGV" for Amazon.in
        connection_id       : FK to marketplace_connections.id (for logging)
    """

    source_type = SourceType.AMAZON_API
    platform    = "amazon"

    # SP API endpoint base URLs
    _SP_API_BASE = "https://sellingpartnerapi-eu.amazon.com"
    _LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    def __init__(
        self,
        company_id: UUID,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        marketplace_id: str = "A21TJRUUN4KGV",  # Amazon.in
        connection_id: Optional[UUID] = None,
    ) -> None:
        self._company_id    = company_id
        self._refresh_token = refresh_token
        self._client_id     = client_id
        self._client_secret = client_secret
        self._marketplace_id = marketplace_id
        self._connection_id = connection_id
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    # ── IngestionConnector interface ──────────────────────────────────────────

    async def authenticate(self) -> bool:
        """
        Exchange refresh_token for a short-lived access token via LWA.

        Implementation:
            POST https://api.amazon.com/auth/o2/token
            Body: grant_type=refresh_token, refresh_token=..., client_id=..., client_secret=...
            Response: { access_token, expires_in }

        Store access_token + expiry in self._access_token / self._token_expiry.
        Returns True on success; raises on auth failure (no retry — expired token
        needs re-authorisation by the user).
        """
        # TODO Phase 2: implement LWA token refresh
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     resp = await client.post(self._LWA_TOKEN_URL, data={...})
        #     resp.raise_for_status()
        #     data = resp.json()
        #     self._access_token = data["access_token"]
        #     self._token_expiry = datetime.utcnow() + timedelta(seconds=data["expires_in"] - 60)
        raise NotImplementedError("AmazonConnector.authenticate() not yet implemented")

    async def validate_connection(self) -> ConnectionHealth:
        """
        Call GetMarketplaceParticipations to verify the token is valid.

        Implementation:
            GET /sellers/v1/marketplaceParticipations
            Headers: x-amz-access-token: {access_token}

        Returns ConnectionHealth(ok=True, account_name=seller_name) on success.
        """
        # TODO Phase 2: call GetMarketplaceParticipations
        raise NotImplementedError("AmazonConnector.validate_connection() not yet implemented")

    async def fetch_canonical_events(
        self,
        company_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        **kwargs,
    ) -> AsyncGenerator[CanonicalLedgerEvent, None]:
        """
        Fetch financial events via ListFinancialEventGroups + ListFinancialEvents.

        Implementation steps:
          1. GET /finances/v0/financialEventGroups
             params: FinancialEventGroupStartedAfter=date_from, MaxResultsPerPage=100
             paginate via NextToken
          2. For each group: GET /finances/v0/financialEventGroups/{id}/financialEvents
             paginate via NextToken
          3. For each ShipmentItem in ShipmentEventList → yield SALE event
          4. For each RefundItem in RefundEventList → yield RETURN event
          5. For each FeeComponent in ServiceFeeEventList → yield FEE event
          6. For each TaxWithheldEvent in TaxWithholdingEventList → yield TCS/TDS event
          7. For each group with OriginalTotal → yield PAYOUT event (one per group)

        Pagination note:
          Always yield events from one page before fetching the next — the
          executor writes in batches, which provides progress visibility for
          large datasets.

        Rate limiting:
          0.5 req/s for financial endpoints.  Use asyncio.sleep(2) between pages.

        Currency:
          SP API amounts are in the settlement currency.  Indian sellers settle
          in INR.  Check ItemChargeList[].ChargeAmount.CurrencyCode — if not INR,
          apply conversion rate (store in lineage_metadata for auditability).
        """
        # TODO Phase 2: implement SP API financial event pagination
        raise NotImplementedError("AmazonConnector.fetch_canonical_events() not yet implemented")
        yield  # type: ignore[misc]

    # ── Private SP API helpers (implement in Phase 2) ─────────────────────────

    def _map_shipment_item_to_event(
        self,
        item: dict,
        order_id: str,
        settlement_id: str,
        settlement_date: str,
    ) -> CanonicalLedgerEvent:
        """Map a ShipmentItem from SP API to a CanonicalLedgerEvent with SALE type."""
        # Charges: ItemChargeList where ChargeType == "Principal"
        principal = Decimal("0")
        for charge in item.get("ItemChargeList", []):
            if charge.get("ChargeType") == "Principal":
                principal += Decimal(str(charge.get("ChargeAmount", {}).get("CurrencyAmount", 0)))

        return CanonicalLedgerEvent(
            source_type      = SourceType.AMAZON_API,
            platform         = "amazon",
            connection_id    = self._connection_id,
            transaction_type = TransactionType.SALE.value,
            amount           = principal,
            order_id         = order_id,
            settlement_id    = settlement_id,
            settlement_date  = settlement_date,
            sku              = item.get("SellerSKU"),
            currency         = "INR",
            lineage_metadata = {"raw_item_type": "ShipmentItem"},
        )

    def _map_fee_to_event(
        self,
        fee: dict,
        order_id: str,
        settlement_id: str,
    ) -> CanonicalLedgerEvent:
        """Map an ItemFeeList entry to a CanonicalLedgerEvent with FEE type."""
        return CanonicalLedgerEvent(
            source_type      = SourceType.AMAZON_API,
            platform         = "amazon",
            connection_id    = self._connection_id,
            transaction_type = TransactionType.FEE.value,
            amount           = Decimal(str(fee.get("FeeAmount", {}).get("CurrencyAmount", 0))),
            order_id         = order_id,
            settlement_id    = settlement_id,
            fee_type         = fee.get("FeeType"),
            currency         = "INR",
            lineage_metadata = {"raw_fee_type": fee.get("FeeType")},
        )
