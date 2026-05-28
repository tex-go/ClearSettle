"""
Flipkart Payment Report Parser Adapter.

Wraps app.services.flipkart.payment_parser.parse_flipkart_payment_report
(the 3-level merged-header quarterly Payment Report parser) and normalises
its output into LedgerRecord instances.

For each order row: 1 LedgerRecord for the sale/return amount.
For each GST detail row with a fee: 1 LedgerRecord for the fee deduction.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.normalization.value_normalizer import normalize_fee_type
from app.services.parsers.base import BaseParser, LedgerRecord, ParseResult

logger = logging.getLogger(__name__)


class FlipkartPaymentParser(BaseParser):
    parser_name = "FlipkartPaymentParser"
    platform    = "flipkart"
    report_type = "payment_report"

    def parse(self, file_bytes: bytes, **kwargs: Any) -> ParseResult:
        quarter_label = kwargs.get("quarter_label", "unknown")
        result = self._make_result(schema_version="flipkart_payment_v1")

        try:
            from app.services.flipkart.payment_parser import parse_flipkart_payment_report
            parsed = parse_flipkart_payment_report(file_bytes, quarter_label=quarter_label)
        except Exception as exc:
            result.errors.append(f"Flipkart Payment parse failed: {exc}")
            return result

        result.errors.extend(parsed.get("errors", []))
        result.raw_summary = {
            "quarter":      parsed.get("quarter"),
            "total_orders": parsed.get("total_orders"),
            "total_sale":   parsed.get("total_sale_amount"),
            "total_settlement": parsed.get("total_settlement"),
        }

        # ── Order rows → sale/return LedgerRecords ────────────────────────────
        for i, row in enumerate(parsed.get("order_rows") or []):
            tx_type = "return" if self._safe_str(row.get("return_type")) else "sale"
            amount  = self._safe_decimal(row.get("sale_amount"))

            rec = LedgerRecord(
                platform=self.platform,
                report_type=self.report_type,
                order_id=self._safe_str(row.get("order_item_id") or row.get("order_id")),
                sku=self._safe_str(row.get("seller_sku")),
                product_title=self._safe_str(row.get("product_title")),
                category=self._safe_str(row.get("category")),
                transaction_type=tx_type,
                amount=amount,
                currency="INR",
                transaction_date=self._safe_date(row.get("order_date")),
                settlement_date=self._safe_date(row.get("settlement_date")),
                payout_status=self._safe_str(row.get("settlement_status")),
                source_row_number=i,
                lineage_metadata={
                    "sheet":              "Payment Details",
                    "commission":         row.get("commission"),
                    "fixed_fee":          row.get("fixed_fee"),
                    "shipping_fee":       row.get("shipping_fee"),
                    "reverse_shipping_fee": row.get("reverse_shipping_fee"),
                    "commission_rate_pct":  row.get("commission_rate_pct"),
                    "settlement_amount":  row.get("settlement_amount"),
                },
            )
            result.ledger_records.append(rec)

        # ── GST detail rows → per-fee-type LedgerRecords ─────────────────────
        for j, row in enumerate(parsed.get("gst_rows") or []):
            fee_name = self._safe_str(row.get("fee_name")) or "other"
            fee_amt  = self._safe_decimal(row.get("fee_amount"))
            gst_amt  = self._safe_decimal(row.get("gst_amount"))

            if fee_amt is None and gst_amt is None:
                continue

            rec = LedgerRecord(
                platform=self.platform,
                report_type=self.report_type,
                order_id=self._safe_str(row.get("order_item_id")),
                transaction_type="fee",
                fee_type=normalize_fee_type(fee_name),
                amount=fee_amt,
                tax_amount=gst_amt,
                currency="INR",
                source_row_number=j,
                lineage_metadata={
                    "sheet":    "GST Details",
                    "fee_name": fee_name,
                    "is_suspect": fee_name.lower() == "wallet redeem",
                },
            )
            result.ledger_records.append(rec)

        # ── Run enhanced reconciliation ───────────────────────────────────────
        try:
            from app.services.flipkart.reconciliation import run_payment_report_reconciliation
            issues = run_payment_report_reconciliation(
                parsed.get("order_rows") or [],
                parsed.get("gst_rows") or [],
            )
            result.recon_issues = issues
        except Exception as exc:
            result.warnings.append(f"Reconciliation step failed: {exc}")

        return result
