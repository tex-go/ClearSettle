"""
Agent 14: Continuous Learning (Stub).

Future capability: adjusts platform signal weights and schema mappings
based on user correction feedback.

v1 implementation: accepts feedback hooks but does not modify signals.
Returns feedback_applied=False with notes explaining the roadmap.
"""
from __future__ import annotations

import time

from app.services.intelligence.models import AgentStatus, LearningResult

_MODEL_VERSION = "v1.0.0-stub"
_NOTES = (
    "Learning pipeline v1 — manual corrections accepted but not yet applied to signal weights. "
    "When a user overrides a platform/report_type classification, that correction is stored "
    "and will be used to adjust confidence weights in v2."
)


class AgentLearning:
    AGENT_ID = 14
    AGENT_NAME = "Agent 14: Continuous Learning"

    def run(self, context: dict) -> LearningResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return LearningResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                feedback_applied=False,
                confidence_adjusted=False,
                new_signals_learned=0,
                model_version=_MODEL_VERSION,
                notes=f"Learning agent error: {e}",
            )

    def _process(self, context: dict) -> LearningResult:
        # Check if there's any correction feedback in context
        feedback = context.get("user_correction_feedback") or {}
        new_signals = 0

        if feedback:
            # In v2, we would:
            # 1. Store the correction in a feedback_log table
            # 2. Increment signal weights for the corrected platform
            # 3. Decrement weights for the incorrectly detected platform
            # For now, just acknowledge receipt
            new_signals = len(feedback.get("new_signals", []))

        return LearningResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=AgentStatus.success,
            duration_ms=0.0,
            messages=[],
            feedback_applied=False,
            confidence_adjusted=False,
            new_signals_learned=new_signals,
            model_version=_MODEL_VERSION,
            notes=_NOTES,
        )
