"""
Pipeline Router.

Orchestrates the full ingestion pipeline for a single uploaded file:

  File bytes
    ↓ fingerprint_file()       → FileFingerprint
    ↓ detect_platform()        → PlatformDetectionResult
    ↓ detect_report_type()     → ReportTypeResult
    ↓ detect_schema_version()  → SchemaDetectionResult
    ↓ get_parser()             → BaseParser instance
    ↓ parser.parse()           → ParseResult (LedgerRecord list)
    ↓ (async) persist to DB    → ingestion_ledger rows + processing_logs

run_ingestion_pipeline() is called from the FastAPI background task.
It is NOT async (the heavy parsing is CPU-bound); the caller wraps
the DB writes in an async session.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    uploaded_file_id:    UUID
    platform:            str
    report_type:         str
    schema_version:      str
    parser_name:         str
    confidence_score:    float
    needs_manual_review: bool
    ledger_count:        int
    recon_issue_count:   int
    errors:              List[str]              = field(default_factory=list)
    warnings:            List[str]              = field(default_factory=list)
    drift_alert:         Optional[Dict[str, Any]] = None
    detection_metadata:  Dict[str, Any]         = field(default_factory=dict)


def run_ingestion_pipeline(
    file_bytes: bytes,
    file_name:  str,
    uploaded_file_id: UUID,
    *,
    quarter_label: str = "unknown",
) -> PipelineResult:
    """
    Execute the full detection → parse pipeline synchronously.
    Returns a PipelineResult with all metadata needed to persist to DB.

    Does NOT write to the database — the caller (background task) handles
    async DB writes using the PipelineResult data.
    """
    from app.services.detection.fingerprinter     import fingerprint_file
    from app.services.detection.platform_detector import detect_platform
    from app.services.detection.report_type_detector import detect_report_type
    from app.services.detection.schema_detector   import detect_schema_version
    from app.services.parsers.registry            import get_parser

    logs: List[Dict[str, Any]] = []

    def _log(level: str, stage: str, msg: str, ctx: Dict = None):
        logs.append({"level": level, "stage": stage, "message": msg, "context": ctx or {}})
        getattr(logger, level, logger.info)(msg)

    # ── Stage 1: Fingerprint ──────────────────────────────────────────────────
    _log("info", "fingerprint", f"Fingerprinting '{file_name}' ({len(file_bytes):,} bytes)")
    try:
        fp = fingerprint_file(file_bytes, file_name)
    except Exception as exc:
        _log("error", "fingerprint", f"Fingerprinting failed: {exc}")
        return _failed(uploaded_file_id, str(exc), logs)

    for w in fp.parse_warnings:
        _log("warning", "fingerprint", w)

    _log("info", "fingerprint", (
        f"Fingerprint complete: {len(fp.sheets)} sheet(s), "
        f"{len(fp.all_column_names)} unique columns, sig={fp.schema_signature[:12]}…"
    ), {"sheet_names": [s.sheet_name for s in fp.sheets], "col_count": len(fp.all_column_names)})

    # ── Stage 2: Platform detection ───────────────────────────────────────────
    _log("info", "detect", f"Detecting platform for '{file_name}'")
    platform_result = detect_platform(fp)
    _log("info", "detect", (
        f"Platform={platform_result.detected_platform} "
        f"confidence={platform_result.confidence_score:.2%} "
        f"signals={len(platform_result.matched_signals)}"
    ), {"matched_signals": platform_result.matched_signals[:10]})

    if platform_result.needs_manual_review:
        _log("warning", "detect", (
            f"Platform confidence {platform_result.confidence_score:.2%} below threshold "
            "— file flagged for manual review"
        ))

    # ── Stage 3: Report type detection ───────────────────────────────────────
    type_result = detect_report_type(platform_result.detected_platform, fp)
    _log("info", "detect", (
        f"Report type={type_result.report_type} confidence={type_result.confidence:.2%}"
    ), {"schema_hints": type_result.schema_hints})

    # ── Stage 4: Schema version detection ────────────────────────────────────
    schema_result = detect_schema_version(
        platform_result.detected_platform,
        type_result.report_type,
        fp,
    )
    _log("info", "detect", (
        f"Schema version={schema_result.schema_version} "
        f"parser={schema_result.parser_name} "
        f"match={schema_result.match_confidence:.2%}"
    ))

    if schema_result.drift_alert:
        da = schema_result.drift_alert
        _log("warning", "detect", f"Schema drift: {da.message}", {
            "missing_columns": da.missing_columns[:10],
            "extra_columns":   da.extra_columns[:10],
            "nearest_version": da.nearest_version,
        })

    # ── Stage 5: Parse ────────────────────────────────────────────────────────
    parser = get_parser(schema_result.parser_name)
    _log("info", "parse", f"Running parser {schema_result.parser_name}")

    try:
        parse_result = parser.parse(file_bytes, quarter_label=quarter_label)
    except Exception as exc:
        _log("error", "parse", f"Parser raised unexpected exception: {exc}")
        return _failed(uploaded_file_id, str(exc), logs)

    for e in parse_result.errors:
        _log("error", "parse", e)
    for w in parse_result.warnings:
        _log("warning", "parse", w)

    _log("info", "parse", (
        f"Parse complete: {parse_result.record_count} ledger records, "
        f"{len(parse_result.recon_issues)} recon issues"
    ))

    # ── Stage 6: Build result ─────────────────────────────────────────────────
    drift_dict = None
    if schema_result.drift_alert:
        da = schema_result.drift_alert
        drift_dict = {
            "platform":            da.platform,
            "report_type":         da.report_type,
            "schema_signature":    da.schema_signature,
            "missing_columns":     da.missing_columns,
            "extra_columns":       da.extra_columns,
            "nearest_version":     da.nearest_version,
            "nearest_similarity":  da.nearest_similarity,
            "message":             da.message,
        }

    detection_metadata = {
        "sheet_names":       [s.sheet_name for s in fp.sheets],
        "all_columns":       fp.all_column_names[:50],
        "schema_signature":  fp.schema_signature,
        "platform_signals":  platform_result.matched_signals[:20],
        "type_signals":      type_result.matched_signals[:10],
        "schema_hints":      type_result.schema_hints,
        "runner_up_platform": platform_result.runner_up_platform,
        "runner_up_score":   platform_result.runner_up_score,
        "processing_logs":   logs,
    }

    return PipelineResult(
        uploaded_file_id=uploaded_file_id,
        platform=platform_result.detected_platform,
        report_type=type_result.report_type,
        schema_version=schema_result.schema_version,
        parser_name=schema_result.parser_name,
        confidence_score=platform_result.confidence_score,
        needs_manual_review=platform_result.needs_manual_review,
        ledger_count=parse_result.record_count,
        recon_issue_count=len(parse_result.recon_issues),
        errors=parse_result.errors,
        warnings=parse_result.warnings,
        drift_alert=drift_dict,
        detection_metadata=detection_metadata,
    ), parse_result


def _failed(
    uploaded_file_id: UUID,
    error: str,
    logs: List[Dict],
) -> "tuple[PipelineResult, None]":
    return PipelineResult(
        uploaded_file_id=uploaded_file_id,
        platform="unknown",
        report_type="unknown",
        schema_version="unknown",
        parser_name="unknown",
        confidence_score=0.0,
        needs_manual_review=True,
        ledger_count=0,
        recon_issue_count=0,
        errors=[error],
        detection_metadata={"processing_logs": logs},
    ), None
