"""
Agent 3: Platform Detection.

Wraps the existing platform_detector.detect_platform() and converts
its PlatformDetectionResult into a PlatformResult.
"""
from __future__ import annotations

import time

from app.services.detection.platform_detector import detect_platform
from app.services.intelligence.models import AgentStatus, PlatformResult


class AgentPlatform:
    AGENT_ID = 3
    AGENT_NAME = "Agent 3: Platform Detection"

    def run(self, context: dict) -> PlatformResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return PlatformResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                platform="unknown",
                confidence=0.0,
                matched_signals=[],
                runner_up=None,
                runner_up_confidence=0.0,
                needs_manual_review=True,
                reason=f"Detection failed: {e}",
            )

    def _process(self, context: dict) -> PlatformResult:
        fp = context.get("fingerprint")
        if fp is None:
            return PlatformResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.skipped,
                duration_ms=0.0,
                messages=["No fingerprint available — skipped."],
                platform="unknown",
                confidence=0.0,
                matched_signals=[],
                runner_up=None,
                runner_up_confidence=0.0,
                needs_manual_review=True,
                reason="Fingerprint not available.",
            )

        det = detect_platform(fp)

        platform_hint = context.get("platform_hint", "")
        if platform_hint and det.detected_platform == "unknown":
            # Honour manual hint
            return PlatformResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.warning,
                duration_ms=0.0,
                messages=[f"Platform auto-detection returned 'unknown'; using hint '{platform_hint}'."],
                platform=platform_hint,
                confidence=0.5,
                matched_signals=[f"manual_hint:{platform_hint}"],
                runner_up=det.runner_up_platform,
                runner_up_confidence=det.runner_up_score,
                needs_manual_review=True,
                reason="Low confidence auto-detection; manual hint applied.",
            )

        status = AgentStatus.warning if det.needs_manual_review else AgentStatus.success
        reason = (
            "Low confidence — manual review recommended."
            if det.needs_manual_review
            else f"Platform detected with {det.confidence_score:.0%} confidence."
        )

        return PlatformResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=[],
            platform=det.detected_platform,
            confidence=det.confidence_score,
            matched_signals=det.matched_signals,
            runner_up=det.runner_up_platform,
            runner_up_confidence=det.runner_up_score,
            needs_manual_review=det.needs_manual_review,
            reason=reason,
        )
