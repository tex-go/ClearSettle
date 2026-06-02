"""
Agent 9: Reconciliation Readiness Assessment.

Determines how ready the uploaded data is for reconciliation based on
what report types have been uploaded for this company.

Full reconciliation requires:
  - Flipkart: pl_report + payment_report + returns_report
  - Amazon: settlement_report + returns_report
  - Meesho: payment_report + returns_report
"""
from __future__ import annotations

import time
from typing import Dict, List, Set

from app.services.intelligence.models import (
    AgentStatus, ReadinessResult, ReconciliationStatus,
)

# Per-platform requirements for full reconciliation
_PLATFORM_REQUIREMENTS: Dict[str, Dict[str, List[str]]] = {
    "flipkart": {
        "full": ["pl_report", "payment_report", "returns_report"],
        "orders": ["pl_report"],
        "settlement": ["payment_report"],
        "returns": ["returns_report"],
        "gst": ["tax_report"],
    },
    "amazon": {
        "full": ["settlement_report", "returns_report"],
        "orders": ["settlement_report"],
        "settlement": ["settlement_report"],
        "returns": ["returns_report"],
        "gst": [],
    },
    "meesho": {
        "full": ["payment_report", "returns_report"],
        "orders": ["payment_report"],
        "settlement": ["payment_report"],
        "returns": ["returns_report"],
        "gst": [],
    },
    "unknown": {
        "full": [],
        "orders": [],
        "settlement": [],
        "returns": [],
        "gst": [],
    },
}


class AgentReadiness:
    AGENT_ID = 9
    AGENT_NAME = "Agent 9: Reconciliation Readiness"

    def run(self, context: dict) -> ReadinessResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return ReadinessResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                reconciliation_status=ReconciliationStatus.insufficient,
                readiness_score=0.0,
                uploaded_report_types=[],
                missing_report_types=[],
                recommended_uploads=[],
                can_reconcile_orders=False,
                can_reconcile_settlement=False,
                can_reconcile_returns=False,
                can_reconcile_gst=False,
            )

    def _process(self, context: dict) -> ReadinessResult:
        platform_result = context.get("platform")
        classification_result = context.get("classification")
        platform = (platform_result.platform if platform_result else "unknown").lower()
        current_report_type = classification_result.report_type if classification_result else "unknown"

        # In production, query DB for all uploaded report types for this company+platform.
        # Here we work with what we have in context (the current upload + any parsed_data hints).
        parsed_data = context.get("parsed_data") or {}
        existing_types_from_context: Set[str] = set(
            parsed_data.get("uploaded_report_types", [])
        )

        # Always include the current report type
        uploaded_types: Set[str] = existing_types_from_context | {current_report_type}

        reqs = _PLATFORM_REQUIREMENTS.get(platform, _PLATFORM_REQUIREMENTS["unknown"])
        full_req = set(reqs.get("full", []))
        order_req = set(reqs.get("orders", []))
        settle_req = set(reqs.get("settlement", []))
        return_req = set(reqs.get("returns", []))
        gst_req = set(reqs.get("gst", []))

        missing = full_req - uploaded_types
        recommended = sorted(missing)

        can_recon_orders = order_req.issubset(uploaded_types)
        can_recon_settle = settle_req.issubset(uploaded_types)
        can_recon_return = return_req.issubset(uploaded_types)
        can_recon_gst = gst_req.issubset(uploaded_types) if gst_req else False

        # Readiness score
        if not full_req:
            readiness_score = 50.0
            recon_status = ReconciliationStatus.single_report
        elif not missing:
            readiness_score = 100.0
            recon_status = ReconciliationStatus.full_ready
        else:
            present = full_req & uploaded_types
            readiness_score = (len(present) / len(full_req)) * 100.0
            recon_status = (
                ReconciliationStatus.partial if readiness_score >= 50
                else ReconciliationStatus.insufficient
            )

        messages: List[str] = []
        if recommended:
            messages.append(f"Missing for full reconciliation: {', '.join(recommended)}")

        agent_status = (
            AgentStatus.success if recon_status == ReconciliationStatus.full_ready
            else AgentStatus.warning
        )

        return ReadinessResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=agent_status,
            duration_ms=0.0,
            messages=messages,
            reconciliation_status=recon_status,
            readiness_score=round(readiness_score, 2),
            uploaded_report_types=sorted(uploaded_types),
            missing_report_types=sorted(missing),
            recommended_uploads=recommended,
            can_reconcile_orders=can_recon_orders,
            can_reconcile_settlement=can_recon_settle,
            can_reconcile_returns=can_recon_return,
            can_reconcile_gst=can_recon_gst,
        )
