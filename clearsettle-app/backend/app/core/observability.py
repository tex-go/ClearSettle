"""
ClearSettle Observability — standardised structured logging contract.

EVERY log line emitted during ingestion, sync, or ETL MUST include at minimum:
    company_id, source_type, platform

EVERY log line inside a connector run MUST also include:
    connection_id OR uploaded_file_id

EVERY log line inside LedgerSyncExecutor MUST include:
    uploaded_file_id, events_written (at completion)

Usage
-----
    from app.core.observability import ingestion_log, sync_log, etl_log

    logger.info("Step complete", extra=ingestion_log(
        upload_id=str(file_id),
        company_id=str(company_id),
        source_type="manual_upload",
        platform="flipkart",
        stage="parse",
        status="success",
        record_count=412,
    ))

Cloud Logging filter examples (paste into GCP Log Explorer)
------------------------------------------------------------

1. All ingestion events for a company:
    resource.type="gce_instance"
    jsonPayload.company_id="<UUID>"
    jsonPayload.stage=~"^INGESTION"

2. All failed API syncs in last 24h:
    resource.type="gce_instance"
    jsonPayload.source_type!="manual_upload"
    jsonPayload.status="failed"
    timestamp>"-24h"

3. Sync events for a specific connection:
    resource.type="gce_instance"
    jsonPayload.connection_id="<UUID>"

4. All ETL errors:
    resource.type="gce_instance"
    jsonPayload.stage="etl"
    severity="ERROR"

5. Events where external_event_id conflict triggered (idempotency):
    resource.type="gce_instance"
    jsonPayload.idempotent_skipped>0

6. Slow ingestions (>10s):
    resource.type="gce_instance"
    jsonPayload.duration_ms>10000
    jsonPayload.stage="complete"

Cloud Monitoring alert policies
---------------------------------
Metric: logging/user/clearsettle_ingestion_failures
  Filter: jsonPayload.status="failed" AND jsonPayload.stage="ingestion"
  Threshold: > 5 in 5 minutes → PagerDuty

Metric: logging/user/clearsettle_etl_failures
  Filter: jsonPayload.stage="etl" AND severity="ERROR"
  Threshold: > 2 in 10 minutes → PagerDuty

Metric: logging/user/clearsettle_slow_ingestion
  Filter: jsonPayload.duration_ms>30000
  Threshold: > 10 in 1 hour → Slack alert

Error Reporting
---------------
GCP Error Reporting automatically groups stack traces from Cloud Run.
Tag every exception with the correlation fields using exc_info=True:

    logger.error("Ingestion failed", extra={...CORRELATION_FIELDS...}, exc_info=True)

This makes Error Reporting link each crash to its company_id + upload_id.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# ── Standard correlation field set ───────────────────────────────────────────

def ingestion_log(
    *,
    upload_id: Optional[str] = None,
    company_id: Optional[str] = None,
    source_type: Optional[str] = None,
    platform: Optional[str] = None,
    connection_id: Optional[str] = None,
    sync_job_id: Optional[str] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    record_count: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Build a structured log dict for ingestion pipeline events.

    All fields are optional so callers can pass only what they have at each stage.
    """
    fields: Dict[str, Any] = {}
    if upload_id:      fields["upload_id"]    = upload_id
    if company_id:     fields["company_id"]   = company_id
    if source_type:    fields["source_type"]  = source_type
    if platform:       fields["platform"]     = platform
    if connection_id:  fields["connection_id"] = connection_id
    if sync_job_id:    fields["sync_job_id"]  = sync_job_id
    if stage:          fields["stage"]        = stage
    if status:         fields["status"]       = status
    if record_count is not None: fields["record_count"] = record_count
    if duration_ms  is not None: fields["duration_ms"]  = duration_ms
    fields.update(extra)
    return fields


def sync_log(
    *,
    connection_id: str,
    company_id: str,
    platform: str,
    source_type: str,
    sync_job_id: Optional[str] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    events_total: Optional[int] = None,
    events_written: Optional[int] = None,
    events_skipped: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Standard log fields for API sync jobs."""
    fields: Dict[str, Any] = {
        "connection_id": connection_id,
        "company_id":    company_id,
        "platform":      platform,
        "source_type":   source_type,
    }
    if sync_job_id:          fields["sync_job_id"]     = sync_job_id
    if stage:                fields["stage"]           = stage
    if status:               fields["status"]          = status
    if events_total    is not None: fields["events_total"]    = events_total
    if events_written  is not None: fields["events_written"]  = events_written
    if events_skipped  is not None: fields["events_skipped"]  = events_skipped
    if duration_ms     is not None: fields["duration_ms"]     = duration_ms
    fields.update(extra)
    return fields


def etl_log(
    *,
    upload_id: str,
    company_id: str,
    platform: str,
    stage: str = "etl",
    status: Optional[str] = None,
    settlements_created: Optional[int] = None,
    settlements_updated: Optional[int] = None,
    payouts_upserted:    Optional[int] = None,
    ledger_rows:         Optional[int] = None,
    duration_ms:         Optional[float] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Standard log fields for ETL runs."""
    fields: Dict[str, Any] = {
        "upload_id":  upload_id,
        "company_id": company_id,
        "platform":   platform,
        "stage":      stage,
    }
    if status:                    fields["status"]               = status
    if settlements_created is not None: fields["settlements_created"] = settlements_created
    if settlements_updated is not None: fields["settlements_updated"] = settlements_updated
    if payouts_upserted    is not None: fields["payouts_upserted"]    = payouts_upserted
    if ledger_rows         is not None: fields["ledger_rows"]         = ledger_rows
    if duration_ms         is not None: fields["duration_ms"]         = duration_ms
    fields.update(extra)
    return fields


# ── GCP Cloud Logging structured log format ───────────────────────────────────
# When running on Cloud Run / GCE with the GCP logging handler configured,
# every field in `extra={}` becomes a top-level key in jsonPayload.
# The standard Python logging handler writes:
#   {
#     "severity": "INFO",
#     "message": "INGESTION[3/5] LedgerSyncExecutor complete",
#     "upload_id": "...",
#     "company_id": "...",
#     "source_type": "manual_upload",
#     "platform": "flipkart",
#     "events_written": 412,
#     "duration_ms": 1240.5
#   }
#
# This makes all fields queryable in Log Explorer without log-based metric extraction.
#
# Setup in logging_setup.py:
#   from google.cloud.logging_v2.handlers import CloudLoggingHandler
#   handler = CloudLoggingHandler(client)
#   handler.setFormatter(StructuredLogFormatter())  # custom formatter that flattens `extra`
