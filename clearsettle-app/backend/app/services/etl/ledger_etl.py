"""
Ledger ETL: ingestion_ledger → settlements + payout_events

This is the critical post-ingestion step that was missing, causing the dashboard
to show ₹0 even after successful file uploads.

Call order (in _run_ingestion step 7):
  await run_ledger_etl(db, uploaded_file_id, company_id, platform)

What it does:
  1. Reads all IngestionLedger rows for the uploaded file
  2. Groups by settlement_id (falls back to one group per uploaded_file)
  3. Per group: creates or updates a Settlement row
  4. Per settlement with a payout amount: creates or updates a PayoutEvent row

After this runs, get_dashboard_summary() returns real numbers instead of ₹0.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ingestion import IngestionLedger
from app.db.models.payout_event import PayoutEvent
from app.db.models.settlement import Settlement

logger = logging.getLogger(__name__)

# Transaction types that map to each bucket
_SALE_TYPES    = frozenset({"sale", "order", "sold", "my_share", "forward"})
_RETURN_TYPES  = frozenset({"return", "returned", "refund", "rto", "reverse"})
_FEE_TYPES     = frozenset({
    "fee", "commission", "fixed_fee", "shipping_fee", "reverse_shipping",
    "collection_fee", "marketplace_fee", "platform_fee",
})
_TAX_TYPES     = frozenset({"tax", "tds", "tcs", "gst", "tax_tds", "tax_tcs"})
_PAYOUT_TYPES  = frozenset({
    "payout", "settlement", "transfer", "bank_settlement",
    "net_settlement", "neft", "remittance",
})


async def run_ledger_etl(
    db: AsyncSession,
    uploaded_file_id: UUID,
    company_id: UUID,
    platform: Optional[str] = None,
) -> dict:
    """
    Run the ETL that converts ingestion_ledger rows into the settlements +
    payout_events tables consumed by the dashboard.

    Returns a summary dict for logging.
    """
    fid = str(uploaded_file_id)
    logger.info(
        "LEDGER_ETL start",
        extra={"file_id": fid, "company_id": str(company_id), "platform": platform},
    )

    rows: List[IngestionLedger] = (
        await db.execute(
            select(IngestionLedger)
            .where(IngestionLedger.uploaded_file_id == uploaded_file_id)
        )
    ).scalars().all()

    if not rows:
        logger.warning("LEDGER_ETL no rows found", extra={"file_id": fid})
        return {"settlements_created": 0, "settlements_updated": 0, "payouts_upserted": 0}

    # ── Group rows by settlement key ──────────────────────────────────────────
    # Key = (platform, settlement_id) if settlement_id exists,
    #       else (platform, "file_{uploaded_file_id}")
    _plat = (platform or rows[0].platform or "unknown").lower()

    groups: Dict[str, dict] = defaultdict(lambda: {
        "platform":       _plat,
        "settlement_id":  None,
        "gross":          Decimal("0"),
        "returns":        Decimal("0"),
        "fees":           Decimal("0"),
        "taxes":          Decimal("0"),
        "payout":         Decimal("0"),
        "order_ids":      set(),
        "dates":          [],
        "settlement_dates": [],
    })

    for r in rows:
        row_plat = (r.platform or _plat).lower()
        ext_id   = r.settlement_id or f"file_{fid}"
        grp_key  = f"{row_plat}::{ext_id}"
        g        = groups[grp_key]
        g["platform"]      = row_plat
        g["settlement_id"] = r.settlement_id or f"file_{fid}"
        amt = r.amount or Decimal("0")
        tx  = (r.transaction_type or "").lower()

        if tx in _SALE_TYPES:
            g["gross"] += amt
        elif tx in _RETURN_TYPES:
            g["returns"] += amt     # returns are typically negative amounts
        elif tx in _FEE_TYPES:
            g["fees"] += amt        # fees are typically negative
        elif tx in _TAX_TYPES:
            g["taxes"] += amt
        elif tx in _PAYOUT_TYPES:
            g["payout"] += amt

        if r.order_id:
            g["order_ids"].add(r.order_id)
        if r.transaction_date:
            g["dates"].append(r.transaction_date)
        if r.settlement_date:
            g["settlement_dates"].append(r.settlement_date)

    # ── Upsert into settlements + payout_events ───────────────────────────────
    created = 0
    updated = 0
    payouts = 0

    for grp_key, g in groups.items():
        row_platform = g["platform"]
        ext_id       = g["settlement_id"]
        gross        = g["gross"]
        returns      = g["returns"]
        fees         = g["fees"]
        taxes        = g["taxes"]
        payout_amt   = g["payout"]
        order_count  = len(g["order_ids"])

        total_amount = gross + returns  # returns usually negative → reduces total
        # If no explicit payout rows, estimate from gross+returns+fees+taxes
        if payout_amt == 0:
            payout_amt = total_amount + fees + taxes

        # Parse period dates
        all_dates = sorted(set(g["dates"] + g["settlement_dates"]))
        period_start: Optional[datetime] = None
        period_end:   Optional[datetime] = None
        if all_dates:
            try:
                period_start = datetime.fromisoformat(all_dates[0][:10])
                period_end   = datetime.fromisoformat(all_dates[-1][:10])
            except ValueError:
                pass

        # Status: 'closed' if we have a positive payout, else 'open'
        settle_status = "closed" if payout_amt > 0 else "open"

        # ── Check if Settlement already exists ────────────────────────────────
        existing_settle = (
            await db.execute(
                select(Settlement).where(
                    Settlement.company_id == company_id,
                    Settlement.platform   == row_platform,
                    Settlement.external_id == ext_id,
                )
            )
        ).scalar_one_or_none()

        if existing_settle:
            # Update totals — this file may be a re-upload
            existing_settle.total_amount       = total_amount
            existing_settle.fees_total         = abs(fees) + abs(taxes)
            existing_settle.transactions_count = order_count
            existing_settle.status             = settle_status
            if period_start:
                existing_settle.period_start = period_start
            if period_end:
                existing_settle.period_end = period_end
                existing_settle.fund_transfer_date = period_end
            settle_obj = existing_settle
            updated += 1
        else:
            settle_obj = Settlement(
                id=uuid.uuid4(),
                company_id=company_id,
                platform=row_platform,
                external_id=ext_id,
                status=settle_status,
                currency="INR",
                total_amount=total_amount,
                fund_transfer_amount=payout_amt,
                fees_total=abs(fees) + abs(taxes),
                transactions_count=order_count,
                period_start=period_start,
                period_end=period_end,
                fund_transfer_date=period_end,
            )
            db.add(settle_obj)
            await db.flush()   # get settle_obj.id before payout_event FK
            created += 1

        # ── Upsert PayoutEvent ────────────────────────────────────────────────
        if payout_amt != 0:
            existing_payout = (
                await db.execute(
                    select(PayoutEvent).where(
                        PayoutEvent.settlement_id == settle_obj.id,
                    )
                )
            ).scalar_one_or_none()

            payout_status = "transferred" if payout_amt > 0 else "pending"

            if existing_payout:
                existing_payout.amount        = payout_amt
                existing_payout.status        = payout_status
                existing_payout.transfer_date = period_end
            else:
                db.add(PayoutEvent(
                    id=uuid.uuid4(),
                    settlement_id=settle_obj.id,
                    company_id=company_id,
                    platform=row_platform,
                    status=payout_status,
                    currency="INR",
                    amount=payout_amt,
                    transfer_date=period_end,
                ))
            payouts += 1

    await db.commit()

    summary = {
        "settlements_created": created,
        "settlements_updated": updated,
        "payouts_upserted":    payouts,
        "groups_processed":    len(groups),
        "ledger_rows_read":    len(rows),
    }
    logger.info("LEDGER_ETL complete", extra={"file_id": fid, **summary})
    return summary
