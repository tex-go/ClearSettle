"""
Agent 5: Schema Intelligence.

Wraps detect_schema_version() from the existing schema_detector and
ALSO performs universal field mapping using UNIVERSAL_FIELD_MAP.
Computes mapping_coverage = mapped_columns / total_columns.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from app.services.detection.schema_detector import detect_schema_version
from app.services.intelligence.models import (
    AgentStatus, FieldMapping, SchemaResult,
)
from app.services.intelligence.universal_schema import map_column


class AgentSchema:
    AGENT_ID = 5
    AGENT_NAME = "Agent 5: Schema Intelligence"

    def run(self, context: dict) -> SchemaResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return SchemaResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                schema_version="unknown",
                mapped_fields=[],
                unmapped_columns=[],
                mapping_coverage=0.0,
                drift_detected=False,
                drift_details=None,
            )

    def _process(self, context: dict) -> SchemaResult:
        fp = context.get("fingerprint")
        platform_result = context.get("platform")
        classification_result = context.get("classification")

        platform = (platform_result.platform if platform_result else None) or "unknown"
        report_type = (classification_result.report_type if classification_result else None) or "unknown"

        if fp is None:
            return SchemaResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.skipped,
                duration_ms=0.0,
                messages=["No fingerprint available — skipped."],
                schema_version="unknown",
                mapped_fields=[],
                unmapped_columns=[],
                mapping_coverage=0.0,
                drift_detected=False,
                drift_details=None,
            )

        # Schema version detection
        sdr = detect_schema_version(platform, report_type, fp)
        drift_detected = sdr.drift_alert is not None
        drift_details: Dict[str, Any] | None = None
        if sdr.drift_alert:
            da = sdr.drift_alert
            drift_details = {
                "message": da.message,
                "missing_columns": da.missing_columns,
                "extra_columns": da.extra_columns[:20],
                "nearest_version": da.nearest_version,
                "nearest_similarity": da.nearest_similarity,
            }

        # Universal field mapping
        all_columns = fp.all_column_names
        mapped_fields: List[FieldMapping] = []
        unmapped_columns: List[str] = []

        for col in all_columns:
            spec = map_column(platform, col)
            if spec:
                universal_field, transform = spec
                mapped_fields.append(FieldMapping(
                    source_column=col,
                    universal_field=universal_field,
                    confidence=0.9,
                    transform=transform,
                ))
            else:
                unmapped_columns.append(col)

        total = len(all_columns)
        mapping_coverage = (len(mapped_fields) / total * 100.0) if total > 0 else 0.0

        messages = []
        if drift_detected:
            messages.append(f"Schema drift detected. {sdr.drift_alert.message[:200]}")
        if mapping_coverage < 50.0:
            messages.append(f"Low field mapping coverage: {mapping_coverage:.1f}%")

        status = (
            AgentStatus.error if drift_detected and mapping_coverage < 20.0
            else AgentStatus.warning if drift_detected or mapping_coverage < 50.0
            else AgentStatus.success
        )

        return SchemaResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=messages,
            schema_version=sdr.schema_version,
            mapped_fields=mapped_fields,
            unmapped_columns=unmapped_columns,
            mapping_coverage=round(mapping_coverage, 2),
            drift_detected=drift_detected,
            drift_details=drift_details,
        )
