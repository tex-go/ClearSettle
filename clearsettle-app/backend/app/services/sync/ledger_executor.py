"""
LedgerSyncExecutor — the universal ingestion worker.

This is the single code path that turns CanonicalLedgerEvent objects into
database rows, regardless of source.

Flow:
    connector.fetch_canonical_events()
    ↓ yield CanonicalLedgerEvent (one per transaction row)
    ↓ write to ingestion_ledger (batch)
    ↓ run_ledger_etl()  →  settlements + payout_events
    ↓ return ConnectorResult

Adding a new marketplace requires ONLY implementing IngestionConnector.
This executor, the ETL, the dashboard, and the mobile app never change.

STABILITY CONTRACT
------------------
The executor writes these fields from CanonicalLedgerEvent into IngestionLedger:
  - All FROZEN fields (transaction_type, amount, order_id, settlement_id, …)
  - Provenance fields (source_type, connection_id, sync_job_id, uploaded_file_id)

The ETL (ledger_etl.py) only reads FROZEN fields.  Provenance fields are for
traceability and never affect financial calculations.
"""
from __future__ import annotations

import logging
import time
import uuid
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import IngestionConnector
from app.db.models.ingestion import IngestionLedger, ReportProcessingLog
from app.models.canonical.events import CanonicalLedgerEvent, ConnectorResult, SourceType
from app.services.etl import run_ledger_etl

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500   # rows per DB commit during streaming ingestion


class LedgerSyncExecutor:
    """
    Executes a connector, writes its events to ingestion_ledger, runs ETL.

    Thread safety: one instance per execution — do not share across concurrent requests.
    """

    async def run(
        self,
        *,
        connector: IngestionConnector,
        company_id: UUID,
        db: AsyncSession,
        uploaded_file_id: Optional[UUID] = None,
        connection_id: Optional[UUID] = None,
        sync_job_id: Optional[UUID] = None,
        date_from=None,
        date_to=None,
        run_etl: bool = True,
    ) -> ConnectorResult:
        """
        Run the full ingestion cycle for one connector invocation.

        Parameters
        ----------
        connector         : The IngestionConnector to drain events from.
        company_id        : Tenant isolation boundary.
        db                : Open async SQLAlchemy session.
        uploaded_file_id  : Set when source_type=manual_upload.
        connection_id     : Set when source_type=*_api.
        sync_job_id       : Set when triggered by scheduled sync.
        date_from/date_to : Passed to connector.fetch_canonical_events().
        run_etl           : Run ledger_etl after writing (default True).
                            Set False in tests or when replaying a single step.
        """
        t_start = time.perf_counter()
        from datetime import datetime, timedelta

        if date_from is None:
            date_from = datetime.utcnow() - timedelta(days=90)
        if date_to is None:
            date_to = datetime.utcnow()

        result = ConnectorResult(
            source_type=connector.source_type,
            platform=connector.platform,
        )
        fid = str(uploaded_file_id) if uploaded_file_id else "—"
        cid_log = str(connection_id) if connection_id else "—"

        logger.info(
            "LedgerSyncExecutor.run start",
            extra={
                "source_type":       connector.source_type.value,
                "platform":          connector.platform,
                "company_id":        str(company_id),
                "uploaded_file_id":  fid,
                "connection_id":     cid_log,
                "sync_job_id":       str(sync_job_id) if sync_job_id else "—",
                "date_from":         date_from.isoformat(),
                "date_to":           date_to.isoformat(),
            },
        )

        # ── Authenticate ──────────────────────────────────────────────────────
        try:
            ok = await connector.authenticate()
            if not ok:
                result.errors.append("Authentication failed")
                return result
        except Exception as exc:
            result.errors.append(f"Authentication error: {exc}")
            logger.error(
                "LedgerSyncExecutor authenticate failed",
                extra={"source_type": connector.source_type.value, "error": str(exc)},
                exc_info=True,
            )
            return result

        # ── Stream and write events in batches ────────────────────────────────
        batch: list[IngestionLedger] = []
        written = 0
        skipped = 0

        try:
            async for event in connector.fetch_canonical_events(
                company_id=company_id,
                date_from=date_from,
                date_to=date_to,
            ):
                result.events_total += 1
                row = self._to_ledger_row(
                    event,
                    company_id=company_id,
                    uploaded_file_id=uploaded_file_id,
                    connection_id=connection_id,
                    sync_job_id=sync_job_id,
                )
                if row is None:
                    skipped += 1
                    continue
                batch.append(row)

                if len(batch) >= _BATCH_SIZE:
                    written += await self._flush(db, batch, fid)
                    batch.clear()

            # flush remainder
            if batch:
                written += await self._flush(db, batch, fid)

        except Exception as exc:
            msg = f"Event stream error: {exc!s:.300}"
            result.errors.append(msg)
            logger.error(
                "LedgerSyncExecutor stream error",
                extra={
                    "source_type":      connector.source_type.value,
                    "uploaded_file_id": fid,
                    "events_so_far":    result.events_total,
                    "error":            str(exc)[:300],
                },
                exc_info=True,
            )
            # Don't abort: partial data is still useful; ETL will run below

        result.events_written = written
        result.events_skipped = skipped

        logger.info(
            "LedgerSyncExecutor events written",
            extra={
                "source_type":      connector.source_type.value,
                "uploaded_file_id": fid,
                "events_total":     result.events_total,
                "events_written":   written,
                "events_skipped":   skipped,
            },
        )

        # ── Run ETL ───────────────────────────────────────────────────────────
        if run_etl and written > 0 and uploaded_file_id:
            try:
                etl_summary = await run_ledger_etl(
                    db=db,
                    uploaded_file_id=uploaded_file_id,
                    company_id=company_id,
                    platform=connector.platform,
                )
                result.settlements_created = etl_summary.get("settlements_created", 0)
                result.settlements_updated = etl_summary.get("settlements_updated", 0)
                result.payouts_upserted    = etl_summary.get("payouts_upserted", 0)
            except Exception as etl_exc:
                warn = f"ETL error (non-fatal): {etl_exc!s:.200}"
                result.warnings.append(warn)
                logger.error(
                    "LedgerSyncExecutor ETL failed",
                    extra={
                        "uploaded_file_id": fid,
                        "error": str(etl_exc)[:300],
                    },
                    exc_info=True,
                )

        result.duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
        logger.info(
            "LedgerSyncExecutor.run complete",
            extra={
                "source_type":       connector.source_type.value,
                "platform":          connector.platform,
                "events_written":    result.events_written,
                "settlements_created": result.settlements_created,
                "errors":            len(result.errors),
                "duration_ms":       result.duration_ms,
            },
        )
        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _to_ledger_row(
        event: CanonicalLedgerEvent,
        company_id: UUID,
        uploaded_file_id: Optional[UUID],
        connection_id: Optional[UUID],
        sync_job_id: Optional[UUID],
    ) -> Optional[IngestionLedger]:
        """Convert a CanonicalLedgerEvent to an IngestionLedger ORM row."""
        try:
            # Use provenance from the event, fall back to executor-level values
            ev_file_id = event.uploaded_file_id or uploaded_file_id
            ev_conn_id = event.connection_id or connection_id
            ev_job_id  = event.sync_job_id  or sync_job_id

            if ev_file_id is None:
                # API connectors that don't create an UploadedFile record must
                # pass uploaded_file_id at the executor level — raise rather than
                # silently dropping rows.
                raise ValueError(
                    "uploaded_file_id required in LedgerSyncExecutor.run() "
                    "when connector.source_type != manual_upload"
                )

            return IngestionLedger(
                id=uuid.uuid4(),
                uploaded_file_id=ev_file_id,
                company_id=company_id,
                # Provenance
                source_type=event.source_type.value,
                connection_id=ev_conn_id,
                sync_job_id=ev_job_id,
                # Frozen financial fields
                platform=event.platform,
                report_type=event.report_type,
                order_id=event.order_id,
                shipment_id=event.shipment_id,
                settlement_id=event.settlement_id,
                invoice_id=event.invoice_id,
                sku=event.sku,
                product_title=event.product_title,
                category=event.category,
                transaction_type=event.transaction_type,
                fee_type=event.fee_type,
                amount=event.amount,
                tax_amount=event.tax_amount,
                currency=event.currency,
                transaction_date=event.transaction_date,
                settlement_date=event.settlement_date,
                return_status=event.return_status,
                payout_status=event.payout_status,
                source_row_number=event.source_row_number,
                lineage_metadata=event.lineage_metadata,
            )
        except Exception as exc:
            logger.warning(
                "LedgerSyncExecutor: skipping malformed event",
                extra={"error": str(exc)[:200], "event_tx_type": event.transaction_type},
            )
            return None

    @staticmethod
    async def _flush(
        db: AsyncSession,
        batch: list[IngestionLedger],
        fid: str,
    ) -> int:
        for row in batch:
            db.add(row)
        await db.commit()
        logger.debug(
            "LedgerSyncExecutor batch flushed",
            extra={"count": len(batch), "uploaded_file_id": fid},
        )
        return len(batch)
