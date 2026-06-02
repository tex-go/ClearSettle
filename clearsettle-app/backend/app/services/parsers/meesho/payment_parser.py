"""
Meesho Payment Report Parser Adapter.

Wraps app.services.meesho.parser.parse_meesho_payment_report and
normalises its output into LedgerRecord instances.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.normalization.value_normalizer import normalize_fee_type
from app.services.parsers.base import BaseParser, LedgerRecord, ParseResult

logger = logging.getLogger(__name__)


class MeeshoPaymentParser(BaseParser):
    parser_name = "MeeshoPaymentParser"
    platform    = "meesho"
    report_type = "payment_report"

    def parse(self, file_bytes: bytes, **kwargs: Any) -> ParseResult:
        result = self._make_result(schema_version="meesho_payment_v1")

        try:
            from app.services.meesho.parser import parse_meesho_payment_report
            parsed = parse_meesho_payment_report(file_bytes)
        except Exception as exc:
            result.errors.append(f"Meesho payment parse failed: {exc}")
            return result

        result.errors.extend(parsed.get("errors", []))
        result.raw_summary = {
            "order_count":  len(parsed.get("order_rows") or []),
            "total_payout": parsed.get("summary", {}).get("total_net_payment"),
        }

        for i, row in enumerate(parsed.get("order_rows") or []):
            status  = (row.get("order_status") or row.get("status") or "").lower()
            tx_type = "return" if "return" in status else "sale"

            gross = self._safe_decimal(row.get("customer_paid_amount") or row.get("gross_amount"))
            net   = self._safe_decimal(row.get("net_payment") or row.get("net_earnings"))
            comm  = self._safe_decimal(row.get("commission"))
            ship  = self._safe_decimal(row.get("shipping_charges"))
            rship = self._safe_decimal(row.get("reverse_shipping_charges") or row.get("reverse_shipping"))
            tcs   = self._safe_decimal(row.get("tcs"))
            tds   = self._safe_decimal(row.get("tds"))

            rec = LedgerRecord(
                platform=self.platform,
                report_type=self.report_type,
                order_id=self._safe_str(row.get("order_id") or row.get("sub_order_id")),
                sku=self._safe_str(row.get("sku")),
                product_title=self._safe_str(row.get("product_name")),
                category=self._safe_str(row.get("category")),
                transaction_type=tx_type,
                amount=gross,
                currency="INR",
                transaction_date=self._safe_date(row.get("order_date")),
                settlement_date=self._safe_date(row.get("payment_date")),
                return_status=self._safe_str(row.get("order_status")),
                payout_status=self._safe_str(row.get("payment_status")),
                source_row_number=i,
                lineage_metadata={
                    "sheet":           "Payment Report",
                    "net_payment":     float(net) if net is not None else None,
                    "commission":      float(comm) if comm is not None else None,
                    "shipping":        float(ship) if ship is not None else None,
                    "reverse_shipping": float(rship) if rship is not None else None,
                    "tcs":             float(tcs) if tcs is not None else None,
                    "tds":             float(tds) if tds is not None else None,
                },
            )
            result.ledger_records.append(rec)

            # Emit fee-type records for significant deductions
            for fee_name, fee_val in [
                ("commission", comm),
                ("shipping_fee", ship),
                ("reverse_shipping", rship),
                ("tcs", tcs),
                ("tds", tds),
            ]:
                if fee_val and abs(fee_val) > 0:
                    result.ledger_records.append(LedgerRecord(
                        platform=self.platform,
                        report_type=self.report_type,
                        order_id=rec.order_id,
                        transaction_type="fee",
                        fee_type=fee_name,
                        amount=-abs(fee_val),
                        currency="INR",
                        transaction_date=rec.transaction_date,
                        source_row_number=i,
                        lineage_metadata={"sheet": "Payment Report", "fee_name": fee_name},
                    ))

        # Run Meesho reconciliation
        try:
            from app.services.meesho.reconciliation import run_meesho_reconciliation
            issues = run_meesho_reconciliation(parsed.get("order_rows") or [])
            result.recon_issues = issues
        except Exception as exc:
            result.warnings.append(f"Meesho reconciliation step failed: {exc}")

        return result
