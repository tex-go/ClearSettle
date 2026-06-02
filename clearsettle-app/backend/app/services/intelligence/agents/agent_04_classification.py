"""
Agent 4: Report Classification.

Wraps the existing report_type_detector.detect_report_type() and converts
its ReportTypeResult into a ClassificationResult with a human-readable label.
"""
from __future__ import annotations

import time

from app.services.detection.report_type_detector import detect_report_type
from app.services.intelligence.models import AgentStatus, ClassificationResult

_REPORT_TYPE_LABELS = {
    # Flipkart
    "pl_report":          "Flipkart Profit & Loss Report",
    "payment_report":     "Payment / Settlement Report",
    "tax_report":         "Tax / GST Report",
    "returns_report":     "Returns Report",
    "commission_invoice": "Commission Invoice",
    "fulfillment_report": "Fulfillment / Logistics Report",
    # Amazon
    "settlement_report":  "Amazon Settlement Report",
    "safe_t_report":      "Amazon SAFE-T Reimbursement",
    "fba_inventory":      "FBA Inventory Report",
    # Meesho
    "order_report":       "Meesho Order Report",
    # Generic
    "unknown":            "Unknown Report Type",
}


class AgentClassification:
    AGENT_ID = 4
    AGENT_NAME = "Agent 4: Report Classification"

    def run(self, context: dict) -> ClassificationResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return ClassificationResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                report_type="unknown",
                report_type_label="Unknown Report Type",
                confidence=0.0,
                matched_signals=[],
                schema_hints={},
            )

    def _process(self, context: dict) -> ClassificationResult:
        fp = context.get("fingerprint")
        platform_result = context.get("platform")
        platform = (platform_result.platform if platform_result else None) or "unknown"

        if fp is None or platform == "unknown":
            return ClassificationResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.skipped,
                duration_ms=0.0,
                messages=["Cannot classify without fingerprint and platform — skipped."],
                report_type="unknown",
                report_type_label="Unknown Report Type",
                confidence=0.0,
                matched_signals=[],
                schema_hints={},
            )

        # Apply report type hint if present
        report_type_hint = context.get("report_type_hint", "")
        if report_type_hint:
            label = _REPORT_TYPE_LABELS.get(report_type_hint, report_type_hint.replace("_", " ").title())
            return ClassificationResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.success,
                duration_ms=0.0,
                messages=[f"Using provided report_type hint: {report_type_hint}"],
                report_type=report_type_hint,
                report_type_label=label,
                confidence=1.0,
                matched_signals=[f"manual_hint:{report_type_hint}"],
                schema_hints={},
            )

        rtr = detect_report_type(platform, fp)
        label = _REPORT_TYPE_LABELS.get(rtr.report_type, rtr.report_type.replace("_", " ").title())

        status = AgentStatus.warning if rtr.confidence < 0.4 else AgentStatus.success
        messages = []
        if rtr.confidence < 0.4:
            messages.append(f"Low classification confidence ({rtr.confidence:.0%}). Manual review advised.")

        return ClassificationResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=messages,
            report_type=rtr.report_type,
            report_type_label=label,
            confidence=rtr.confidence,
            matched_signals=rtr.matched_signals,
            schema_hints=rtr.schema_hints,
        )
