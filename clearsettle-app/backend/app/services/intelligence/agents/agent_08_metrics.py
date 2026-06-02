"""
Agent 8: Metrics Generation.

Computes business KPIs from FinancialResult:
  - AOV = gross_sales / total_orders
  - settlement_efficiency = actual_settlement / expected_settlement * 100
  - fee_percentage = total_fees / gross_sales * 100
  - return_rate = return_value / gross_sales * 100
  - hidden_deductions = gross_sales - fees - returns - net_payout
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import List, Optional

from app.services.intelligence.models import AgentStatus, MetricsResult


class AgentMetrics:
    AGENT_ID = 8
    AGENT_NAME = "Agent 8: Metrics Generation"

    def run(self, context: dict) -> MetricsResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            zero = Decimal("0")
            return MetricsResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                gross_sales=zero,
                net_sales=zero,
                average_order_value=zero,
                total_orders=0,
                expected_settlement=zero,
                actual_settlement=zero,
                settlement_efficiency=0.0,
                return_rate=0.0,
                refund_rate=0.0,
                return_value=zero,
                total_marketplace_fees=zero,
                total_logistics_fees=zero,
                fee_percentage=0.0,
                hidden_deductions=zero,
                ad_spend=zero,
                acos=None,
                roas=None,
            )

    def _process(self, context: dict) -> MetricsResult:
        financial = context.get("financial")
        parsed_data = context.get("parsed_data") or {}
        messages: List[str] = []

        if financial is None:
            return MetricsResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.skipped,
                duration_ms=0.0,
                messages=["No financial data available — skipped."],
                gross_sales=Decimal("0"),
                net_sales=Decimal("0"),
                average_order_value=Decimal("0"),
                total_orders=0,
                expected_settlement=Decimal("0"),
                actual_settlement=Decimal("0"),
                settlement_efficiency=0.0,
                return_rate=0.0,
                refund_rate=0.0,
                return_value=Decimal("0"),
                total_marketplace_fees=Decimal("0"),
                total_logistics_fees=Decimal("0"),
                fee_percentage=0.0,
                hidden_deductions=Decimal("0"),
                ad_spend=Decimal("0"),
                acos=None,
                roas=None,
            )

        gross_sales = financial.revenue.value
        returns_val = financial.returns.value
        net_sales = gross_sales - returns_val
        total_fees = financial.total_fees.value
        commission = financial.commission.value
        shipping_fees = financial.shipping.value
        net_payout = financial.net_payout.value
        ad_spend = financial.advertising_spend.value
        refunds_val = financial.refunds.value

        # Total orders from parsed data or quality result
        quality = context.get("quality")
        total_orders = 0
        if parsed_data.get("summary", {}).get("total_orders"):
            total_orders = int(parsed_data["summary"]["total_orders"])
        elif quality:
            total_orders = max(quality.total_rows, 0)

        # AOV
        aov = (gross_sales / Decimal(str(total_orders))) if total_orders > 0 else Decimal("0")

        # Settlement efficiency
        expected_settlement = gross_sales - total_fees - returns_val
        actual_settlement = net_payout
        settlement_efficiency = 0.0
        if expected_settlement > Decimal("0"):
            settlement_efficiency = float(actual_settlement / expected_settlement * 100)
            settlement_efficiency = max(0.0, min(200.0, settlement_efficiency))

        # Return rate
        return_rate = 0.0
        if gross_sales > Decimal("0"):
            return_rate = float(returns_val / gross_sales * 100)

        # Refund rate
        refund_rate = 0.0
        if gross_sales > Decimal("0"):
            refund_rate = float(refunds_val / gross_sales * 100)

        # Fee percentage
        fee_percentage = 0.0
        if gross_sales > Decimal("0"):
            fee_percentage = float(total_fees / gross_sales * 100)

        # Hidden deductions (unexplained gap)
        hidden_deductions = gross_sales - total_fees - returns_val - net_payout
        if hidden_deductions < Decimal("0"):
            hidden_deductions = Decimal("0")

        # ACOS / ROAS
        acos: Optional[float] = None
        roas: Optional[float] = None
        if ad_spend > Decimal("0"):
            if net_sales > Decimal("0"):
                acos = float(ad_spend / net_sales * 100)
                roas = float(net_sales / ad_spend)

        if fee_percentage > 30:
            messages.append(f"High fee percentage: {fee_percentage:.1f}%")
        if settlement_efficiency < 85 and gross_sales > Decimal("0"):
            messages.append(f"Low settlement efficiency: {settlement_efficiency:.1f}%")
        if return_rate > 20:
            messages.append(f"High return rate: {return_rate:.1f}%")

        status = AgentStatus.warning if messages else AgentStatus.success

        return MetricsResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=messages,
            gross_sales=gross_sales,
            net_sales=net_sales,
            average_order_value=aov.quantize(Decimal("0.01")),
            total_orders=total_orders,
            expected_settlement=expected_settlement,
            actual_settlement=actual_settlement,
            settlement_efficiency=round(settlement_efficiency, 2),
            return_rate=round(return_rate, 2),
            refund_rate=round(refund_rate, 2),
            return_value=returns_val,
            total_marketplace_fees=commission,
            total_logistics_fees=shipping_fees,
            fee_percentage=round(fee_percentage, 2),
            hidden_deductions=hidden_deductions,
            ad_spend=ad_spend,
            acos=round(acos, 2) if acos is not None else None,
            roas=round(roas, 2) if roas is not None else None,
        )
