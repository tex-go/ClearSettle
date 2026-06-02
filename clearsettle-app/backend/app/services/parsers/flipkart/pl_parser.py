"""
Flipkart P&L Report Parser Adapter.

Wraps the existing app.services.flipkart.parser.parse_flipkart_excel
and normalises its output into LedgerRecord instances.

Each order row → 1 LedgerRecord (transaction_type = 'sale' or 'return').
Each SKU row is not written to the ledger (it's a summary, not a transaction).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from app.services.parsers.base import BaseParser, LedgerRecord, ParseResult

logger = logging.getLogger(__name__)


class FlipkartPLParser(BaseParser):
    parser_name = "FlipkartPLParser"
    platform    = "flipkart"
    report_type = "pl_report"

    def parse(self, file_bytes: bytes, **kwargs: Any) -> ParseResult:
        result = self._make_result(schema_version="flipkart_pl_v1")

        try:
            from app.services.flipkart.parser import parse_flipkart_excel
            parsed = parse_flipkart_excel(file_bytes)
        except Exception as exc:
            result.errors.append(f"Flipkart PL parse failed: {exc}")
            return result

        result.errors.extend(parsed.get("errors", []))
        result.raw_summary = parsed.get("summary", {}) or {}

        order_rows = parsed.get("order_rows") or []
        sku_rows   = parsed.get("sku_rows") or []

        # Derive top-level KPIs for raw_summary
        if not result.raw_summary and sku_rows:
            result.raw_summary["sku_count"] = len(sku_rows)
        result.raw_summary["order_count"] = len(order_rows)

        for i, row in enumerate(order_rows):
            status = (row.get("status") or "").lower()
            tx_type = "return" if status in ("returned", "return") else "sale"

            gross   = self._safe_decimal(row.get("gross_amount"))
            net     = self._safe_decimal(row.get("net_earnings"))
            comm    = self._safe_decimal(row.get("commission"))
            ship    = self._safe_decimal(row.get("shipping_charges"))
            rship   = self._safe_decimal(row.get("reverse_shipping"))
            other   = self._safe_decimal(row.get("other_fees"))

            # Total fees as a single fee record
            total_fees = sum(
                abs(x) for x in [comm, ship, rship, other]
                if x is not None
            )

            rec = LedgerRecord(
                platform=self.platform,
                report_type=self.report_type,
                order_id=self._safe_str(row.get("order_id")),
                sku=self._safe_str(row.get("sku_code")),
                product_title=self._safe_str(row.get("product_title")),
                category=self._safe_str(row.get("category")),
                transaction_type=tx_type,
                amount=gross,
                tax_amount=None,
                currency="INR",
                transaction_date=self._safe_date(row.get("order_date")),
                settlement_date=self._safe_date(row.get("settlement_date")),
                return_status=self._safe_str(row.get("status")),
                payout_status=self._safe_str(row.get("settlement_status")),
                source_row_number=i,
                lineage_metadata={
                    "sheet":     "Order Wise P&L",
                    "net_amount": float(net) if net is not None else None,
                    "commission": float(comm) if comm is not None else None,
                    "shipping":   float(ship) if ship is not None else None,
                    "reverse_shipping": float(rship) if rship is not None else None,
                    "other_fees": float(other) if other is not None else None,
                    "total_fees": float(total_fees),
                },
            )
            result.ledger_records.append(rec)

            # Run base reconciliation and collect issues
            if gross and net:
                expected = gross - Decimal(str(total_fees))
                variance = abs(expected - net) if net else None
                if variance and variance > Decimal("1"):
                    result.warnings.append(
                        f"Row {i}: order {rec.order_id} variance ₹{float(variance):.2f}"
                    )

        return result
