"""
ManualUploadConnector — wraps the existing file-parse pipeline and converts
parser output into CanonicalLedgerEvent objects.

This connector makes manual file upload a first-class citizen of the connector
framework.  It uses the exact same pipeline as every future API connector:

    ManualUploadConnector
    ↓ fetch_canonical_events()
    ↓ yield CanonicalLedgerEvent
    ↓ LedgerSyncExecutor
    ↓ ingestion_ledger
    ↓ ETL
    ↓ settlements / payout_events / dashboard

No code is duplicated.  The existing parse pipeline (fingerprint → detect →
parse → ledger records) produces the raw data; this connector normalises it
into the canonical model.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, Optional
from uuid import UUID

from app.connectors.base import ConnectionHealth, IngestionConnector
from app.models.canonical.events import CanonicalLedgerEvent, SourceType

logger = logging.getLogger(__name__)


class ManualUploadConnector(IngestionConnector):
    """
    Connector for manually uploaded Excel / CSV files.

    Constructor arguments match the existing ingestion router so the transition
    is drop-in.  The router creates one of these, passes it to LedgerSyncExecutor,
    and the rest of the pipeline is identical to any API connector.
    """

    source_type = SourceType.MANUAL_UPLOAD

    def __init__(
        self,
        file_bytes: bytes,
        file_name: str,
        uploaded_file_id: Optional[UUID] = None,
        platform_hint: Optional[str] = None,
        report_type_hint: Optional[str] = None,
    ) -> None:
        self._file_bytes       = file_bytes
        self._file_name        = file_name
        self._uploaded_file_id = uploaded_file_id
        self._platform_hint    = platform_hint
        self._report_type_hint = report_type_hint

        # Determined after fetch_canonical_events() runs
        self.detected_platform:    Optional[str] = None
        self.detected_report_type: Optional[str] = None
        self.detected_parser:      Optional[str] = None
        self.confidence_score:     float = 0.0
        self.needs_manual_review:  bool = False
        self.schema_version:       Optional[str] = None
        self.detection_metadata:   dict = {}
        self.pipeline_errors:      list = []
        self.pipeline_warnings:    list = []

    @property
    def platform(self) -> str:  # type: ignore[override]
        return self.detected_platform or self._platform_hint or "unknown"

    # ── IngestionConnector interface ──────────────────────────────────────────

    async def authenticate(self) -> bool:
        # File uploads require no remote authentication.
        return True

    async def validate_connection(self) -> ConnectionHealth:
        if not self._file_bytes:
            return ConnectionHealth(ok=False, message="No file bytes provided")
        return ConnectionHealth(
            ok=True,
            message=f"File ready: {self._file_name} ({len(self._file_bytes)} bytes)",
        )

    async def fetch_canonical_events(
        self,
        company_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        **kwargs,
    ) -> AsyncGenerator[CanonicalLedgerEvent, None]:
        """
        Run the existing detection + parse pipeline synchronously (it's CPU-bound)
        and yield each parsed row as a CanonicalLedgerEvent.

        The pipeline does:
          1. Fingerprint file (sheet names, column names, signatures)
          2. Detect platform with confidence score
          3. Detect report type and schema version
          4. Route to the correct parser (Flipkart/Amazon/Meesho/Generic)
          5. Normalise rows into LedgerRecord objects

        This connector then converts LedgerRecord → CanonicalLedgerEvent.
        """
        from app.services.pipeline.router import run_ingestion_pipeline

        logger.info(
            "ManualUploadConnector.fetch_canonical_events",
            extra={
                "file_name":          self._file_name,
                "file_bytes":         len(self._file_bytes),
                "platform_hint":      self._platform_hint,
                "report_type_hint":   self._report_type_hint,
                "uploaded_file_id":   str(self._uploaded_file_id) if self._uploaded_file_id else None,
            },
        )

        pipeline_result, parse_result = run_ingestion_pipeline(
            self._file_bytes,
            self._file_name,
            self._uploaded_file_id,
            platform_hint=self._platform_hint,
            report_type_hint=self._report_type_hint,
        )

        # Store pipeline metadata — caller (LedgerSyncExecutor / ingestion router)
        # writes these to report_detection_results
        self.detected_platform    = pipeline_result.platform
        self.detected_report_type = pipeline_result.report_type
        self.detected_parser      = pipeline_result.parser_name
        self.confidence_score     = pipeline_result.confidence_score
        self.needs_manual_review  = pipeline_result.needs_manual_review
        self.schema_version       = pipeline_result.schema_version
        self.detection_metadata   = pipeline_result.detection_metadata or {}
        self.pipeline_errors      = pipeline_result.errors or []
        self.pipeline_warnings    = pipeline_result.warnings or []

        if parse_result is None or parse_result.is_empty:
            logger.warning(
                "ManualUploadConnector: parser returned no records",
                extra={
                    "file_name":  self._file_name,
                    "platform":   pipeline_result.platform,
                    "parser":     pipeline_result.parser_name,
                    "errors":     pipeline_result.errors[:3] if pipeline_result.errors else [],
                },
            )
            return

        plat = (pipeline_result.platform or "unknown").lower()

        for lr in parse_result.ledger_records:
            row_num = lr.source_row_number
            # external_event_id is "row_{N}" for manual uploads.
            # This makes LedgerSyncExecutor idempotent: reprocessing the same file
            # first deletes old rows (reprocess endpoint), then re-inserts with the
            # same key — no duplicates even if the conflict path triggers.
            ext_id = f"row_{row_num}" if row_num is not None else None

            yield CanonicalLedgerEvent(
                # Provenance
                source_type        = SourceType.MANUAL_UPLOAD,
                platform           = plat,
                event_version      = "1.1",
                uploaded_file_id   = self._uploaded_file_id,
                connection_id      = None,
                sync_job_id        = None,
                # Idempotency
                external_event_id  = ext_id,
                # Frozen financial fields
                transaction_type   = lr.transaction_type or "adjustment",
                amount             = Decimal(str(lr.amount)) if lr.amount is not None else Decimal("0"),
                order_id           = lr.order_id,
                shipment_id        = lr.shipment_id,
                settlement_id      = lr.settlement_id,
                invoice_id         = getattr(lr, "invoice_id", None),
                currency           = lr.currency or "INR",
                transaction_date   = lr.transaction_date,
                settlement_date    = lr.settlement_date,
                # Extended
                sku                = lr.sku,
                product_title      = lr.product_title,
                category           = lr.category,
                fee_type           = lr.fee_type,
                tax_amount         = Decimal(str(lr.tax_amount)) if lr.tax_amount is not None else None,
                return_status      = lr.return_status,
                payout_status      = lr.payout_status,
                report_type        = pipeline_result.report_type,
                source_row_number  = lr.source_row_number,
                lineage_metadata   = lr.lineage_metadata,
            )
