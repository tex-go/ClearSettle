"""
Production-grade async SQLAlchemy 2 queries for settlement APIs.

Design principles
-----------------
* No N+1 — every list endpoint is a single JOIN query.
* Pagination at the DB level via LIMIT / OFFSET.
* Correlated scalar subquery for latest reconciliation status
  (one extra DB call per list page, not per row).
* All aggregations (fee breakdown, transaction summary) use GROUP BY
  in a single round-trip.
* Amounts returned as Python float; callers use them directly.
* Status / label mapping is centralised here so routers stay thin.

Index recommendations (apply via migration if not already present)
------------------------------------------------------------------
settlements(company_id, period_end DESC)      → list sort
settlements(company_id, platform, status)     → filtered lists
settlements(period_start, period_end)         → date-range filter
fees(settlement_id, fee_type)                 → fee breakdown GROUP BY
settlement_transactions(settlement_id, transaction_type) → txn filter
reconciliation_results(settlement_id, created_at DESC)   → correlated subquery
"""
from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fee import Fee
from app.db.models.payout_event import PayoutEvent
from app.db.models.reconciliation_result import ReconciliationResult
from app.db.models.settlement import Settlement
from app.db.models.settlement_transaction import SettlementTransaction
from app.schemas.settlements import (
    FeeBreakdownOut,
    FeeLineItemOut,
    PayoutItemOut,
    PayoutListResponse,
    PayoutOut,
    SettlementDetailOut,
    SettlementListItemOut,
    SettlementListResponse,
    SettlementSummaryOut,
    TransactionItemOut,
    TransactionListResponse,
    TransactionTypeSummaryOut,
)

# ── Label maps ────────────────────────────────────────────────────────────────

_PLATFORM_LABELS: dict[str, str] = {
    "amazon":   "Amazon",
    "flipkart": "Flipkart",
    "meesho":   "Meesho",
    "myntra":   "Myntra",
    "nykaa":    "Nykaa",
    "ajio":     "AJIO",
}

_STATUS_LABELS: dict[str, str] = {
    "closed":     "paid",
    "open":       "pending",
    "processing": "processing",
}

# Accepted status filter values → DB column values
_STATUS_FILTER_MAP: dict[str, str] = {
    "paid":       "closed",
    "closed":     "closed",
    "pending":    "open",
    "open":       "open",
    "processing": "processing",
}

# Valid sort column names → ORM column
_SORT_COLUMNS: dict[str, object] = {
    "period_end":           Settlement.period_end,
    "period_start":         Settlement.period_start,
    "total_amount":         Settlement.total_amount,
    "fund_transfer_amount": Settlement.fund_transfer_amount,
    "transactions_count":   Settlement.transactions_count,
    "created_at":           Settlement.created_at,
    "status":               Settlement.status,
}

# Fee type → breakdown category
_REFERRAL_TYPES = frozenset({"ReferralFee", "Commission"})
_FBA_TYPES      = frozenset({
    "FBAPerUnitFulfillmentFee", "FBAWeightBasedFee",
    "FBAInboundConvenienceFee", "FBARemovalFee",
})
_CLOSING_TYPES  = frozenset({"VariableClosingFee", "PerItemFee"})
_SHIPPING_TYPES = frozenset({"Shipping", "ShippingCharge", "ShippingHBFee", "ShippingTax"})


# ── Private helpers ───────────────────────────────────────────────────────────

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _platform_label(platform: str) -> str:
    return _PLATFORM_LABELS.get(platform.lower(), platform.title())


def _status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


def _period_label(start: datetime | None, end: datetime | None) -> str:
    if not start and not end:
        return "—"
    if start and end:
        sm = _MONTHS[start.month - 1]
        em = _MONTHS[end.month - 1]
        if start.year == end.year and start.month == end.month:
            return f"{sm} {start.day}–{end.day}, {end.year}"
        if start.year == end.year:
            return f"{sm} {start.day} – {em} {end.day}, {end.year}"
        return f"{sm} {start.day}, {start.year} – {em} {end.day}, {end.year}"
    if start:
        return f"{_MONTHS[start.month - 1]} {start.day}, {start.year}"
    assert end is not None
    return f"{_MONTHS[end.month - 1]} {end.day}, {end.year}"


def _f(v) -> float:
    """Safe Decimal / None → float conversion."""
    if v is None:
        return 0.0
    return float(v)


def _net_amount(s: Settlement) -> float:
    if s.fund_transfer_amount is not None:
        return _f(s.fund_transfer_amount)
    return _f(s.total_amount) + _f(s.fees_total)


def _settlement_to_list_item(
    s: Settlement,
    payout_status: str | None,
    recon_status: str | None,
) -> SettlementListItemOut:
    return SettlementListItemOut(
        id=s.id,
        external_id=s.external_id,
        platform=s.platform,
        platform_label=_platform_label(s.platform),
        status=s.status,
        status_label=_status_label(s.status),
        period_start=s.period_start,
        period_end=s.period_end,
        period_label=_period_label(s.period_start, s.period_end),
        currency=s.currency,
        total_amount=_f(s.total_amount),
        fees_total=_f(s.fees_total),
        fund_transfer_amount=_f(s.fund_transfer_amount) if s.fund_transfer_amount else None,
        net_amount=_net_amount(s),
        transactions_count=s.transactions_count or 0,
        fund_transfer_date=s.fund_transfer_date,
        account_tail=s.account_tail,
        payout_status=payout_status,
        reconciliation_status=recon_status,
        created_at=s.created_at,
    )


# ── Settlement list ───────────────────────────────────────────────────────────

async def list_settlements(
    db: AsyncSession,
    *,
    company_id: UUID,
    platform:   str | None  = None,
    status:     str | None  = None,
    date_from:  date | None = None,
    date_to:    date | None = None,
    search:     str | None  = None,
    sort_by:    str         = "period_end",
    sort_order: str         = "desc",
    page:       int         = 1,
    page_size:  int         = 20,
) -> SettlementListResponse:
    """
    Return a paginated list of settlements plus aggregate summary.

    Single-query strategy
    ----------------------
    * Main query: settlements LEFT JOIN payout_events (no N+1).
    * Reconciliation status: correlated scalar subquery (one lookup per row,
      executed server-side in one DB round-trip because it's embedded in SELECT).
    * Summary: separate COUNT/SUM query over identical filter conditions.
    """
    skip = (page - 1) * page_size

    # ── Correlated subquery: latest reconciliation status per settlement ──────
    recon_sq = (
        select(ReconciliationResult.status)
        .where(ReconciliationResult.settlement_id == Settlement.id)
        .order_by(ReconciliationResult.created_at.desc())
        .limit(1)
        .correlate(Settlement)
        .scalar_subquery()
    )

    # ── Build base conditions ─────────────────────────────────────────────────
    conditions = [Settlement.company_id == company_id]

    if platform:
        conditions.append(Settlement.platform == platform.lower())
    if status:
        db_status = _STATUS_FILTER_MAP.get(status.lower(), status)
        conditions.append(Settlement.status == db_status)
    if date_from:
        conditions.append(Settlement.period_start >= datetime(date_from.year, date_from.month, date_from.day))
    if date_to:
        conditions.append(Settlement.period_end <= datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59))
    if search:
        conditions.append(Settlement.external_id.ilike(f"%{search}%"))

    # ── Count total matching rows ─────────────────────────────────────────────
    count_q = select(func.count(Settlement.id)).where(*conditions)
    total = (await db.execute(count_q)).scalar_one() or 0

    # ── Summary aggregates (same filter, separate query) ──────────────────────
    summary_row = (await db.execute(
        select(
            func.coalesce(func.sum(Settlement.total_amount), 0).label("total_gross"),
            func.coalesce(func.sum(Settlement.fees_total), 0).label("total_fees"),
            func.coalesce(func.sum(
                case((Settlement.status == "closed", Settlement.fund_transfer_amount), else_=0)
            ), 0).label("total_net"),
            func.coalesce(func.sum(
                case((Settlement.status != "closed", Settlement.fund_transfer_amount), else_=0)
            ), 0).label("pending_amount"),
            func.coalesce(func.sum(Settlement.transactions_count), 0).label("total_transactions"),
            func.count(case((Settlement.status == "closed", 1))).label("closed_count"),
            func.count(case((Settlement.status == "open", 1))).label("open_count"),
            func.count(case((Settlement.status == "processing", 1))).label("processing_count"),
        )
        .where(*conditions)
    )).one()

    summary = SettlementSummaryOut(
        total_settlements=total,
        closed_count=summary_row.closed_count or 0,
        open_count=summary_row.open_count or 0,
        processing_count=summary_row.processing_count or 0,
        total_gross=_f(summary_row.total_gross),
        total_fees=_f(summary_row.total_fees),
        total_net=_f(summary_row.total_net),
        pending_amount=_f(summary_row.pending_amount),
        total_transactions=int(summary_row.total_transactions or 0),
    )

    # ── Sort ──────────────────────────────────────────────────────────────────
    sort_col = _SORT_COLUMNS.get(sort_by, Settlement.period_end)
    order_expr = (
        sort_col.desc().nullsfirst()
        if sort_order.lower() == "desc"
        else sort_col.asc().nullslast()
    )

    # ── Main query: settlements + payout LEFT JOIN ────────────────────────────
    rows = (await db.execute(
        select(
            Settlement,
            PayoutEvent.status.label("payout_status"),
            recon_sq.label("recon_status"),
        )
        .outerjoin(PayoutEvent, PayoutEvent.settlement_id == Settlement.id)
        .where(*conditions)
        .order_by(order_expr)
        .offset(skip)
        .limit(page_size)
    )).all()

    items = [
        _settlement_to_list_item(row.Settlement, row.payout_status, row.recon_status)
        for row in rows
    ]

    return SettlementListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
        summary=summary,
    )


# ── Settlement detail ─────────────────────────────────────────────────────────

async def _load_settlement(
    db: AsyncSession,
    *,
    settlement_id: UUID | None = None,
    external_id:   str | None  = None,
    company_id:    UUID,
) -> Settlement | None:
    """Load a settlement + its payout event in a single query."""
    conditions = [Settlement.company_id == company_id]
    if settlement_id:
        conditions.append(Settlement.id == settlement_id)
    elif external_id:
        conditions.append(Settlement.external_id == external_id)
    else:
        return None

    row = (await db.execute(
        select(Settlement, PayoutEvent, ReconciliationResult.status.label("recon_status"))
        .outerjoin(PayoutEvent, PayoutEvent.settlement_id == Settlement.id)
        .outerjoin(
            ReconciliationResult,
            (ReconciliationResult.settlement_id == Settlement.id)
            & (ReconciliationResult.created_at == (
                select(func.max(ReconciliationResult.created_at))
                .where(ReconciliationResult.settlement_id == Settlement.id)
                .correlate(ReconciliationResult)
                .scalar_subquery()
            )),
        )
        .where(*conditions)
        .limit(1)
    )).first()

    return row


async def get_settlement_by_id(
    db: AsyncSession, settlement_id: UUID, company_id: UUID
) -> SettlementDetailOut | None:
    return await _build_detail(db, settlement_id=settlement_id, company_id=company_id)


async def get_settlement_by_external_id(
    db: AsyncSession, external_id: str, company_id: UUID
) -> SettlementDetailOut | None:
    return await _build_detail(db, external_id=external_id, company_id=company_id)


async def _build_detail(
    db: AsyncSession,
    *,
    settlement_id: UUID | None = None,
    external_id:   str | None  = None,
    company_id:    UUID,
) -> SettlementDetailOut | None:
    row = await _load_settlement(
        db,
        settlement_id=settlement_id,
        external_id=external_id,
        company_id=company_id,
    )
    if row is None:
        return None

    s: Settlement = row.Settlement
    payout: PayoutEvent | None = row.PayoutEvent
    recon_status: str | None = row.recon_status

    breakdown = await get_fee_breakdown(db, s.id, s.total_amount, s.fund_transfer_amount)

    payout_out: PayoutOut | None = None
    if payout:
        payout_out = PayoutOut(
            id=payout.id,
            status=payout.status,
            amount=_f(payout.amount),
            transfer_date=payout.transfer_date,
            account_tail=payout.account_tail,
            external_id=payout.external_id,
        )

    return SettlementDetailOut(
        id=s.id,
        external_id=s.external_id,
        platform=s.platform,
        platform_label=_platform_label(s.platform),
        status=s.status,
        status_label=_status_label(s.status),
        period_start=s.period_start,
        period_end=s.period_end,
        period_label=_period_label(s.period_start, s.period_end),
        currency=s.currency,
        total_amount=_f(s.total_amount),
        fees_total=_f(s.fees_total),
        fund_transfer_amount=_f(s.fund_transfer_amount) if s.fund_transfer_amount else None,
        beginning_balance=_f(s.beginning_balance) if s.beginning_balance else None,
        transactions_count=s.transactions_count or 0,
        fund_transfer_date=s.fund_transfer_date,
        account_tail=s.account_tail,
        created_at=s.created_at,
        updated_at=s.updated_at,
        payout=payout_out,
        fee_breakdown=breakdown,
        reconciliation_status=recon_status,
    )


# ── Fee breakdown ─────────────────────────────────────────────────────────────

async def get_fee_breakdown(
    db: AsyncSession,
    settlement_id: UUID,
    total_amount,
    fund_transfer_amount,
) -> FeeBreakdownOut:
    """
    Aggregate fees by type + refund + service-fee transactions in two queries.

    Query 1: GROUP BY fee_type on the fees table.
    Query 2: SUM by transaction_type on settlement_transactions.
    """
    # Q1: Fee aggregation
    fee_rows = (await db.execute(
        select(
            Fee.fee_type,
            func.sum(Fee.amount).label("total"),
            func.count(Fee.id).label("count"),
        )
        .where(Fee.settlement_id == settlement_id)
        .group_by(Fee.fee_type)
        .order_by(func.abs(func.sum(Fee.amount)).desc())
    )).all()

    # Q2: Transaction-level aggregation (refunds, service fees)
    txn_rows = (await db.execute(
        select(
            SettlementTransaction.transaction_type,
            func.coalesce(func.sum(SettlementTransaction.total_amount), 0).label("total"),
        )
        .where(
            SettlementTransaction.settlement_id == settlement_id,
            SettlementTransaction.transaction_type.in_(["refund", "service_fee"]),
        )
        .group_by(SettlementTransaction.transaction_type)
    )).all()

    txn_by_type = {r.transaction_type: _f(r.total) for r in txn_rows}
    refund_total   = txn_by_type.get("refund", 0.0)
    service_fees   = txn_by_type.get("service_fee", 0.0)

    # Categorise fee line items
    referral_fees = fba_fees = closing_fees = shipping_fees = 0.0
    tcs_taxes = other_fees = 0.0
    fee_items: list[FeeLineItemOut] = []

    for row in fee_rows:
        amount = _f(row.total)
        ft = row.fee_type

        # Human-readable label
        label = (
            ft.replace("FBAPerUnit", "FBA/Unit ")
              .replace("FBAWeight", "FBA Weight ")
              .replace("VariableClosing", "Variable Closing ")
              .replace("MarketplaceFacilitatorTax-", "MKT Tax – ")
              .replace("PerItem", "Per Item ")
        )
        fee_items.append(FeeLineItemOut(fee_type=ft, label=label, total_amount=amount, count=row.count))

        if ft in _REFERRAL_TYPES:
            referral_fees += amount
        elif ft in _FBA_TYPES:
            fba_fees += amount
        elif ft in _CLOSING_TYPES:
            closing_fees += amount
        elif ft in _SHIPPING_TYPES:
            shipping_fees += amount
        elif "MarketplaceFacilitator" in ft or "Tax" in ft:
            tcs_taxes += amount
        else:
            other_fees += amount

    # Gross = sum of shipment principal amounts (approximated by settlement total_amount)
    # For precise gross, one would SUM principal_amount from shipment transactions.
    # We use fund_transfer_amount (actual payout) as net_payout here.
    gross   = _f(total_amount)
    net_pay = _f(fund_transfer_amount) if fund_transfer_amount else (
        gross + referral_fees + fba_fees + closing_fees
        + shipping_fees + tcs_taxes + service_fees + other_fees + refund_total
    )

    return FeeBreakdownOut(
        gross_amount=gross,
        referral_fees=referral_fees,
        fba_fees=fba_fees,
        closing_fees=closing_fees,
        shipping_fees=shipping_fees,
        tcs_taxes=tcs_taxes,
        service_fees=service_fees,
        other_fees=other_fees,
        refund_total=refund_total,
        net_payout=net_pay,
        fee_items=fee_items,
    )


# ── Transactions ──────────────────────────────────────────────────────────────

async def list_transactions(
    db: AsyncSession,
    settlement_id: UUID,
    *,
    txn_type:   str | None = None,
    order_id:   str | None = None,
    sku:        str | None = None,
    sort_by:    str        = "posted_date",
    sort_order: str        = "desc",
    page:       int        = 1,
    page_size:  int        = 50,
) -> TransactionListResponse:
    """
    Paginated transaction list + per-type summary for a settlement.

    Two queries:
      1. Paginated rows (filtered + sorted).
      2. GROUP BY transaction_type for the summary panel.
    """
    skip = (page - 1) * page_size

    conditions = [SettlementTransaction.settlement_id == settlement_id]
    if txn_type:
        conditions.append(SettlementTransaction.transaction_type == txn_type)
    if order_id:
        conditions.append(SettlementTransaction.order_id == order_id)
    if sku:
        conditions.append(SettlementTransaction.sku.ilike(f"%{sku}%"))

    # Count
    total = (await db.execute(
        select(func.count(SettlementTransaction.id)).where(*conditions)
    )).scalar_one() or 0

    # Sort
    _txn_sort = {
        "posted_date":   SettlementTransaction.posted_date,
        "total_amount":  SettlementTransaction.total_amount,
        "net_amount":    SettlementTransaction.net_amount,
        "fees_total":    SettlementTransaction.fees_total,
        "created_at":    SettlementTransaction.created_at,
    }
    sort_col = _txn_sort.get(sort_by, SettlementTransaction.posted_date)
    order_expr = (
        sort_col.desc().nullsfirst()
        if sort_order.lower() == "desc"
        else sort_col.asc().nullslast()
    )

    # Rows
    rows = (await db.execute(
        select(SettlementTransaction)
        .where(*conditions)
        .order_by(order_expr)
        .offset(skip)
        .limit(page_size)
    )).scalars().all()

    # Type summary (always over all transactions, not just current page)
    type_rows = (await db.execute(
        select(
            SettlementTransaction.transaction_type,
            func.count(SettlementTransaction.id).label("cnt"),
            func.coalesce(func.sum(SettlementTransaction.total_amount), 0).label("total"),
            func.coalesce(func.sum(SettlementTransaction.fees_total), 0).label("fees"),
            func.coalesce(func.sum(SettlementTransaction.net_amount), 0).label("net"),
        )
        .where(SettlementTransaction.settlement_id == settlement_id)
        .group_by(SettlementTransaction.transaction_type)
        .order_by(func.count(SettlementTransaction.id).desc())
    )).all()

    by_type = [
        TransactionTypeSummaryOut(
            transaction_type=r.transaction_type,
            count=r.cnt,
            total_amount=_f(r.total),
            fees_total=_f(r.fees),
            net_amount=_f(r.net),
        )
        for r in type_rows
    ]

    items = [
        TransactionItemOut(
            id=t.id,
            transaction_type=t.transaction_type,
            order_id=t.order_id,
            order_item_id=t.order_item_id,
            sku=t.sku,
            marketplace=t.marketplace,
            posted_date=t.posted_date,
            quantity=t.quantity or 1,
            currency=t.currency,
            principal_amount=_f(t.principal_amount),
            shipping_amount=_f(t.shipping_amount),
            total_amount=_f(t.total_amount),
            fees_total=_f(t.fees_total),
            net_amount=_f(t.net_amount),
            created_at=t.created_at,
        )
        for t in rows
    ]

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
        by_type=by_type,
    )


# ── Payouts ───────────────────────────────────────────────────────────────────

async def list_payouts(
    db: AsyncSession,
    *,
    company_id:  UUID,
    platform:    str | None  = None,
    payout_status: str | None = None,
    date_from:   date | None = None,
    date_to:     date | None = None,
    page:        int         = 1,
    page_size:   int         = 20,
) -> PayoutListResponse:
    """
    List payout events joined with their settlement (for external_id display).
    Returns aggregate totals by status.
    """
    skip = (page - 1) * page_size

    conditions = [PayoutEvent.company_id == company_id]
    if platform:
        conditions.append(PayoutEvent.platform == platform.lower())
    if payout_status:
        conditions.append(PayoutEvent.status == payout_status)
    if date_from:
        conditions.append(PayoutEvent.transfer_date >= datetime(date_from.year, date_from.month, date_from.day))
    if date_to:
        conditions.append(PayoutEvent.transfer_date <= datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59))

    total = (await db.execute(
        select(func.count(PayoutEvent.id)).where(*conditions)
    )).scalar_one() or 0

    # Aggregate totals (unfiltered by page)
    agg_row = (await db.execute(
        select(
            func.coalesce(func.sum(
                case((PayoutEvent.status == "transferred", PayoutEvent.amount), else_=0)
            ), 0).label("transferred"),
            func.coalesce(func.sum(
                case((PayoutEvent.status == "pending", PayoutEvent.amount), else_=0)
            ), 0).label("pending"),
            func.coalesce(func.sum(
                case((PayoutEvent.status == "failed", PayoutEvent.amount), else_=0)
            ), 0).label("failed"),
        )
        .where(*conditions)
    )).one()

    rows = (await db.execute(
        select(PayoutEvent, Settlement.external_id.label("settlement_external_id"))
        .join(Settlement, Settlement.id == PayoutEvent.settlement_id)
        .where(*conditions)
        .order_by(PayoutEvent.transfer_date.desc().nullsfirst())
        .offset(skip)
        .limit(page_size)
    )).all()

    items = [
        PayoutItemOut(
            id=row.PayoutEvent.id,
            settlement_id=row.PayoutEvent.settlement_id,
            settlement_external_id=row.settlement_external_id,
            platform=row.PayoutEvent.platform,
            platform_label=_platform_label(row.PayoutEvent.platform),
            status=row.PayoutEvent.status,
            amount=_f(row.PayoutEvent.amount),
            transfer_date=row.PayoutEvent.transfer_date,
            account_tail=row.PayoutEvent.account_tail,
        )
        for row in rows
    ]

    return PayoutListResponse(
        items=items,
        total=total,
        total_transferred=_f(agg_row.transferred),
        total_pending=_f(agg_row.pending),
        total_failed=_f(agg_row.failed),
    )


# ── Settlement access guard ───────────────────────────────────────────────────

async def verify_settlement_company(
    db: AsyncSession,
    settlement_id: UUID,
    company_id: UUID,
) -> bool:
    """Return True if the settlement belongs to the given company."""
    row = (await db.execute(
        select(Settlement.id)
        .where(
            Settlement.id == settlement_id,
            Settlement.company_id == company_id,
        )
        .limit(1)
    )).scalar_one_or_none()
    return row is not None
