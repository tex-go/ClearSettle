"""
Amazon SP API — Reports API v2021-06-30.

Lifecycle
---------
1. request_report()       → POST /reports  → returns reportId
2. poll_report_status()   → GET  /reports/{reportId}  → wait for DONE
3. get_report_document()  → GET  /reports/documents/{documentId}
4. download_document()    → GET  pre-signed S3 URL  → raw bytes

This module focuses on the *infrastructure* for reports.
The actual report parsers (settlement CSV, MTR, etc.) live in a future
reconciliation session.
"""
import logging
import time
from datetime import datetime
from typing import Optional

from app.services.amazon.constants import (
    DEFAULT_MARKETPLACE_ID,
    ReportStatus,
    ReportType,
)
from app.services.amazon.sp_api_client import SPAPIClient, SpApiError

logger = logging.getLogger(__name__)

REPORTS_BASE = "/reports/2021-06-30"

# Maximum time to wait for a report to become DONE before giving up
DEFAULT_POLL_TIMEOUT_SECONDS = 600   # 10 minutes
DEFAULT_POLL_INTERVAL_SECONDS = 30


# ── Request ───────────────────────────────────────────────────────────────────

def request_report(
    client: SPAPIClient,
    report_type: str,
    *,
    marketplace_ids: list[str] | None = None,
    data_start_time: Optional[datetime] = None,
    data_end_time:   Optional[datetime] = None,
    report_options:  Optional[dict]     = None,
) -> str:
    """
    Request a new report from Amazon.

    Args:
        client:          Authenticated SPAPIClient instance.
        report_type:     One of the ReportType constants.
        marketplace_ids: Defaults to [DEFAULT_MARKETPLACE_ID] (India).
        data_start_time: Optional date range start (UTC).
        data_end_time:   Optional date range end (UTC).
        report_options:  Platform-specific options dict.

    Returns:
        reportId string.

    Raises:
        SpApiError on failure.
    """
    body: dict = {
        "reportType":     report_type,
        "marketplaceIds": marketplace_ids or [DEFAULT_MARKETPLACE_ID],
    }
    if data_start_time:
        body["dataStartTime"] = data_start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    if data_end_time:
        body["dataEndTime"] = data_end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    if report_options:
        body["reportOptions"] = report_options

    data = client.post(f"{REPORTS_BASE}/reports", body)
    report_id = data.get("reportId", "")
    logger.info("Requested report type=%s → reportId=%s", report_type, report_id)
    return report_id


# ── Poll status ───────────────────────────────────────────────────────────────

def get_report_status(client: SPAPIClient, report_id: str) -> dict:
    """
    Fetch the current status of a report request.

    Returns the raw API response dict with keys:
      reportId, reportType, processingStatus, createdTime, etc.
    """
    return client.get(f"{REPORTS_BASE}/reports/{report_id}")


def wait_for_report(
    client:          SPAPIClient,
    report_id:       str,
    *,
    poll_interval:   int = DEFAULT_POLL_INTERVAL_SECONDS,
    timeout_seconds: int = DEFAULT_POLL_TIMEOUT_SECONDS,
) -> dict:
    """
    Block until the report reaches a terminal status (DONE, CANCELLED, FATAL).

    Returns the final status response dict.

    Raises:
        TimeoutError  — report did not complete within timeout_seconds.
        SpApiError    — if the report ends in FATAL or CANCELLED.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status_data  = get_report_status(client, report_id)
        status       = status_data.get("processingStatus", "")
        logger.debug("Report %s status: %s", report_id, status)

        if status == ReportStatus.DONE:
            return status_data

        if status in (ReportStatus.FATAL, ReportStatus.CANCELLED):
            raise SpApiError(
                f"Report {report_id} ended with status {status}",
                status_code=None,
            )

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Report {report_id} did not complete within {timeout_seconds}s"
    )


# ── Document retrieval ────────────────────────────────────────────────────────

def get_report_document_metadata(client: SPAPIClient, document_id: str) -> dict:
    """
    Fetch metadata for a report document, including the pre-signed download URL.

    Returns dict with: reportDocumentId, url, compressionAlgorithm (optional).
    """
    return client.get(f"{REPORTS_BASE}/documents/{document_id}")


def download_report_document(client: SPAPIClient, document_id: str) -> bytes:
    """
    Download the raw bytes of a report document.

    Steps:
      1. Fetch document metadata (pre-signed URL + optional compression info).
      2. Download from the pre-signed S3 URL.
      3. Decompress if compressionAlgorithm == "GZIP".

    Returns the raw (decompressed) report bytes.
    """
    meta = get_report_document_metadata(client, document_id)
    download_url = meta.get("url")
    if not download_url:
        raise SpApiError("Report document metadata missing 'url' field")

    raw_bytes = client.get_raw_bytes(download_url)

    if meta.get("compressionAlgorithm") == "GZIP":
        import gzip
        raw_bytes = gzip.decompress(raw_bytes)
        logger.debug("Decompressed GZIP report document (%d bytes)", len(raw_bytes))

    logger.info("Downloaded report document %s (%d bytes)", document_id, len(raw_bytes))
    return raw_bytes


# ── Convenience: full pipeline ────────────────────────────────────────────────

def request_and_download_report(
    client:          SPAPIClient,
    report_type:     str,
    *,
    marketplace_ids: list[str] | None = None,
    data_start_time: Optional[datetime] = None,
    data_end_time:   Optional[datetime] = None,
    report_options:  Optional[dict]     = None,
    poll_interval:   int = DEFAULT_POLL_INTERVAL_SECONDS,
    timeout_seconds: int = DEFAULT_POLL_TIMEOUT_SECONDS,
) -> bytes:
    """
    Full pipeline: request → poll until done → download.
    Returns the raw report bytes.
    """
    report_id   = request_report(
        client, report_type,
        marketplace_ids=marketplace_ids,
        data_start_time=data_start_time,
        data_end_time=data_end_time,
        report_options=report_options,
    )
    status_data = wait_for_report(client, report_id, poll_interval=poll_interval, timeout_seconds=timeout_seconds)
    document_id = status_data.get("reportDocumentId", "")
    if not document_id:
        raise SpApiError(f"Report {report_id} done but no reportDocumentId in response")

    return download_report_document(client, document_id)
