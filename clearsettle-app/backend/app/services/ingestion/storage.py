"""
Platform-agnostic settlement storage layer.

All functions accept an open AsyncSession and commit where noted.
Uses PostgreSQL INSERT ... ON CONFLICT for efficient upserts.

Duplicate protection
--------------------
  settlements:            UNIQUE (company_id, platform, external_id)
  settlement_transactions: UNIQUE (source_hash)
  fees:                   DELETE-then-INSERT per settlement (re-computed on each run)
  payout_events:          UNIQUE (settlement_id)
"""
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fee import Fee
from app.db.models.payout_event import PayoutEvent
from app.db.models.settlement import Settlement
from app.db.models.settlement_transaction import SettlementTransaction
from app.services.ingestion.models import (
    IngestionResult,
    NormalizedSettlement,
    NormalizedTransaction,
)

logger = logging.getLogger(__name__)


# ── Settlement ────────────────────────────────────────────────────────────────

async def upsert_settlement(
    db: AsyncSession,
    *,
    company_id: UUID,
    connection_id: UUID,
    platform: str,
    normalized: NormalizedSettlement,
) -> tuple[Settlement, bool]:
    """
    Insert or update a settlement row.
    Returns (settlement, created: bool).
    Does NOT commit — caller decides when to commit.
    """
    result = await db.execute(
        select(Settlement).where(
            Settlement.company_id  == company_id,
            Settlement.platform    == platform,
            Settlement.external_id == normalized.external_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.status               = normalized.status
        existing.total_amount         = normalized.total_amount
        existing.converted_amount     = normalized.converted_amount
        existing.fund_transfer_amount = normalized.fund_transfer_amount
        existing.beginning_balance    = normalized.beginning_balance
        existing.period_start         = normalized.period_start
        existing.period_end           = normalized.period_end
        existing.fund_transfer_date   = normalized.fund_transfer_date
        existing.account_tail         = normalized.account_tail
        existing.raw_data_json        = normalized.raw_data_json
        existing.updated_at           = datetime.utcnow()
        db.add(existing)
        return existing, False

    settlement = Settlement(
        id=uuid.uuid4(),
        company_id=company_id,
        connection_id=connection_id,
        platform=platform,
        external_id=normalized.external_id,
        status=normalized.status,
        currency=normalized.currency,
        total_amount=normalized.total_amount,
        converted_amount=normalized.converted_amount,
        fund_transfer_amount=normalized.fund_transfer_amount,
        beginning_balance=normalized.beginning_balance,
        period_start=normalized.period_start,
        period_end=normalized.period_end,
        fund_transfer_date=normalized.fund_transfer_date,
        account_tail=normalized.account_tail,
        raw_data_json=normalized.raw_data_json,
    )
    db.add(settlement)
    await db.flush()   # assigns id without committing
    return settlement, True


# ── Transactions ──────────────────────────────────────────────────────────────

async def upsert_transactions(
    db: AsyncSession,
    *,
    settlement: Settlement,
    company_id: UUID,
    platform: str,
    transactions: list[NormalizedTransaction],
) -> int:
    """
    Bulk-upsert all transactions for a settlement.

    Uses ON CONFLICT (source_hash) DO UPDATE to handle re-ingestion gracefully.
    Returns the number of rows inserted or updated.
    Does NOT commit.
    """
    if not transactions:
        return 0

    rows = [
        {
            "id":               uuid.uuid4(),
            "settlement_id":    settlement.id,
            "company_id":       company_id,
            "platform":         platform,
            "source_hash":      t.source_hash,
            "transaction_type": t.transaction_type,
            "order_id":         t.order_id,
            "order_item_id":    t.order_item_id,
            "sku":              t.sku,
            "marketplace":      t.marketplace,
            "posted_date":      t.posted_date,
            "quantity":         t.quantity,
            "currency":         t.currency,
            "principal_amount": t.principal_amount,
            "shipping_amount":  t.shipping_amount,
            "gift_wrap_amount": t.gift_wrap_amount,
            "promotion_amount": t.promotion_amount,
            "total_amount":     t.total_amount,
            "fees_total":       t.fees_total,
            "net_amount":       t.net_amount,
            "raw_data_json":    t.raw_data_json,
            "created_at":       datetime.utcnow(),
        }
        for t in transactions
    ]

    update_cols = {
        "total_amount":     pg_insert(SettlementTransaction).excluded.total_amount,
        "fees_total":       pg_insert(SettlementTransaction).excluded.fees_total,
        "net_amount":       pg_insert(SettlementTransaction).excluded.net_amount,
        "principal_amount": pg_insert(SettlementTransaction).excluded.principal_amount,
        "shipping_amount":  pg_insert(SettlementTransaction).excluded.shipping_amount,
        "gift_wrap_amount": pg_insert(SettlementTransaction).excluded.gift_wrap_amount,
        "promotion_amount": pg_insert(SettlementTransaction).excluded.promotion_amount,
        "raw_data_json":    pg_insert(SettlementTransaction).excluded.raw_data_json,
    }

    stmt = (
        pg_insert(SettlementTransaction)
        .values(rows)
        .on_conflict_do_update(
            constraint="uq_stxn_source_hash",
            set_=update_cols,
        )
    )
    await db.execute(stmt)

    return len(rows)


# ── Fees ──────────────────────────────────────────────────────────────────────

async def replace_fees(
    db: AsyncSession,
    *,
    settlement: Settlement,
    company_id: UUID,
    platform: str,
    transactions: list[NormalizedTransaction],
) -> int:
    """
    Replace all fees for a settlement: delete existing, bulk-insert new.

    Strategy: delete-then-insert (simpler than ON CONFLICT for child rows
    without a natural unique key). Safe because fees are always re-derived
    from the API response stored in raw_data_json.

    Returns total number of fee rows inserted.
    """
    # Delete all fees for this settlement (faster than per-transaction)
    await db.execute(
        delete(Fee).where(Fee.settlement_id == settlement.id)
    )

    # Map source_hash → DB transaction id
    result = await db.execute(
        select(SettlementTransaction.id, SettlementTransaction.source_hash)
        .where(SettlementTransaction.settlement_id == settlement.id)
    )
    txn_id_by_hash = {row.source_hash: row.id for row in result}

    fee_rows = []
    for t in transactions:
        txn_id = txn_id_by_hash.get(t.source_hash)
        if not txn_id:
            continue
        for f in t.fees:
            fee_rows.append({
                "id":             uuid.uuid4(),
                "transaction_id": txn_id,
                "settlement_id":  settlement.id,
                "company_id":     company_id,
                "platform":       platform,
                "fee_type":       f.fee_type,
                "fee_description": f.fee_description,
                "currency":       f.currency,
                "amount":         f.amount,
                "created_at":     datetime.utcnow(),
            })

    if fee_rows:
        await db.execute(pg_insert(Fee).values(fee_rows))

    return len(fee_rows)


# ── Settlement summaries ──────────────────────────────────────────────────────

async def update_settlement_summaries(
    db: AsyncSession,
    settlement: Settlement,
) -> None:
    """
    Re-compute transactions_count and fees_total on the settlement row
    from the child tables.  Does NOT commit.
    """
    from sqlalchemy import func

    txn_count = await db.execute(
        select(func.count(SettlementTransaction.id))
        .where(SettlementTransaction.settlement_id == settlement.id)
    )
    fee_sum = await db.execute(
        select(func.coalesce(func.sum(Fee.amount), 0))
        .where(Fee.settlement_id == settlement.id)
    )
    settlement.transactions_count = txn_count.scalar_one() or 0
    settlement.fees_total         = fee_sum.scalar_one() or Decimal("0")
    db.add(settlement)


# ── Payouts ───────────────────────────────────────────────────────────────────

async def upsert_payout(
    db: AsyncSession,
    *,
    settlement: Settlement,
    company_id: UUID,
    connection_id: UUID,
    platform: str,
    normalized: NormalizedSettlement,
) -> tuple[PayoutEvent, bool]:
    """
    Insert or update the payout event for a closed settlement.
    Does NOT commit.
    """
    result = await db.execute(
        select(PayoutEvent).where(PayoutEvent.settlement_id == settlement.id)
    )
    existing = result.scalar_one_or_none()

    amount = normalized.fund_transfer_amount or normalized.total_amount

    if existing:
        existing.status        = "transferred" if normalized.fund_transfer_date else "pending"
        existing.amount        = amount
        existing.transfer_date = normalized.fund_transfer_date
        existing.account_tail  = normalized.account_tail
        existing.updated_at    = datetime.utcnow()
        db.add(existing)
        return existing, False

    payout = PayoutEvent(
        id=uuid.uuid4(),
        settlement_id=settlement.id,
        company_id=company_id,
        connection_id=connection_id,
        platform=platform,
        status="transferred" if normalized.fund_transfer_date else "pending",
        currency=normalized.currency,
        amount=amount,
        transfer_date=normalized.fund_transfer_date,
        account_tail=normalized.account_tail,
    )
    db.add(payout)
    return payout, True
