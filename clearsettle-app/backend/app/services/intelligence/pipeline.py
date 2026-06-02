"""
14-Agent Intelligent Report Ingestion Pipeline.

Orchestrates all 14 specialised agents sequentially.
Each agent enriches the shared context, which subsequent agents consume.
A failure in one agent is caught and logged — the pipeline continues.

Usage:
    pipeline = IntelligencePipeline()
    result = await pipeline.run(
        file_bytes, filename, upload_id, company_id, db,
        parsed_data={"summary": {...}, "orders": [...]},
    )
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.services.detection.fingerprinter import fingerprint_file
from app.services.intelligence.agents.agent_01_intake import AgentIntake
from app.services.intelligence.agents.agent_02_structure import AgentStructure
from app.services.intelligence.agents.agent_03_platform import AgentPlatform
from app.services.intelligence.agents.agent_04_classification import AgentClassification
from app.services.intelligence.agents.agent_05_schema import AgentSchema
from app.services.intelligence.agents.agent_06_quality import AgentQuality
from app.services.intelligence.agents.agent_07_financial import AgentFinancial
from app.services.intelligence.agents.agent_08_metrics import AgentMetrics
from app.services.intelligence.agents.agent_09_readiness import AgentReadiness
from app.services.intelligence.agents.agent_10_reconciliation import AgentReconciliation
from app.services.intelligence.agents.agent_11_insights import AgentInsights
from app.services.intelligence.agents.agent_12_registry import AgentRegistry
from app.services.intelligence.agents.agent_13_audit import AgentAudit
from app.services.intelligence.agents.agent_14_learning import AgentLearning
from app.services.intelligence.models import PipelineResult


class IntelligencePipeline:
    """
    Runs all 14 intelligence agents sequentially, building up a shared context.

    Agents 1–11 are synchronous (CPU-bound analysis).
    Agents 12–13 are async (DB writes).
    Agent 14 is synchronous (stub).
    """

    async def run(
        self,
        file_bytes: bytes,
        filename: str,
        upload_id: str,
        company_id: str,
        db,  # AsyncSession | None
        parsed_data: Optional[Dict[str, Any]] = None,
        platform_hint: Optional[str] = None,
        report_type_hint: Optional[str] = None,
        is_duplicate_upload: bool = False,
    ) -> PipelineResult:
        pipeline_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # Shared mutable context — each agent reads and extends this
        context: Dict[str, Any] = {
            "file_bytes": file_bytes,
            "filename": filename,
            "upload_id": upload_id,
            "company_id": company_id,
            "db": db,
            "parsed_data": parsed_data or {},
            "platform_hint": platform_hint or "",
            "report_type_hint": report_type_hint or "",
            "is_duplicate_upload": is_duplicate_upload,
        }

        result = PipelineResult(
            pipeline_id=pipeline_id,
            upload_id=upload_id,
            company_id=company_id,
            started_at=started_at,
            pipeline_status="running",
        )

        errors: List[str] = []

        # ── Phase 1: File intake ──────────────────────────────────────────────────
        try:
            result.intake = AgentIntake().run(context)
            context["intake"] = result.intake
        except Exception as e:
            errors.append(f"Agent 1 (Intake) fatal: {e}")

        # Fingerprint the file — shared by agents 2-10
        try:
            fp = fingerprint_file(file_bytes, filename)
            context["fingerprint"] = fp
        except Exception as e:
            errors.append(f"Fingerprinting failed: {e}")
            context["fingerprint"] = None

        # ── Phase 2: Structure analysis ───────────────────────────────────────────
        try:
            result.structure = AgentStructure().run(context)
            context["structure"] = result.structure
        except Exception as e:
            errors.append(f"Agent 2 (Structure) fatal: {e}")

        # ── Phase 3: Platform detection ───────────────────────────────────────────
        try:
            result.platform = AgentPlatform().run(context)
            context["platform"] = result.platform
        except Exception as e:
            errors.append(f"Agent 3 (Platform) fatal: {e}")

        # ── Phase 4: Report classification ────────────────────────────────────────
        try:
            result.classification = AgentClassification().run(context)
            context["classification"] = result.classification
        except Exception as e:
            errors.append(f"Agent 4 (Classification) fatal: {e}")

        # ── Phase 5: Schema intelligence ──────────────────────────────────────────
        try:
            result.schema = AgentSchema().run(context)
            context["schema"] = result.schema
        except Exception as e:
            errors.append(f"Agent 5 (Schema) fatal: {e}")

        # ── Phase 6: Data quality ─────────────────────────────────────────────────
        try:
            result.quality = AgentQuality().run(context)
            context["quality"] = result.quality
        except Exception as e:
            errors.append(f"Agent 6 (Quality) fatal: {e}")

        # ── Phase 7: Financial extraction ─────────────────────────────────────────
        try:
            result.financial = AgentFinancial().run(context)
            context["financial"] = result.financial
        except Exception as e:
            errors.append(f"Agent 7 (Financial) fatal: {e}")

        # ── Phase 8: Metrics KPIs ─────────────────────────────────────────────────
        try:
            result.metrics = AgentMetrics().run(context)
            context["metrics"] = result.metrics
        except Exception as e:
            errors.append(f"Agent 8 (Metrics) fatal: {e}")

        # ── Phase 9: Reconciliation readiness ─────────────────────────────────────
        try:
            result.readiness = AgentReadiness().run(context)
            context["readiness"] = result.readiness
        except Exception as e:
            errors.append(f"Agent 9 (Readiness) fatal: {e}")

        # ── Phase 10: Reconciliation intelligence ─────────────────────────────────
        try:
            result.reconciliation = AgentReconciliation().run(context)
            context["reconciliation"] = result.reconciliation
        except Exception as e:
            errors.append(f"Agent 10 (Reconciliation) fatal: {e}")

        # ── Phase 11: Insights generation ────────────────────────────────────────
        try:
            result.insights = AgentInsights().run(context)
            context["insights"] = result.insights
        except Exception as e:
            errors.append(f"Agent 11 (Insights) fatal: {e}")

        # ── Phase 12: Registry (async) ────────────────────────────────────────────
        try:
            if db is not None:
                result.registry = await AgentRegistry().run_async(context)
            else:
                result.registry = AgentRegistry().run(context)
            context["registry"] = result.registry
        except Exception as e:
            errors.append(f"Agent 12 (Registry) fatal: {e}")

        # ── Phase 13: Audit (async) ───────────────────────────────────────────────
        try:
            if db is not None:
                result.audit = await AgentAudit().run_async(context)
            else:
                result.audit = AgentAudit().run(context)
            context["audit"] = result.audit
        except Exception as e:
            errors.append(f"Agent 13 (Audit) fatal: {e}")

        # ── Phase 14: Learning (sync) ─────────────────────────────────────────────
        try:
            result.learning = AgentLearning().run(context)
            context["learning"] = result.learning
        except Exception as e:
            errors.append(f"Agent 14 (Learning) fatal: {e}")

        # ── Finalise ──────────────────────────────────────────────────────────────
        completed_at = datetime.utcnow()
        result.completed_at = completed_at
        result.total_duration_ms = (completed_at - started_at).total_seconds() * 1000
        result.errors = errors
        result.pipeline_status = (
            "failed" if len(errors) >= 7
            else "partial" if errors
            else "success"
        )
        result.summary = self._build_summary(result)
        result.recommended_actions = self._build_recommendations(result)

        return result

    def _build_summary(self, result: PipelineResult) -> Dict[str, Any]:
        return {
            "pipeline_id": result.pipeline_id,
            "platform": result.platform.platform if result.platform else "unknown",
            "platform_confidence": result.platform.confidence if result.platform else 0.0,
            "report_type": result.classification.report_type if result.classification else "unknown",
            "report_type_label": result.classification.report_type_label if result.classification else "Unknown",
            "schema_version": result.schema.schema_version if result.schema else "unknown",
            "mapping_coverage": result.schema.mapping_coverage if result.schema else 0.0,
            "quality_score": result.quality.quality_score if result.quality else 0.0,
            "total_rows": result.quality.total_rows if result.quality else 0,
            "duplicate_rows": result.quality.duplicate_rows if result.quality else 0,
            "gross_sales": str(result.metrics.gross_sales) if result.metrics else "0",
            "net_settlement": str(result.financial.net_payout.value) if result.financial else "0",
            "total_orders": result.metrics.total_orders if result.metrics else 0,
            "fee_percentage": result.metrics.fee_percentage if result.metrics else 0.0,
            "return_rate": result.metrics.return_rate if result.metrics else 0.0,
            "settlement_efficiency": result.metrics.settlement_efficiency if result.metrics else 0.0,
            "reconciliation_readiness": result.readiness.readiness_score if result.readiness else 0.0,
            "reconciliation_status": (
                result.readiness.reconciliation_status.value if result.readiness else "unknown"
            ),
            "discrepancies_found": result.reconciliation.discrepancy_count if result.reconciliation else 0,
            "total_recoverable": str(result.reconciliation.total_recoverable) if result.reconciliation else "0",
            "insights_count": result.insights.total_insights if result.insights else 0,
            "critical_insights": result.insights.critical_count if result.insights else 0,
            "opportunity_amount": str(result.insights.opportunity_amount) if result.insights else "0",
            "drift_detected": result.schema.drift_detected if result.schema else False,
            "needs_manual_review": result.platform.needs_manual_review if result.platform else True,
            "total_duration_ms": result.total_duration_ms,
        }

    def _build_recommendations(self, result: PipelineResult) -> List[str]:
        recs: List[str] = []

        if result.readiness and result.readiness.recommended_uploads:
            for rpt in result.readiness.recommended_uploads:
                recs.append(f"Upload {rpt.replace('_', ' ')} for complete reconciliation")

        if result.quality and result.quality.quality_score < 70:
            recs.append("Review data quality issues before running reconciliation")

        if result.reconciliation and result.reconciliation.total_recoverable > Decimal("0"):
            recs.append(
                f"₹{result.reconciliation.total_recoverable:.0f} in recoverable amounts detected — "
                "raise disputes with marketplace"
            )

        if result.schema and result.schema.drift_detected:
            recs.append("Schema drift detected — register new schema version before next upload")

        if result.platform and result.platform.needs_manual_review:
            recs.append(
                f"Platform detection confidence is low ({result.platform.confidence:.0%}) — "
                "verify platform manually"
            )

        if result.metrics and result.metrics.return_rate > 20:
            recs.append(
                f"High return rate ({result.metrics.return_rate:.1f}%) — "
                "investigate product listings and quality"
            )

        return recs
