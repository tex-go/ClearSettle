"""
Agent 11: Seller Insights Generator.

Rules-based engine that produces natural language insights from
all previous agent results. Insights are categorised and severity-tagged.
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import List

from app.services.intelligence.models import (
    AgentStatus, Insight, InsightsResult,
)


class AgentInsights:
    AGENT_ID = 11
    AGENT_NAME = "Agent 11: Seller Insights"

    def run(self, context: dict) -> InsightsResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return InsightsResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                insights=[],
                total_insights=0,
                critical_count=0,
                opportunity_amount=Decimal("0"),
            )

    def _process(self, context: dict) -> InsightsResult:
        quality = context.get("quality")
        financial = context.get("financial")
        metrics = context.get("metrics")
        readiness = context.get("readiness")
        reconciliation = context.get("reconciliation")
        schema = context.get("schema")
        platform_result = context.get("platform")

        platform = (platform_result.platform if platform_result else "unknown").lower()
        insights: List[Insight] = []

        # ── Quality insights ──────────────────────────────────────────────────────
        if quality:
            if quality.quality_score < 50:
                insights.append(Insight(
                    category="compliance",
                    severity="critical",
                    title="Severe Data Quality Issues",
                    message=(
                        f"Data quality score is {quality.quality_score:.0f}/100. "
                        "Significant data quality problems detected. Reconciliation accuracy will be impacted."
                    ),
                    metric_value=f"{quality.quality_score:.0f}/100",
                    action="Review and correct data quality issues before proceeding.",
                ))
            elif quality.quality_score < 70:
                insights.append(Insight(
                    category="compliance",
                    severity="warning",
                    title="Data Quality Issues Detected",
                    message=(
                        f"Data quality score is {quality.quality_score:.0f}/100. "
                        f"{len(quality.issues)} issue(s) found including null fields and/or duplicates."
                    ),
                    metric_value=f"{quality.quality_score:.0f}/100",
                    action="Review flagged rows before running reconciliation.",
                ))
            if quality.duplicate_rows > 0:
                insights.append(Insight(
                    category="compliance",
                    severity="warning",
                    title="Duplicate Order IDs Found",
                    message=f"{quality.duplicate_rows} duplicate order IDs detected. These may inflate financial totals.",
                    metric_value=str(quality.duplicate_rows),
                    action="Investigate and de-duplicate before reconciliation.",
                ))
            if quality.is_duplicate_upload:
                insights.append(Insight(
                    category="compliance",
                    severity="info",
                    title="Duplicate File Upload",
                    message="This file has been uploaded before. Existing results are available.",
                    metric_value=None,
                    action="Use existing results or re-process if needed.",
                ))

        # ── Return rate insights ──────────────────────────────────────────────────
        if metrics:
            if metrics.return_rate > 30:
                insights.append(Insight(
                    category="returns",
                    severity="critical",
                    title="Very High Return Rate",
                    message=(
                        f"Return rate is {metrics.return_rate:.1f}% — significantly above the 20% threshold. "
                        f"Returns value: ₹{metrics.return_value:.0f}."
                    ),
                    metric_value=f"{metrics.return_rate:.1f}%",
                    action="Investigate product quality, listing accuracy, or customer expectations.",
                ))
            elif metrics.return_rate > 20:
                insights.append(Insight(
                    category="returns",
                    severity="warning",
                    title="High Return Rate Detected",
                    message=(
                        f"Return rate is {metrics.return_rate:.1f}%, exceeding the 20% benchmark. "
                        f"Returns value: ₹{metrics.return_value:.0f}."
                    ),
                    metric_value=f"{metrics.return_rate:.1f}%",
                    action="Review return reasons and product descriptions.",
                ))

            # ── Fee insights ──────────────────────────────────────────────────────
            if metrics.fee_percentage > 30:
                insights.append(Insight(
                    category="fees",
                    severity="critical",
                    title=f"Marketplace Fees Consuming {metrics.fee_percentage:.0f}% of Revenue",
                    message=(
                        f"Total marketplace fees are {metrics.fee_percentage:.1f}% of gross sales. "
                        f"Total fees: ₹{metrics.total_marketplace_fees + metrics.total_logistics_fees:.0f}."
                    ),
                    metric_value=f"{metrics.fee_percentage:.1f}%",
                    action="Negotiate fee structures or review product pricing strategy.",
                ))
            elif metrics.fee_percentage > 25:
                insights.append(Insight(
                    category="fees",
                    severity="warning",
                    title="Marketplace Fees Above 25% of Gross Sales",
                    message=(
                        f"Fees are {metrics.fee_percentage:.1f}% of gross revenue. "
                        "This may be reducing profitability."
                    ),
                    metric_value=f"{metrics.fee_percentage:.1f}%",
                    action="Review fee structures and consider product pricing adjustments.",
                ))

            # ── Settlement efficiency ─────────────────────────────────────────────
            if metrics.settlement_efficiency < 80 and metrics.gross_sales > Decimal("0"):
                insights.append(Insight(
                    category="settlement",
                    severity="critical",
                    title=f"Settlement Efficiency Only {metrics.settlement_efficiency:.0f}%",
                    message=(
                        f"Only {metrics.settlement_efficiency:.1f}% of expected settlement received. "
                        f"Expected: ₹{metrics.expected_settlement:.0f}, "
                        f"Actual: ₹{metrics.actual_settlement:.0f}."
                    ),
                    metric_value=f"{metrics.settlement_efficiency:.1f}%",
                    action="Raise a settlement dispute with the marketplace immediately.",
                ))
            elif metrics.settlement_efficiency < 90 and metrics.gross_sales > Decimal("0"):
                insights.append(Insight(
                    category="settlement",
                    severity="warning",
                    title="Settlement Efficiency Below 90%",
                    message=(
                        f"Settlement efficiency is {metrics.settlement_efficiency:.1f}%. "
                        f"Gap: ₹{float(metrics.expected_settlement - metrics.actual_settlement):.0f}."
                    ),
                    metric_value=f"{metrics.settlement_efficiency:.1f}%",
                    action="Review settlement statement for unexplained deductions.",
                ))

            # ── Hidden deductions ─────────────────────────────────────────────────
            if metrics.hidden_deductions > Decimal("500"):
                insights.append(Insight(
                    category="opportunity",
                    severity="warning",
                    title="Unexplained Deductions Detected",
                    message=(
                        f"₹{metrics.hidden_deductions:.0f} in deductions not accounted for by "
                        "known fee types."
                    ),
                    metric_value=f"₹{metrics.hidden_deductions:.0f}",
                    action="Request fee breakdown from marketplace.",
                ))

            # ── Revenue insights ──────────────────────────────────────────────────
            if metrics.gross_sales > Decimal("100000"):
                insights.append(Insight(
                    category="revenue",
                    severity="info",
                    title="High Revenue Period",
                    message=(
                        f"Gross sales of ₹{metrics.gross_sales:.0f} with {metrics.total_orders} orders. "
                        f"Average order value: ₹{metrics.average_order_value:.0f}."
                    ),
                    metric_value=f"₹{metrics.gross_sales:.0f}",
                    action=None,
                ))

        # ── Schema drift insight ──────────────────────────────────────────────────
        if schema and schema.drift_detected:
            insights.append(Insight(
                category="compliance",
                severity="warning",
                title="Report Format Changed — Schema Drift Detected",
                message=(
                    "The report schema has changed from the known baseline. "
                    "Field mappings may be incomplete."
                ),
                metric_value=f"{schema.mapping_coverage:.0f}% mapped",
                action="Review unmapped columns and update schema registry.",
            ))

        # ── Reconciliation insights ───────────────────────────────────────────────
        if reconciliation and reconciliation.discrepancy_count > 0:
            insights.append(Insight(
                category="opportunity",
                severity="critical" if reconciliation.total_recoverable > Decimal("1000") else "warning",
                title=f"{reconciliation.discrepancy_count} Discrepancies Found",
                message=(
                    f"{reconciliation.discrepancy_count} discrepancies totalling "
                    f"₹{reconciliation.total_leakage:.0f} in leakage. "
                    f"Recoverable: ₹{reconciliation.total_recoverable:.0f}."
                ),
                metric_value=f"₹{reconciliation.total_recoverable:.0f}",
                action="Review discrepancies and raise disputes with the marketplace.",
            ))

        # ── Readiness insights ────────────────────────────────────────────────────
        if readiness and readiness.recommended_uploads:
            insights.append(Insight(
                category="compliance",
                severity="info",
                title="Additional Reports Needed for Full Reconciliation",
                message=(
                    f"Missing: {', '.join(readiness.recommended_uploads)}. "
                    f"Current readiness: {readiness.readiness_score:.0f}%."
                ),
                metric_value=f"{readiness.readiness_score:.0f}%",
                action=f"Upload {', '.join(readiness.recommended_uploads)} for complete analysis.",
            ))

        # Sort: critical first, then warning, then info
        _severity_order = {"critical": 0, "warning": 1, "info": 2}
        insights.sort(key=lambda i: _severity_order.get(i.severity, 3))

        critical_count = sum(1 for i in insights if i.severity == "critical")
        opportunity_amount = (
            reconciliation.total_recoverable
            if reconciliation else Decimal("0")
        )

        status = (
            AgentStatus.warning if critical_count > 0
            else AgentStatus.success
        )

        return InsightsResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=[],
            insights=insights,
            total_insights=len(insights),
            critical_count=critical_count,
            opportunity_amount=opportunity_amount,
        )
