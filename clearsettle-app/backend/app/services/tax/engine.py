"""
Tax extraction engine — processes a Settlement into TaxLedgerEntry rows.

Idempotency
-----------
All existing TaxLedgerEntry rows for a settlement are deleted before new
ones are inserted, so calling process_settlement() twice is always safe.

Fee handling
------------
Fees are loaded from Settlement.fees (the denormalised direct relationship),
which avoids traversing SettlementTransaction for each fee.

Amounts
-------
Fee.amount is negative (deductions) — we work with abs() throughout.
SettlementTransaction.principal_amount is positive for shipments and
negative for refunds; we use abs() and steer by transaction_type.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.settlement import Settlement
from app.db.models.settlement_transaction import SettlementTransaction
from app.db.models.tax_ledger_entry import TaxLedgerEntry
from app.services.tax.calculator import (
    GST_RATE_ON_FEES,
    TCS_RATE,
    compute_tcs_taxable_base,
    gst_from_inclusive,
    is_tcs_fee,
    split_igst,
)

logger = logging.getLogger(__name__)

ZERO = Decimal("0")


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class TaxExtractionResult:
    settlement_id:          UUID
    period:                 str
    platform:               str
    entries_created:        int          = 0
    tcs_total:              Decimal      = field(default_factory=lambda: ZERO)
    gst_on_fees_total:      Decimal      = field(default_factory=lambda: ZERO)
    gross_sales:            Decimal      = field(default_factory=lambda: ZERO)
    refund_amount:          Decimal      = field(default_factory=lambda: ZERO)
    fees_processed:         int          = 0
    transactions_processed: int          = 0
    error_message:          Optional[str] = None


# ── Period helper ─────────────────────────────────────────────────────────────

def _period(s: Settlement) -> str:
    """Return 'YYYY-MM' from the settlement's period or transfer date."""
    dt: Optional[datetime] = s.period_start or s.fund_transfer_date
    if dt is None:
        dt = getattr(s, "created_at", None) or datetime.utcnow()
    return dt.strftime("%Y-%m")


# ── Core processor ────────────────────────────────────────────────────────────

async def process_settlement(
    db: AsyncSession,
    settlement_id: UUID,
    company_id: UUID,
    *,
    supply_type: str = "inter_state",
) -> TaxExtractionResult:
    """
    Extract GST/TCS ledger entries for one settlement and persist them.

    Deletes any existing entries for this settlement before inserting fresh
    ones — re-running is always safe and produces a clean ledger.

    Returns a TaxExtractionResult summary of what was extracted.
    """
    # Load settlement with fees and transactions (with their fees)
    res = await db.execute(
        select(Settlement)
        .where(Settlement.id == settlement_id, Settlement.company_id == company_id)
        .options(
            selectinload(Settlement.fees),
            selectinload(Settlement.transactions).selectinload(SettlementTransaction.fees),
        )
    )
    settlement = res.scalar_one_or_none()
    if not settlement:
        return TaxExtractionResult(
            settlement_id=settlement_id,
            period="unknown",
            platform="unknown",
            error_message="Settlement not found or access denied.",
        )

    period = _period(settlement)
    result = TaxExtractionResult(
        settlement_id=settlement_id,
        period=period,
        platform=settlement.platform,
    )

    # Idempotency: wipe existing entries for this settlement
    await db.execute(
        delete(TaxLedgerEntry).where(TaxLedgerEntry.settlement_id == settlement_id)
    )

    entries: list[TaxLedgerEntry] = []

    # ── Process settlement-level fees ─────────────────────────────────────────
    for fee in settlement.fees:
        abs_amt = abs(fee.amount) if fee.amount else ZERO
        if abs_amt == ZERO:
            continue
        result.fees_processed += 1

        if is_tcs_fee(fee.fee_type):
            # TCS deducted by marketplace (Section 52 CGST Act)
            igst, cgst, sgst = split_igst(abs_amt, supply_type)
            entries.append(TaxLedgerEntry(
                company_id=company_id,
                settlement_id=settlement_id,
                platform=settlement.platform,
                period=period,
                entry_type="tcs_deducted",
                fee_id=fee.id,
                transaction_id=fee.transaction_id,
                fee_type=fee.fee_type,
                taxable_amount=compute_tcs_taxable_base(abs_amt),
                tax_rate_pct=TCS_RATE,
                tax_amount=abs_amt,
                igst_amount=igst,
                cgst_amount=cgst,
                sgst_amount=sgst,
                supply_type=supply_type,
                is_reversal=False,
            ))
            result.tcs_total += abs_amt

        else:
            # Marketplace fee — 18% GST reverse-calculated from inclusive amount
            taxable_base, gst_amount = gst_from_inclusive(abs_amt)
            if gst_amount == ZERO:
                continue
            igst, cgst, sgst = split_igst(gst_amount, supply_type)
            entries.append(TaxLedgerEntry(
                company_id=company_id,
                settlement_id=settlement_id,
                platform=settlement.platform,
                period=period,
                entry_type="gst_on_fee",
                fee_id=fee.id,
                transaction_id=fee.transaction_id,
                fee_type=fee.fee_type,
                taxable_amount=taxable_base,
                tax_rate_pct=GST_RATE_ON_FEES,
                tax_amount=gst_amount,
                igst_amount=igst,
                cgst_amount=cgst,
                sgst_amount=sgst,
                supply_type=supply_type,
                is_reversal=False,
            ))
            result.gst_on_fees_total += gst_amount

    # ── Process transactions ──────────────────────────────────────────────────
    for txn in settlement.transactions:
        principal = txn.principal_amount or ZERO
        abs_principal = abs(principal)

        if txn.transaction_type == "shipment" and abs_principal > ZERO:
            result.gross_sales += abs_principal
            result.transactions_processed += 1
            # GST on sale — stored informational (rate unknown without HSN/category)
            entries.append(TaxLedgerEntry(
                company_id=company_id,
                settlement_id=settlement_id,
                platform=settlement.platform,
                period=period,
                entry_type="gst_on_sale",
                transaction_id=txn.id,
                order_id=txn.order_id,
                taxable_amount=abs_principal,
                tax_rate_pct=ZERO,
                tax_amount=ZERO,
                igst_amount=ZERO,
                cgst_amount=ZERO,
                sgst_amount=ZERO,
                supply_type=supply_type,
                is_reversal=False,
            ))

        elif txn.transaction_type == "refund" and abs_principal > ZERO:
            result.refund_amount += abs_principal
            result.transactions_processed += 1
            entries.append(TaxLedgerEntry(
                company_id=company_id,
                settlement_id=settlement_id,
                platform=settlement.platform,
                period=period,
                entry_type="gst_on_refund",
                transaction_id=txn.id,
                order_id=txn.order_id,
                taxable_amount=abs_principal,
                tax_rate_pct=ZERO,
                tax_amount=ZERO,
                igst_amount=ZERO,
                cgst_amount=ZERO,
                sgst_amount=ZERO,
                supply_type=supply_type,
                is_reversal=True,
            ))

    db.add_all(entries)
    result.entries_created = len(entries)

    logger.info(
        "tax.engine: settlement=%s period=%s entries=%d tcs=%s gst_on_fees=%s",
        settlement_id, period, len(entries),
        result.tcs_total, result.gst_on_fees_total,
    )
    return result


async def process_all_for_period(
    db: AsyncSession,
    company_id: UUID,
    platform: str,
    period: str,
    *,
    supply_type: str = "inter_state",
    limit: int = 200,
) -> list[TaxExtractionResult]:
    """
    Process all settlements whose period matches `period` (YYYY-MM).

    Matches on Settlement.period_start falling within the calendar month.
    Each settlement is processed independently; failures are collected and
    do not abort the batch.

    Does NOT commit — caller is responsible.
    """
    try:
        year, month = int(period[:4]), int(period[5:7])
    except (ValueError, IndexError):
        return []

    period_start = datetime(year, month, 1)
    if month == 12:
        period_end = datetime(year + 1, 1, 1)
    else:
        period_end = datetime(year, month + 1, 1)

    res = await db.execute(
        select(Settlement.id)
        .where(
            Settlement.company_id  == company_id,
            Settlement.platform    == platform,
            Settlement.period_start >= period_start,
            Settlement.period_start <  period_end,
        )
        .limit(limit)
    )
    ids = [row[0] for row in res.fetchall()]

    results: list[TaxExtractionResult] = []
    for sid in ids:
        try:
            r = await process_settlement(db, sid, company_id, supply_type=supply_type)
            results.append(r)
        except Exception as exc:
            logger.exception("tax.engine: batch failed for settlement %s", sid)
            results.append(TaxExtractionResult(
                settlement_id=sid,
                period=period,
                platform=platform,
                error_message=str(exc),
            ))

    return results
