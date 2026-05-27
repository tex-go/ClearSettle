"""
Monthly tax summary aggregation and CSV report generation.

build_monthly_summary()
    Aggregates TaxLedgerEntry rows for (company, platform, period) into a
    MonthlyTaxSummary row.  Deletes the existing summary before reinserting
    so repeated calls are always safe.

generate_ledger_csv()
    Returns a UTF-8 CSV string of ledger entries, suitable for download.

generate_summary_csv()
    Returns a UTF-8 CSV string of monthly summaries across all periods.
"""
from __future__ import annotations

import csv
import io
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.monthly_tax_summary import MonthlyTaxSummary
from app.db.models.tax_ledger_entry import TaxLedgerEntry

ZERO = Decimal("0")


async def build_monthly_summary(
    db: AsyncSession,
    company_id: UUID,
    platform: str,
    period: str,
) -> MonthlyTaxSummary:
    """
    Aggregate TaxLedgerEntry rows into a MonthlyTaxSummary for one period.

    Steps:
      1. GROUP BY entry_type — sum tax amounts and counts.
      2. Count distinct settlements for metadata.
      3. Delete any existing summary row (UNIQUE enforced by DB, safer to delete).
      4. Insert fresh MonthlyTaxSummary and return it.

    Caller must commit.
    """
    # Aggregate by entry_type
    agg_res = await db.execute(
        select(
            TaxLedgerEntry.entry_type,
            func.coalesce(func.sum(TaxLedgerEntry.taxable_amount), 0).label("taxable"),
            func.coalesce(func.sum(TaxLedgerEntry.tax_amount),     0).label("tax"),
            func.coalesce(func.sum(TaxLedgerEntry.igst_amount),    0).label("igst"),
            func.coalesce(func.sum(TaxLedgerEntry.cgst_amount),    0).label("cgst"),
            func.coalesce(func.sum(TaxLedgerEntry.sgst_amount),    0).label("sgst"),
            func.count(TaxLedgerEntry.id).label("cnt"),
        )
        .where(
            TaxLedgerEntry.company_id == company_id,
            TaxLedgerEntry.platform   == platform,
            TaxLedgerEntry.period     == period,
        )
        .group_by(TaxLedgerEntry.entry_type)
    )

    buckets: dict[str, dict] = {}
    for row in agg_res:
        buckets[row.entry_type] = {
            "taxable": Decimal(str(row.taxable)),
            "tax":     Decimal(str(row.tax)),
            "igst":    Decimal(str(row.igst)),
            "cgst":    Decimal(str(row.cgst)),
            "sgst":    Decimal(str(row.sgst)),
            "cnt":     int(row.cnt),
        }

    def _b(key: str) -> dict:
        return buckets.get(key, {
            "taxable": ZERO, "tax": ZERO,
            "igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cnt": 0,
        })

    tcs    = _b("tcs_deducted")
    fees   = _b("gst_on_fee")
    sales  = _b("gst_on_sale")
    refund = _b("gst_on_refund")

    gross_sales   = sales["taxable"]
    refund_amount = refund["taxable"]
    net_sales     = (gross_sales - refund_amount).quantize(Decimal("0.0001"))
    total_fees    = tcs["taxable"] + fees["taxable"]
    gst_on_fees   = fees["tax"]

    # Distinct settlements processed this period
    settle_count_res = await db.execute(
        select(func.count(func.distinct(TaxLedgerEntry.settlement_id)))
        .where(
            TaxLedgerEntry.company_id == company_id,
            TaxLedgerEntry.platform   == platform,
            TaxLedgerEntry.period     == period,
        )
    )
    settlements_processed = int(settle_count_res.scalar_one() or 0)

    # Delete previous summary (UNIQUE constraint, safe to replace)
    await db.execute(
        delete(MonthlyTaxSummary).where(
            MonthlyTaxSummary.company_id == company_id,
            MonthlyTaxSummary.platform   == platform,
            MonthlyTaxSummary.period     == period,
        )
    )

    summary = MonthlyTaxSummary(
        company_id=company_id,
        platform=platform,
        period=period,
        gross_sales=gross_sales,
        refund_amount=refund_amount,
        net_sales=net_sales,
        tcs_deducted=tcs["tax"],
        tcs_igst=tcs["igst"],
        tcs_cgst=tcs["cgst"],
        tcs_sgst=tcs["sgst"],
        total_fees=total_fees,
        gst_on_fees=gst_on_fees,
        igst_on_fees=fees["igst"],
        cgst_on_fees=fees["cgst"],
        sgst_on_fees=fees["sgst"],
        gst_on_refunds=refund["tax"],
        settlements_processed=settlements_processed,
        transactions_count=sales["cnt"] + refund["cnt"],
        fees_count=tcs["cnt"] + fees["cnt"],
        net_tcs_credit=tcs["tax"],
        itc_claimable=gst_on_fees,
    )
    db.add(summary)
    return summary


# ── CSV generators ────────────────────────────────────────────────────────────

def generate_ledger_csv(entries: list[TaxLedgerEntry]) -> str:
    """Return a CSV string of detailed ledger entries for download."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "ID", "Period", "Platform", "Entry Type",
        "Fee Type", "Order ID",
        "Taxable Amount (INR)", "Tax Rate %", "Tax Amount (INR)",
        "IGST (INR)", "CGST (INR)", "SGST (INR)",
        "Supply Type", "Is Reversal", "Created At",
    ])
    for e in entries:
        w.writerow([
            str(e.id),
            e.period,
            e.platform,
            e.entry_type,
            e.fee_type or "",
            e.order_id or "",
            float(e.taxable_amount or 0),
            float(e.tax_rate_pct or 0),
            float(e.tax_amount or 0),
            float(e.igst_amount or 0),
            float(e.cgst_amount or 0),
            float(e.sgst_amount or 0),
            e.supply_type or "inter_state",
            e.is_reversal,
            e.created_at.isoformat() if e.created_at else "",
        ])
    return buf.getvalue()


def generate_summary_csv(summaries: list[MonthlyTaxSummary]) -> str:
    """Return a CSV string of monthly tax summaries across periods."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "Period", "Platform",
        "Gross Sales (INR)", "Refund Amount (INR)", "Net Sales (INR)",
        "TCS Deducted (INR)", "TCS IGST", "TCS CGST", "TCS SGST",
        "Total Fees (INR)", "GST on Fees (INR)", "IGST on Fees", "CGST on Fees", "SGST on Fees",
        "GST on Refunds (INR)",
        "TCS Credit (GSTR-2A) (INR)", "ITC Claimable (INR)",
        "Settlements Processed", "Transactions", "Fee Lines",
        "Is Finalized",
    ])
    for s in summaries:
        w.writerow([
            s.period, s.platform,
            float(s.gross_sales or 0),
            float(s.refund_amount or 0),
            float(s.net_sales or 0),
            float(s.tcs_deducted or 0),
            float(s.tcs_igst or 0),
            float(s.tcs_cgst or 0),
            float(s.tcs_sgst or 0),
            float(s.total_fees or 0),
            float(s.gst_on_fees or 0),
            float(s.igst_on_fees or 0),
            float(s.cgst_on_fees or 0),
            float(s.sgst_on_fees or 0),
            float(s.gst_on_refunds or 0),
            float(s.net_tcs_credit or 0),
            float(s.itc_claimable or 0),
            s.settlements_processed or 0,
            s.transactions_count or 0,
            s.fees_count or 0,
            s.is_finalized,
        ])
    return buf.getvalue()
