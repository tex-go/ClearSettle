"""
IngestionConnector — the single interface every data source must implement.

DESIGN RULES
------------
1.  A connector's ONLY job is to produce CanonicalLedgerEvent objects.
2.  Connectors must NOT write to the database directly.
3.  LedgerSyncExecutor owns all DB writes (ingestion_ledger + ETL).
4.  Adding a new marketplace = implement IngestionConnector, register it,
    and call LedgerSyncExecutor.run().  Nothing else changes.

IMPLEMENTATION GUIDE
--------------------
Minimal implementation (API connector):

    class AmazonConnector(IngestionConnector):
        source_type = SourceType.AMAZON_API
        platform    = "amazon"

        async def authenticate(self) -> bool:
            # refresh SP API tokens
            ...

        async def validate_connection(self) -> ConnectionHealth:
            # call GetMarketplaceParticipations
            ...

        async def fetch_canonical_events(
            self, company_id, date_from, date_to, **kwargs
        ) -> AsyncGenerator[CanonicalLedgerEvent, None]:
            async for order in self._sp_client.list_orders(date_from, date_to):
                for event in self._map_order(order):
                    yield event

Minimal implementation (file upload connector):

    class ManualUploadConnector(IngestionConnector):
        source_type = SourceType.MANUAL_UPLOAD

        async def fetch_canonical_events(...):
            pipeline_result, parse_result = run_ingestion_pipeline(...)
            for lr in parse_result.ledger_records:
                yield _to_canonical(lr, SourceType.MANUAL_UPLOAD, platform)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator, List, Optional
from uuid import UUID

from app.models.canonical.events import CanonicalLedgerEvent, SourceType


# ── Value objects ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ConnectionHealth:
    """Result of validate_connection()."""
    ok:              bool
    account_name:    Optional[str] = None
    marketplace_id:  Optional[str] = None
    message:         Optional[str] = None
    detail:          Optional[dict] = None


@dataclass(frozen=True)
class DataRange:
    """A contiguous block of data available from the source."""
    date_from:    datetime
    date_to:      datetime
    data_type:    str              # settlements | orders | fees | payouts
    record_count: Optional[int] = None
    extra:        Optional[dict] = None


# ── Abstract connector ────────────────────────────────────────────────────────

class IngestionConnector(ABC):
    """
    Base for every data source connector.

    Subclasses MUST set class attributes:
        source_type: SourceType  — which enum value identifies this connector
        platform:    str         — canonical platform slug (amazon, flipkart, …)

    Subclasses MUST implement:
        authenticate()           — refresh / obtain credentials
        validate_connection()    — health-check against the remote API / file
        fetch_canonical_events() — yield CanonicalLedgerEvent objects

    Subclasses MAY implement:
        discover_available_data() — tell the executor what date ranges exist
    """

    source_type: SourceType  # set on the class, not per-instance
    platform: str            # canonical slug

    # ── Required ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def authenticate(self) -> bool:
        """Ensure credentials are valid and not expired.

        Must be idempotent — safe to call even if already authenticated.
        Returns True on success, raises on unrecoverable failure.
        """

    @abstractmethod
    async def validate_connection(self) -> ConnectionHealth:
        """Make a lightweight remote call to verify the connection is live."""

    @abstractmethod
    async def fetch_canonical_events(
        self,
        company_id: UUID,
        date_from: datetime,
        date_to: datetime,
        **kwargs,
    ) -> AsyncGenerator[CanonicalLedgerEvent, None]:
        """
        Yield CanonicalLedgerEvent objects for the given date range.

        IMPORTANT: This is an async generator.  Use  `yield event`  not
        `return [events]`.  For large datasets (API pagination), yield
        each page's events before fetching the next — this provides
        progress visibility and allows the executor to write incrementally.

        Every event MUST have:
          - source_type matching self.source_type
          - platform matching self.platform
          - transaction_type from TransactionType enum
          - amount as Decimal (never None)
        """
        # satisfy the type checker; subclasses override
        return
        yield  # noqa: unreachable — makes this an async generator

    # ── Optional ──────────────────────────────────────────────────────────────

    async def discover_available_data(
        self,
        company_id: UUID,
        lookback_days: int = 90,
    ) -> List[DataRange]:
        """Return available data ranges.

        Default implementation returns a single range covering the last
        lookback_days.  Override for sources that have explicit report periods
        (e.g. Flipkart P&L reports cover specific settlement cycles).
        """
        from datetime import timedelta
        now = datetime.utcnow()
        return [
            DataRange(
                date_from=now - timedelta(days=lookback_days),
                date_to=now,
                data_type="all",
            )
        ]

    async def disconnect(self) -> None:
        """Clean up credentials / revoke tokens.  Optional."""
