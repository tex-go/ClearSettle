"""
Amazon Settlement Report Parser Adapter.

Wraps app.services.amazon.parser.parse_amazon_settlement_report and
normalises its output into LedgerRecord instances.

Each transaction row → 1 LedgerRecord.
Transaction type is mapped from Amazon's amount-type + amount-description.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.normalization.value_normalizer import normalize_fee_type
from app.services.parsers.base import BaseParser, LedgerRecord, ParseResult

logger = logging.getLogger(__name__)

_TX_TYPE_MAP = {
    "order":      "sale",
    "refund":     "return",
    "transfer":   "payout",
    "adjustment": "adjustment",
    "service_fee": "fee",
    "debt":       "fee",
    "subscription": "fee",
}

_AMOUNT_DESC_FEE_TYPES = {
    "commission":               "commission",
    "fbaperunitmfulfillmentfee": "fixed_fee",
    "fbaperunitfulfillmentfee": "fixed_fee",
    "shippinghb":               "shipping_fee",
    "shippingchargebacks":      "shipping_fee",
    "safetreinbursement":       "safe_t_claim",
    "warehousedamage":          "reimbursement",
    "disposalcompletereport":   "reimbursement",
    "tax":                      "gst_on_fees",
    "marketplacefacilitatortax": "tcs",
    "principal":                None,  # → amount, not a fee
    "shipping":                 "shipping_fee",
    "giftwrap":                 "other",
    "promotionshipping":        "other",
}


class AmazonSettlementParser(BaseParser):
    parser_name = "AmazonSettlementParser"
    platform    = "amazon"
    report_type = "settlement_report"

    def parse(self, file_bytes: bytes, **kwargs: Any) -> ParseResult:
        result = self._make_result(schema_version="amazon_settlement_v2")

        try:
            from app.services.amazon.parser import parse_amazon_settlement_report
            parsed = parse_amazon_settlement_report(file_bytes)
        except Exception as exc:
            result.errors.append(f"Amazon settlement parse failed: {exc}")
            return result

        result.errors.extend(parsed.get("errors", []))
        meta = parsed.get("meta") or {}
        result.raw_summary = {
            "settlement_id":    meta.get("settlement_id"),
            "start_date":       str(meta.get("settlement_start_date") or ""),
            "end_date":         str(meta.get("settlement_end_date") or ""),
            "deposit_date":     str(meta.get("deposit_date") or ""),
            "total_amount":     meta.get("total_amount"),
            "currency":         meta.get("currency", "INR"),
            "order_count":      len(parsed.get("order_rows") or []),
        }

        for i, row in enumerate(parsed.get("order_rows") or []):
            amazon_tx_type = (row.get("transaction_type") or "").lower().strip()
            tx_type = _TX_TYPE_MAP.get(amazon_tx_type, "adjustment")

            amount_type = (row.get("amount_type") or "").lower().replace("-", "").replace(" ", "")
            amount_desc = (row.get("amount_description") or "").lower().replace("-", "").replace(" ", "")
            raw_amount  = self._safe_decimal(row.get("amount"))

            # Classify as fee or sale amount
            fee_type = None
            if amount_type in ("itemfees", "othertransaction"):
                fee_type = _AMOUNT_DESC_FEE_TYPES.get(amount_desc, normalize_fee_type(amount_desc))
                tx_type  = "fee"
            elif amount_type == "itemwithheldtax":
                fee_type = "tcs"
                tx_type  = "tax"

            rec = LedgerRecord(
                platform=self.platform,
                report_type=self.report_type,
                order_id=self._safe_str(row.get("order_id")),
                shipment_id=self._safe_str(row.get("shipment_id")),
                settlement_id=self._safe_str(meta.get("settlement_id")),
                sku=self._safe_str(row.get("sku")),
                product_title=self._safe_str(row.get("product_name")),
                transaction_type=tx_type,
                fee_type=fee_type,
                amount=raw_amount,
                currency=meta.get("currency", "INR"),
                transaction_date=self._safe_date(row.get("posted_date")),
                settlement_date=self._safe_date(meta.get("deposit_date")),
                source_row_number=i,
                lineage_metadata={
                    "amount_type":   row.get("amount_type"),
                    "amount_desc":   row.get("amount_description"),
                    "marketplace":   row.get("marketplace"),
                    "fulfillment_id": row.get("fulfillment_id"),
                },
            )
            result.ledger_records.append(rec)

        # Run Amazon reconciliation
        try:
            from app.services.amazon.reconciliation import run_amazon_reconciliation
            issues = run_amazon_reconciliation(parsed.get("order_rows") or [])
            result.recon_issues = issues
        except Exception as exc:
            result.warnings.append(f"Amazon reconciliation step failed: {exc}")

        return result
