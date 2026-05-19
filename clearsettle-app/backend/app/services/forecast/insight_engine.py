"""
AI-powered cash flow insight engine using Claude API.

Generates plain-language insights, warnings, and recommendations from
historical snapshots and the current projection.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1024

_SYSTEM = """\
You are a financial analyst AI specializing in e-commerce cash flow.
You analyze settlement data, fee patterns, and cash flow projections for
Indian marketplace sellers (primarily Amazon, Flipkart).
Return concise, actionable insights in JSON format only.
"""

_PROMPT_TEMPLATE = """\
Analyze the following cash flow data and return exactly this JSON structure:
{{
  "insights": [
    {{
      "type": "trend|warning|opportunity|anomaly",
      "severity": "info|warning|critical",
      "title": "Short title (max 8 words)",
      "description": "2-3 sentence explanation",
      "action": "Specific recommended action (optional)"
    }}
  ]
}}

Return 3-6 insights. Focus on:
- Cash shortage warnings (negative or near-zero projections)
- Revenue trends (growing, declining, seasonal)
- Fee anomalies (unusually high fees)
- Platform concentration risk
- Opportunities to improve cash flow

Data:
{data_json}
"""


async def generate_insights(
    snapshots: list[dict],
    projection: dict[str, Any] | None,
    *,
    anthropic_api_key: str,
) -> dict[str, Any]:
    """
    Call Claude to generate cash flow insights.
    Returns dict with 'insights' list and metadata.
    Falls back to rule-based insights if API call fails.
    """
    # Build compact data summary for the prompt
    data_summary = {
        "historical_snapshots": snapshots[-6:] if len(snapshots) > 6 else snapshots,
        "projection_summary": {
            "horizon":                  projection.get("horizon") if projection else None,
            "current_balance":          projection.get("current_balance") if projection else None,
            "total_projected_inflow":   projection.get("total_projected_inflow") if projection else None,
            "total_projected_outflow":  projection.get("total_projected_outflow") if projection else None,
            "net_projection":           projection.get("net_projection") if projection else None,
            "shortage_points":          [
                p for p in (projection.get("points") or [])
                if p.get("shortage_risk") in ("high", "critical")
            ][:3] if projection else [],
        } if projection else None,
    }

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": _PROMPT_TEMPLATE.format(
                    data_json=json.dumps(data_summary, indent=2)
                ),
            }],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        return {
            "insights":     parsed.get("insights", []),
            "generated_at": datetime.utcnow().isoformat(),
            "model_used":   _MODEL,
        }
    except Exception as exc:
        logger.warning("insight_engine: AI call failed, using rule-based fallback: %s", exc)
        return _rule_based_insights(snapshots, projection)


def _rule_based_insights(
    snapshots: list[dict],
    projection: dict[str, Any] | None,
) -> dict[str, Any]:
    insights = []

    if projection:
        net = projection.get("net_projection", 0)
        balance = projection.get("current_balance", 0)

        if net < 0:
            insights.append({
                "type": "warning",
                "severity": "critical",
                "title": "Negative net cash flow projected",
                "description": (
                    f"Your projected outflows exceed inflows by ₹{abs(net):,.0f} "
                    f"over the next {projection.get('horizon', 'period')}. "
                    "This will reduce your available working capital."
                ),
                "action": "Review and reduce platform fees, or increase sales volume.",
            })

        critical_points = [
            p for p in (projection.get("points") or [])
            if p.get("shortage_risk") == "critical"
        ]
        if critical_points:
            insights.append({
                "type": "warning",
                "severity": "critical",
                "title": "Cash shortage risk detected",
                "description": (
                    f"Balance may go critically low around {critical_points[0]['date']}. "
                    "This could impact your ability to replenish inventory or pay vendors."
                ),
                "action": "Arrange working capital credit line or defer large purchases.",
            })

    if snapshots:
        recent = snapshots[:3]
        if len(recent) >= 2:
            trend = recent[0].get("inflows", 0) - recent[-1].get("inflows", 0)
            if trend < 0:
                insights.append({
                    "type": "trend",
                    "severity": "warning",
                    "title": "Declining inflows trend",
                    "description": "Settlement inflows have been declining over the past periods.",
                    "action": "Investigate sales performance and advertising spend ROI.",
                })
            else:
                insights.append({
                    "type": "trend",
                    "severity": "info",
                    "title": "Positive inflow trend",
                    "description": "Settlement receipts are growing — strong revenue momentum.",
                    "action": None,
                })

    if not insights:
        insights.append({
            "type": "trend",
            "severity": "info",
            "title": "Insufficient data for deep analysis",
            "description": "Connect more platforms and allow more settlement data to accumulate for better insights.",
            "action": "Link additional marketplaces in Platform Connections.",
        })

    return {
        "insights":     insights,
        "generated_at": datetime.utcnow().isoformat(),
        "model_used":   "rule_based",
    }
