"""
Agent 6: Data Quality Assessment.

Checks:
  - Duplicate order IDs within the file
  - Null / empty critical fields (order_id, amount, date)
  - Type mismatches (amount fields that are not numeric)
  - Duplicate upload detection via file hash stored in context
  - Computes quality_score 0-100
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Set

from app.services.intelligence.models import (
    AgentStatus, QualityIssue, QualityResult,
)

_CRITICAL_UNIVERSAL_FIELDS = {"order_id", "gross_amount", "net_settlement", "order_date"}
_NUMERIC_FIELDS = {"gross_amount", "net_settlement", "commission", "shipping_fee", "tcs", "tds", "gst_on_fees"}


class AgentQuality:
    AGENT_ID = 6
    AGENT_NAME = "Agent 6: Data Quality Assessment"

    def run(self, context: dict) -> QualityResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return QualityResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                quality_score=0.0,
                total_rows=0,
                valid_rows=0,
                duplicate_rows=0,
                null_critical_fields=0,
                type_mismatch_count=0,
                is_duplicate_upload=False,
                issues=[],
            )

    def _process(self, context: dict) -> QualityResult:
        fp = context.get("fingerprint")
        schema_result = context.get("schema")
        intake_result = context.get("intake")
        issues: List[QualityIssue] = []
        messages: List[str] = []

        # Duplicate upload detection
        is_duplicate_upload = context.get("is_duplicate_upload", False)
        if is_duplicate_upload:
            issues.append(QualityIssue(
                severity="warning",
                code="DUPLICATE_UPLOAD",
                message="This file has been uploaded before (identical SHA-256 hash).",
                affected_rows=None,
                affected_column=None,
            ))

        if fp is None:
            return QualityResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.skipped,
                duration_ms=0.0,
                messages=["No fingerprint available — skipped."],
                quality_score=50.0,
                total_rows=0,
                valid_rows=0,
                duplicate_rows=0,
                null_critical_fields=0,
                type_mismatch_count=0,
                is_duplicate_upload=is_duplicate_upload,
                issues=issues,
            )

        # Gather all sample rows from all sheets
        all_samples: List[Dict[str, Any]] = []
        for sh in fp.sheets:
            all_samples.extend(sh.sample_rows)

        total_rows = sum(sh.row_count for sh in fp.sheets)
        # Estimate data rows (subtract header scan rows)
        data_rows = max(total_rows - len(fp.sheets) * 20, 0) if total_rows > 0 else 0
        # Use sample rows for quality checks (we only have samples)
        sample_count = len(all_samples)

        # Build field→column mapping from schema result
        field_to_col: Dict[str, str] = {}
        if schema_result and schema_result.mapped_fields:
            for fm in schema_result.mapped_fields:
                field_to_col[fm.universal_field] = fm.source_column

        # 1. Null critical fields check
        null_critical = 0
        critical_cols = {field_to_col.get(f, f) for f in _CRITICAL_UNIVERSAL_FIELDS}
        for row in all_samples:
            for col in critical_cols:
                val = row.get(col)
                if val is None or str(val).strip() == "":
                    null_critical += 1

        if null_critical > 0:
            issues.append(QualityIssue(
                severity="warning",
                code="NULL_CRITICAL_FIELDS",
                message=f"{null_critical} null values in critical fields across sample rows.",
                affected_rows=null_critical,
                affected_column=str(critical_cols),
            ))

        # 2. Duplicate order IDs
        order_id_col = field_to_col.get("order_id", "order id")
        order_ids: List[str] = []
        for row in all_samples:
            val = row.get(order_id_col) or row.get("order_id") or row.get("order id")
            if val and str(val).strip():
                order_ids.append(str(val).strip())

        seen: Set[str] = set()
        duplicates = 0
        for oid in order_ids:
            if oid in seen:
                duplicates += 1
            seen.add(oid)

        if duplicates > 0:
            issues.append(QualityIssue(
                severity="warning",
                code="DUPLICATE_ORDER_IDS",
                message=f"{duplicates} duplicate order IDs detected in sample rows.",
                affected_rows=duplicates,
                affected_column=order_id_col,
            ))

        # 3. Type mismatch check
        type_mismatches = 0
        numeric_cols = {field_to_col.get(f, f) for f in _NUMERIC_FIELDS}
        for row in all_samples:
            for col in numeric_cols:
                val = row.get(col)
                if val is not None and str(val).strip() != "":
                    cleaned = str(val).replace(",", "").replace("₹", "").strip()
                    try:
                        float(cleaned)
                    except (ValueError, TypeError):
                        type_mismatches += 1

        if type_mismatches > 0:
            issues.append(QualityIssue(
                severity="error",
                code="TYPE_MISMATCH",
                message=f"{type_mismatches} non-numeric values found in amount fields.",
                affected_rows=type_mismatches,
                affected_column="amount_fields",
            ))

        # 4. Empty file warning
        if total_rows == 0 or (sample_count == 0 and data_rows == 0):
            issues.append(QualityIssue(
                severity="error",
                code="EMPTY_FILE",
                message="No data rows detected in the file.",
                affected_rows=0,
                affected_column=None,
            ))

        # 5. Too few columns
        total_cols = len(fp.all_column_names)
        if total_cols < 3:
            issues.append(QualityIssue(
                severity="warning",
                code="FEW_COLUMNS",
                message=f"Only {total_cols} columns detected. File may be incomplete.",
                affected_rows=None,
                affected_column=None,
            ))

        # Quality score calculation
        # Start at 100, deduct for issues
        score = 100.0
        for issue in issues:
            if issue.code == "EMPTY_FILE":
                score -= 50.0
            elif issue.severity == "error":
                score -= 15.0
            elif issue.severity == "warning":
                score -= 5.0

        # Penalise heavily for null critical fields relative to sample size
        if sample_count > 0 and null_critical > 0:
            null_pct = null_critical / (sample_count * len(critical_cols)) if critical_cols else 0
            score -= null_pct * 20.0

        score = max(0.0, min(100.0, score))

        valid_rows = max(0, data_rows - duplicates - null_critical)

        if issues:
            status = AgentStatus.warning if score >= 60 else AgentStatus.error
        else:
            status = AgentStatus.success

        if score < 70:
            messages.append(f"Quality score {score:.0f}/100 — review issues before reconciliation.")

        return QualityResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=messages,
            quality_score=round(score, 2),
            total_rows=data_rows,
            valid_rows=valid_rows,
            duplicate_rows=duplicates,
            null_critical_fields=null_critical,
            type_mismatch_count=type_mismatches,
            is_duplicate_upload=is_duplicate_upload,
            issues=issues,
        )
