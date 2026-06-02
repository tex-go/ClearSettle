"""
Agent 7: Financial Understanding.

Extracts financial fields from:
  1. parsed_data in context (if pre-parsed data exists from existing parsers)
  2. Fallback: sample rows via universal field mappings from schema agent

Aggregates: gross_revenue, total_fees, net_settlement, commission,
            shipping, returns, tcs, tds, gst, advertising_spend.
"""
from __future__ import annotations

import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from app.services.intelligence.models import (
    AgentStatus, FinancialField, FinancialResult,
)


def _ff(field: str, value: Decimal, col: Optional[str] = None) -> FinancialField:
    return FinancialField(field=field, value=value, currency="INR", column_source=col)


def _to_decimal(val: Any) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        cleaned = str(val).replace(",", "").replace("₹", "").replace(" ", "").strip()
        if cleaned in ("", "-", "N/A", "n/a"):
            return Decimal("0")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0")


class AgentFinancial:
    AGENT_ID = 7
    AGENT_NAME = "Agent 7: Financial Understanding"

    def run(self, context: dict) -> FinancialResult:
        start = time.time()
        try:
            result = self._process(context)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            zero = Decimal("0")
            return FinancialResult(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                status=AgentStatus.error,
                duration_ms=(time.time() - start) * 1000,
                messages=[str(e)],
                period_start=None,
                period_end=None,
                currency="INR",
                revenue=_ff("revenue", zero),
                settlement=_ff("settlement", zero),
                total_fees=_ff("total_fees", zero),
                commission=_ff("commission", zero),
                shipping=_ff("shipping", zero),
                returns=_ff("returns", zero),
                refunds=_ff("refunds", zero),
                tcs=_ff("tcs", zero),
                tds=_ff("tds", zero),
                gst=_ff("gst", zero),
                adjustments=_ff("adjustments", zero),
                advertising_spend=_ff("advertising_spend", zero),
                net_payout=_ff("net_payout", zero),
                fact_model={},
            )

    def _process(self, context: dict) -> FinancialResult:
        parsed_data: Dict[str, Any] = context.get("parsed_data") or {}
        schema_result = context.get("schema")
        fp = context.get("fingerprint")
        messages: List[str] = []

        # Try to use pre-parsed summary first
        summary = parsed_data.get("summary") or {}
        orders: List[Dict] = parsed_data.get("orders") or []

        # Build field→column mapping from schema
        field_to_col: Dict[str, str] = {}
        if schema_result and schema_result.mapped_fields:
            for fm in schema_result.mapped_fields:
                field_to_col[fm.universal_field] = fm.source_column

        # Accumulate totals
        gross_revenue = Decimal("0")
        net_settlement = Decimal("0")
        commission = Decimal("0")
        shipping = Decimal("0")
        returns = Decimal("0")
        refunds = Decimal("0")
        tcs = Decimal("0")
        tds = Decimal("0")
        gst = Decimal("0")
        adjustments = Decimal("0")
        ad_spend = Decimal("0")

        if summary:
            # Use pre-parsed summary
            gross_revenue = _to_decimal(summary.get("gross_revenue") or summary.get("gross_sales") or 0)
            net_settlement = _to_decimal(summary.get("net_settlement") or summary.get("net_payout") or 0)
            commission = _to_decimal(summary.get("commission") or summary.get("total_commission") or 0)
            shipping = _to_decimal(summary.get("shipping_fee") or summary.get("shipping") or 0)
            returns = _to_decimal(summary.get("return_value") or summary.get("returns") or 0)
            refunds = _to_decimal(summary.get("refund_amount") or summary.get("refunds") or 0)
            tcs = _to_decimal(summary.get("tcs") or 0)
            tds = _to_decimal(summary.get("tds") or 0)
            gst = _to_decimal(summary.get("gst") or summary.get("gst_on_fees") or 0)
            adjustments = _to_decimal(summary.get("adjustments") or 0)
            ad_spend = _to_decimal(summary.get("advertising_spend") or summary.get("ad_spend") or 0)
            messages.append("Financial data sourced from pre-parsed summary.")

        elif orders:
            # Aggregate from order rows
            gross_col = field_to_col.get("gross_amount", "gross_amount")
            net_col = field_to_col.get("net_settlement", "net_settlement")
            comm_col = field_to_col.get("commission", "commission")
            ship_col = field_to_col.get("shipping_fee", "shipping_fee")
            ret_col = field_to_col.get("return_value", "return_value")
            tcs_col = field_to_col.get("tcs", "tcs")
            tds_col = field_to_col.get("tds", "tds")
            gst_col = field_to_col.get("gst_on_fees", "gst_on_fees")

            for order in orders:
                gross_revenue += _to_decimal(order.get(gross_col) or order.get("gross_amount"))
                net_settlement += _to_decimal(order.get(net_col) or order.get("net_settlement"))
                commission += _to_decimal(order.get(comm_col) or order.get("commission"))
                shipping += _to_decimal(order.get(ship_col) or order.get("shipping_fee"))
                returns += _to_decimal(order.get(ret_col) or order.get("return_value"))
                tcs += _to_decimal(order.get(tcs_col) or order.get("tcs"))
                tds += _to_decimal(order.get(tds_col) or order.get("tds"))
                gst += _to_decimal(order.get(gst_col) or order.get("gst_on_fees"))

            messages.append(f"Financial data aggregated from {len(orders)} order rows.")

        elif fp:
            # Last resort: scan sample rows using schema mapping
            all_samples: List[Dict] = []
            for sh in fp.sheets:
                all_samples.extend(sh.sample_rows)

            gross_col = field_to_col.get("gross_amount", "")
            net_col = field_to_col.get("net_settlement", "")
            comm_col = field_to_col.get("commission", "")
            ship_col = field_to_col.get("shipping_fee", "")
            tcs_col = field_to_col.get("tcs", "")
            tds_col = field_to_col.get("tds", "")
            gst_col = field_to_col.get("gst_on_fees", "")

            for row in all_samples:
                if gross_col:
                    gross_revenue += _to_decimal(row.get(gross_col))
                if net_col:
                    net_settlement += _to_decimal(row.get(net_col))
                if comm_col:
                    commission += _to_decimal(row.get(comm_col))
                if ship_col:
                    shipping += _to_decimal(row.get(ship_col))
                if tcs_col:
                    tcs += _to_decimal(row.get(tcs_col))
                if tds_col:
                    tds += _to_decimal(row.get(tds_col))
                if gst_col:
                    gst += _to_decimal(row.get(gst_col))

            messages.append(f"Financial data estimated from {len(all_samples)} sample rows only.")

        total_fees = abs(commission) + abs(shipping) + abs(tcs) + abs(tds) + abs(gst)

        # Net payout = gross - fees - returns
        if net_settlement == Decimal("0") and gross_revenue != Decimal("0"):
            net_settlement = gross_revenue - total_fees - abs(returns)

        fact_model: Dict[str, Any] = {
            "gross_revenue": str(gross_revenue),
            "total_fees": str(total_fees),
            "net_settlement": str(net_settlement),
            "commission": str(commission),
            "shipping": str(shipping),
            "returns": str(returns),
            "tcs": str(tcs),
            "tds": str(tds),
            "gst": str(gst),
        }

        status = AgentStatus.warning if gross_revenue == Decimal("0") else AgentStatus.success
        if gross_revenue == Decimal("0"):
            messages.append("Could not extract gross revenue — financial data may be incomplete.")

        return FinancialResult(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            status=status,
            duration_ms=0.0,
            messages=messages,
            period_start=None,
            period_end=None,
            currency="INR",
            revenue=_ff("revenue", gross_revenue, field_to_col.get("gross_amount")),
            settlement=_ff("settlement", net_settlement, field_to_col.get("net_settlement")),
            total_fees=_ff("total_fees", total_fees),
            commission=_ff("commission", abs(commission), field_to_col.get("commission")),
            shipping=_ff("shipping", abs(shipping), field_to_col.get("shipping_fee")),
            returns=_ff("returns", abs(returns), field_to_col.get("return_value")),
            refunds=_ff("refunds", abs(refunds)),
            tcs=_ff("tcs", abs(tcs), field_to_col.get("tcs")),
            tds=_ff("tds", abs(tds), field_to_col.get("tds")),
            gst=_ff("gst", abs(gst), field_to_col.get("gst_on_fees")),
            adjustments=_ff("adjustments", adjustments),
            advertising_spend=_ff("advertising_spend", abs(ad_spend)),
            net_payout=_ff("net_payout", net_settlement, field_to_col.get("net_settlement")),
            fact_model=fact_model,
        )
