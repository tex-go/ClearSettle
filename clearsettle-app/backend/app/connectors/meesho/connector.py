"""
MeeshoConnector — Meesho Partner API integration.

IMPLEMENTATION STATUS: SKELETON (Phase 4)

Meesho Partner API docs: https://partner.meesho.com/api-docs

Authentication:
    API key-based (no OAuth).
    Header: X-API-KEY: {api_key}

Key endpoints:
    POST /api/v2/orders  — paginated orders list
    POST /api/v2/payments/settlements — payment/settlement ledger

CANONICAL MAPPING
-----------------
Meesho API → CanonicalLedgerEvent.transaction_type:
    order_type == FORWARD  → SALE
    order_type == REVERSE  → RETURN (negative)
    fee_type == COMMISSION → COMMISSION
    fee_type == SHIPPING   → SHIPPING_FEE
    fee_type == REVERSE_PICKUP → REVERSE_SHIPPING
    TCS amount             → TCS
    Settlement payout      → PAYOUT
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, Optional
from uuid import UUID

from app.connectors.base import ConnectionHealth, IngestionConnector
from app.connectors.registry import connector_registry
from app.models.canonical.events import CanonicalLedgerEvent, SourceType

logger = logging.getLogger(__name__)


@connector_registry.register(SourceType.MEESHO_API, platform="meesho")
class MeeshoConnector(IngestionConnector):
    """
    Meesho Partner API connector.

    Constructor parameters:
        company_id    : UUID
        api_key       : Meesho partner API key (encrypted in DB)
        supplier_id   : Meesho supplier ID
        connection_id : FK to marketplace_connections.id
    """

    source_type = SourceType.MEESHO_API
    platform    = "meesho"

    _API_BASE = "https://partner-api.meesho.com"

    def __init__(
        self,
        company_id: UUID,
        api_key: str,
        supplier_id: str,
        connection_id: Optional[UUID] = None,
    ) -> None:
        self._company_id   = company_id
        self._api_key      = api_key
        self._supplier_id  = supplier_id
        self._connection_id = connection_id

    async def authenticate(self) -> bool:
        """
        Verify API key is present.  Meesho uses long-lived API keys; no refresh needed.
        Optionally: call /api/v1/supplier/profile to verify the key is valid.
        """
        return bool(self._api_key)

    async def validate_connection(self) -> ConnectionHealth:
        """
        Implementation:
            POST /api/v1/supplier/profile
            Headers: X-API-KEY: {api_key}
        """
        raise NotImplementedError("MeeshoConnector.validate_connection() not yet implemented")

    async def fetch_canonical_events(
        self,
        company_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        **kwargs,
    ) -> AsyncGenerator[CanonicalLedgerEvent, None]:
        """
        Implementation steps:
          1. POST /api/v2/orders
             Body: { start_date, end_date, page_no: 1, page_size: 500 }
             paginate while page_no * page_size < total_count
          2. For each sub_order_id in orders:
             - amount > 0 and type == FORWARD   → SALE
             - amount > 0 and type == REVERSE   → RETURN (negate amount)
             - commission                       → COMMISSION
             - shipping fees                    → SHIPPING_FEE
             - tcs_amount                       → TCS
          3. POST /api/v2/payments/settlements
             Body: { start_date, end_date }
             For each row → PAYOUT event (type=NEFT_CREDIT)
        """
        raise NotImplementedError("MeeshoConnector.fetch_canonical_events() not yet implemented")
        yield  # type: ignore[misc]
