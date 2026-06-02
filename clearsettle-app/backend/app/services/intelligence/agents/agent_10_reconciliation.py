"""
Agent 10: Reconciliation Intelligence.

If data quality > 60% and the report is a settlement/payment report:
  - Detects order vs settlement gaps
  - Detects commission rate overcharges (rate > platform max)
  - Detects returns without refunds

Works on parsed_data orders + ledger data from context.
"""
from __future__ import annotations

import time
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from app.services.intelligence.models import (
    AgentStatus, Discrepancy, ReconciliationResult,
)

# Known maximum commission rates per platform (%)
_MAX_COMMISSION_RATES: Dict[str, float] = {
    "flipkart": 25.0,
    "amazon":   40.0,
    "meesho":   20.0,
    "myntra":   35.0,
    "ajio":     30.0,
    "shopify":  3.0,
}

_SETTLEMENT_REPORT_TYPES = {
    "payment_report", "settlement_report", "pl_report",
}


def _to_decimal(val: Any) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val).replace(",", "").replace("₹", "").strip() or "0")
    except (InvalidOperation, ValueError):
        return Decimal("0")


class AgentReconciliation:
    AGENT_ID = 10
    AGENT_NAME = "Agent 10: Reconciliation Intelligence"

    def run(self, context: dict) -> ReconciliationResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            return ReconciliationResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                discrepancy_count=0,
                total_leakage=Decimal("0"),
                total_recoverable=Decimal("0"),
                discrepancies=[],
                reconciliation_type="none",
                summary={},
            )

    def _process(self, context: dict) -> ReconciliationResult:
        quality_result = context.get("quality")
        classification_result = context.get("classification")
        platform_result = context.get("platform")
        financial_result = context.get("financial")
        parsed_data = context.get("parsed_data") or {}

        platform = (platform_result.platform if platform_result else "unknown").lower()
        report_type = (classification_result.report_type if classification_result else "unknown").lower()
        quality_score = quality_result.quality_score if quality_result else 0.0

        discrepancies: List[Discrepancy] = []
        messages: List[str] = []

        # Only run full reconciliation if quality is sufficient
        if quality_score < 60.0:
            return ReconciliationResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.skipped,
                duration_ms=0.0,
                messages=[f"Quality score {quality_score:.0f}/100 too low for reconciliation (min 60)."],
                discrepancy_count=0,
                total_leakage=Decimal("0"),
                total_recoverable=Decimal("0"),
                discrepancies=[],
                reconciliation_type="skipped_low_quality",
                summary={"reason": "quality_score_below_threshold"},
            )

        recon_type = "order_vs_settlement" if report_type in _SETTLEMENT_REPORT_TYPES else "fee_audit"
        orders: List[Dict] = parsed_data.get("orders") or []

        # ── Check 1: Order vs Settlement gap ─────────────────────────────────────
        if financial_result and report_type in _SETTLEMENT_REPORT_TYPES:
            expected = financial_result.revenue.value
            actual = financial_result.net_payout.value
            fees = financial_result.total_fees.value
            returns = financial_result.returns.value
            computed_net = expected - fees - returns

            if actual > Decimal("0") and abs(computed_net - actual) > Decimal("1"):
                gap = computed_net - actual
                discrepancies.append(Discrepancy(
                    type="order_settlement_gap",
                    severity="high" if abs(gap) > 1000 else "medium",
                    order_id=None,
                    expected_amount=computed_net,
                    actual_amount=actual,
                    gap=gap,
                    description=(
                        f"Expected net settlement ₹{computed_net:.2f} "
                        f"but actual payout was ₹{actual:.2f}. "
                        f"Gap: ₹{gap:.2f}"
                    ),
                    recoverable=gap > Decimal("0"),
                ))

        # ── Check 2: Commission rate overcharge ──────────────────────────────────
        max_rate = _MAX_COMMISSION_RATES.get(platform, 50.0)
        for order in orders[:500]:  # cap at 500 for perf
            gross = _to_decimal(order.get("gross_amount") or order.get("gross_sales"))
            comm = abs(_to_decimal(order.get("commission")))
            if gross > Decimal("10") and comm > Decimal("0"):
                actual_rate = float(comm / gross * 100)
                if actual_rate > max_rate:
                    gap = comm - (gross * Decimal(str(max_rate / 100)))
                    discrepancies.append(Discrepancy(
                        type="fee_overcharge",
                        severity="high" if gap > Decimal("500") else "medium",
                        order_id=str(order.get("order_id", "")),
                        expected_amount=gross * Decimal(str(max_rate / 100)),
                        actual_amount=comm,
                        gap=gap,
                        description=(
                            f"Commission rate {actual_rate:.1f}% exceeds max {max_rate:.0f}% "
                            f"for {platform}. Overcharged ₹{gap:.2f}."
                        ),
                        recoverable=True,
                    ))

        # ── Check 3: Returns without refunds ─────────────────────────────────────
        returns_value = financial_result.returns.value if financial_result else Decimal("0")
        refunds_value = financial_result.refunds.value if financial_result else Decimal("0")
        if returns_value > Decimal("100") and refunds_value < returns_value * Decimal("0.5"):
            gap = returns_value - refunds_value
            discrepancies.append(Discrepancy(
                type="return_not_refunded",
                severity="medium",
                order_id=None,
                expected_amount=returns_value,
                actual_amount=refunds_value,
                gap=gap,
                description=(
                    f"Returns total ₹{returns_value:.2f} but only ₹{refunds_value:.2f} refunded. "
                    f"Unrefunded: ₹{gap:.2f}"
                ),
                recoverable=True,
            ))

        total_leakage = sum((d.gap for d in discrepancies if d.gap > 0), Decimal("0"))
        total_recoverable = sum((d.gap for d in discrepancies if d.recoverable and d.gap > 0), Decimal("0"))

        if discrepancies:
            messages.append(f"{len(discrepancies)} discrepancies found, ₹{total_recoverable:.2f} recoverable.")

        status = AgentStatus.warning if discrepancies else AgentStatus.success

        summary: Dict[str, Any] = {
            "platform": platform,
            "report_type": report_type,
            "discrepancy_count": len(discrepancies),
            "total_leakage": str(total_leakage),
            "total_recoverable": str(total_recoverable),
            "by_type": {
                d_type: sum(1 for d in discrepancies if d.type == d_type)
                for d_type in {"order_settlement_gap", "fee_overcharge", "return_not_refunded"}
            },
        }

        return ReconciliationResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=messages,
            discrepancy_count=len(discrepancies),
            total_leakage=total_leakage,
            total_recoverable=total_recoverable,
            discrepancies=discrepancies[:50],  # return at most 50
            reconciliation_type=recon_type,
            summary=summary,
        )
