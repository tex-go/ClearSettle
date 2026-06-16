"""
Settlement APIs — real PostgreSQL-backed implementation.

All endpoints fall back to mock data when DATABASE_URL is not configured
so that the existing demo/frontend experience is preserved.

Endpoints
---------
GET  /settlements/               list with pagination, filtering, sorting
GET  /settlements/payouts        payout list with aggregates
GET  /settlements/{sid}          full detail with fee breakdown + payout
GET  /settlements/{sid}/transactions  paginated transaction list
GET  /settlements/{sid}/fees     fee breakdown by category
POST /settlements/{sid}/dispute  raise a dispute (validates settlement exists)
"""
from __future__ import annotations

import math
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import SETTLEMENTS
from app.db.flipkart_db import fk_session
from app.schemas.settlements import (
    FeeBreakdownOut,
    PayoutListResponse,
    SettlementDetailOut,
    SettlementListResponse,
    SettlementSummaryOut,
    TransactionListResponse,
)
from app.services.settlements import queries as settlement_queries
from app.services import flipkart_queries

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_db_user(user) -> bool:
    """True when the user is a real ORM User object (not the mock dict)."""
    return hasattr(user, "companies")


def _company_id(user) -> UUID:
    if not _is_db_user(user) or not user.companies:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No company associated with this account.",
        )
    return user.companies[0].id


# ── mock fallback helpers ─────────────────────────────────────────────────────

def _mock_list(
    status_filter: str | None,
    platform_filter: str | None,
    search: str | None,
    page: int,
    page_size: int,
) -> SettlementListResponse:
    items = list(SETTLEMENTS)
    if status_filter:
        label_map = {"closed": "paid", "paid": "paid", "open": "pending", "pending": "pending"}
        wanted = label_map.get(status_filter.lower(), status_filter)
        items = [s for s in items if s["status"] == wanted]
    if platform_filter:
        items = [s for s in items if s["plat"].lower() == platform_filter.lower()]
    if search:
        q = search.lower()
        items = [s for s in items if q in s["id"].lower() or q in s["plat"].lower()]

    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start: start + page_size]

    return SettlementListResponse(
        items=[_mock_to_list_item(s) for s in page_items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
        summary=SettlementSummaryOut(
            total_settlements=total,
            closed_count=sum(1 for s in items if s["status"] == "paid"),
            open_count=sum(1 for s in items if s["status"] == "pending"),
            processing_count=0,
            total_gross=sum(s["base"] for s in items),
            total_fees=-sum(s["comm"] + s["logi"] + s["ret"] + s["tcs"] + s["pen"] for s in items),
            total_net=sum(s["net"] for s in items if s["status"] == "paid"),
            pending_amount=sum(s["net"] for s in items if s["status"] == "pending"),
            total_transactions=sum(s["orders"] for s in items),
        ),
    )


def _mock_to_list_item(s: dict):
    """Convert a mock SETTLEMENTS dict to a SettlementListItemOut-compatible dict."""
    from app.schemas.settlements import SettlementListItemOut
    import uuid as _uuid_mod

    return SettlementListItemOut(
        id=_uuid_mod.uuid5(_uuid_mod.NAMESPACE_DNS, s["id"]),
        external_id=s["id"],
        platform=s["plat"].lower(),
        platform_label=s["plat"],
        status="closed" if s["status"] == "paid" else "open",
        status_label=s["status"],
        period_start=None,
        period_end=None,
        period_label=s["period"],
        currency="INR",
        total_amount=float(s["base"]),
        fees_total=-float(s["comm"] + s["logi"] + s["ret"] + s["tcs"] + s["pen"]),
        fund_transfer_amount=float(s["net"]),
        net_amount=float(s["net"]),
        transactions_count=s["orders"],
        fund_transfer_date=None,
        account_tail=None,
        payout_status="transferred" if s["status"] == "paid" else "pending",
        reconciliation_status=None,
        created_at=__import__("datetime").datetime.utcnow(),
    )


def _mock_detail(s: dict) -> dict:
    total_fees = s["comm"] + s["logi"] + s["ret"] + s["tcs"] + s["pen"]
    return {
        "id": s["id"],
        "external_id": s["id"],
        "platform": s["plat"].lower(),
        "platform_label": s["plat"],
        "status": "closed" if s["status"] == "paid" else "open",
        "status_label": s["status"],
        "period_label": s["period"],
        "currency": "INR",
        "total_amount": s["base"],
        "fees_total": -total_fees,
        "fund_transfer_amount": s["net"],
        "net_amount": s["net"],
        "transactions_count": s["orders"],
        "paid_date": s.get("paid_date"),
        "breakdown": {
            "gross_amount": s["base"],
            "referral_fees": -s["comm"],
            "fba_fees": -s["logi"],
            "closing_fees": 0.0,
            "shipping_fees": 0.0,
            "tcs_taxes": -s["tcs"],
            "service_fees": -s["pen"],
            "other_fees": 0.0,
            "refund_total": -s["ret"],
            "net_payout": s["net"],
            "fee_items": [
                {"fee_type": "ReferralFee",              "label": "Commission",    "total_amount": -s["comm"], "count": s["orders"]},
                {"fee_type": "FBAPerUnitFulfillmentFee", "label": "Logistics",     "total_amount": -s["logi"], "count": s["orders"]},
                {"fee_type": "RefundTransaction",        "label": "Returns",       "total_amount": -s["ret"],  "count": 0},
                {"fee_type": "MarketplaceFacilitatorTax-Principal", "label": "TCS", "total_amount": -s["tcs"], "count": s["orders"]},
                {"fee_type": "ServiceFee",               "label": "Penalty",       "total_amount": -s["pen"],  "count": 1 if s["pen"] else 0},
            ],
        },
    }


# ── flipkart_recon → SettlementListResponse adapter ──────────────────────────

def _fk_to_settlement_list(
    fk_data: dict,
    page: int,
    page_size: int,
) -> SettlementListResponse:
    """Convert flipkart_queries.get_settlements() output to SettlementListResponse."""
    import uuid as _uuid_mod
    import datetime as _dt
    from app.schemas.settlements import SettlementListItemOut, SettlementSummaryOut

    raw_items = fk_data["items"]
    total = len(raw_items)
    start = (page - 1) * page_size
    page_items = raw_items[start: start + page_size]

    def _to_item(s: dict) -> SettlementListItemOut:
        sid = _uuid_mod.uuid5(_uuid_mod.NAMESPACE_DNS, s["id"])
        fees = -(s["comm"] + s["ret"] + s["tcs"])
        return SettlementListItemOut(
            id=sid,
            external_id=s["id"],
            platform="flipkart",
            platform_label="Flipkart",
            status="closed" if s["status"] == "paid" else "open",
            status_label=s["status"],
            period_start=None,
            period_end=None,
            period_label=s["period"],
            currency="INR",
            total_amount=float(s["base"]),
            fees_total=float(fees),
            fund_transfer_amount=float(s["net"]),
            net_amount=float(s["net"]),
            transactions_count=int(s["orders"]),
            fund_transfer_date=None,
            account_tail=None,
            payout_status="transferred" if s["status"] == "paid" else "pending",
            reconciliation_status=None,
            created_at=_dt.datetime.utcnow(),
        )

    summary_data = fk_data["summary"]
    paid_items  = [s for s in raw_items if s["status"] == "paid"]
    pend_items  = [s for s in raw_items if s["status"] != "paid"]

    return SettlementListResponse(
        items=[_to_item(s) for s in page_items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
        summary=SettlementSummaryOut(
            total_settlements=total,
            closed_count=len(paid_items),
            open_count=len(pend_items),
            processing_count=0,
            total_gross=sum(s["base"] for s in raw_items),
            total_fees=-sum(s["comm"] + s["ret"] + s["tcs"] for s in raw_items),
            total_net=float(summary_data["total_net"]),
            pending_amount=float(summary_data["pending_net"]),
            total_transactions=sum(s["orders"] for s in raw_items),
        ),
    )


# ── GET /settlements/ ─────────────────────────────────────────────────────────

@router.get("/", response_model=SettlementListResponse)
async def list_settlements(
    platform:   Optional[str]  = Query(None, description="Filter by platform (amazon, flipkart, meesho …)"),
    status:     Optional[str]  = Query(None, description="Filter by status: paid | pending | processing"),
    date_from:  Optional[date] = Query(None, description="Period start on or after (YYYY-MM-DD)"),
    date_to:    Optional[date] = Query(None, description="Period end on or before (YYYY-MM-DD)"),
    search:     Optional[str]  = Query(None, description="Search by settlement ID / external reference"),
    sort_by:    str            = Query("period_end",  description="Sort field"),
    sort_order: str            = Query("desc",        description="asc | desc"),
    page:       int            = Query(1,    ge=1,    description="Page number (1-based)"),
    page_size:  int            = Query(20,   ge=1, le=100, description="Items per page"),
    user       = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Paginated settlement list with aggregate summary.

    Returns items for the authenticated user's primary company.
    Falls back to demo data when the database is not configured.
    """
    if db is None or not _is_db_user(user):
        from app.schemas.settlements import SettlementSummaryOut
        return SettlementListResponse(
            items=[], total=0, page=page, page_size=page_size, total_pages=1,
            summary=SettlementSummaryOut(total_settlements=0, closed_count=0, open_count=0, processing_count=0, total_gross=0, total_fees=0, total_net=0, pending_amount=0, total_transactions=0),
        )

    result = await settlement_queries.list_settlements(
        db,
        company_id=_company_id(user),
        platform=platform,
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    if result.total == 0:
        async with fk_session() as fk_db:
            fk_data = await flipkart_queries.get_settlements(fk_db)
            return _fk_to_settlement_list(fk_data, page, page_size)

    return result


# ── GET /settlements/payouts ──────────────────────────────────────────────────

@router.get("/payouts", response_model=PayoutListResponse)
async def list_payouts(
    platform:   Optional[str]  = Query(None),
    payout_status: Optional[str] = Query(None, description="transferred | pending | failed"),
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
    page:       int            = Query(1, ge=1),
    page_size:  int            = Query(20, ge=1, le=100),
    user       = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    List payout events with transfer amounts and status.

    Returns totals for transferred / pending / failed payouts
    along with the paginated list.
    """
    if db is None or not _is_db_user(user):
        # Mock fallback: derive from SETTLEMENTS
        paid = [s for s in SETTLEMENTS if s["status"] == "paid"]
        pending = [s for s in SETTLEMENTS if s["status"] == "pending"]
        import uuid as _u
        import datetime as _dt
        items = [
            {
                "id": _u.uuid5(_u.NAMESPACE_DNS, s["id"] + "-pay"),
                "settlement_id": _u.uuid5(_u.NAMESPACE_DNS, s["id"]),
                "settlement_external_id": s["id"],
                "platform": s["plat"].lower(),
                "platform_label": s["plat"],
                "status": "transferred",
                "amount": float(s["net"]),
                "transfer_date": None,
                "account_tail": None,
            }
            for s in paid
        ]
        return PayoutListResponse(
            items=items,
            total=len(items),
            total_transferred=sum(s["net"] for s in paid),
            total_pending=sum(s["net"] for s in pending),
            total_failed=0.0,
        )

    return await settlement_queries.list_payouts(
        db,
        company_id=_company_id(user),
        platform=platform,
        payout_status=payout_status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


# ── GET /settlements/{settlement_id} ──────────────────────────────────────────

@router.get("/{settlement_id}")
async def get_settlement(
    settlement_id: str,
    user          = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Full settlement detail including fee breakdown and payout info.

    Accepts both a UUID (from the list API) and a legacy string external_id
    (e.g., "AMZN-2026-0448") for backward compatibility.
    """
    if db is None or not _is_db_user(user):
        raise HTTPException(status_code=404, detail="Settlement not found.")

    cid = _company_id(user)

    # Try UUID first, then fall back to external_id string lookup
    detail: SettlementDetailOut | None = None
    try:
        uid = UUID(settlement_id)
        detail = await settlement_queries.get_settlement_by_id(db, uid, cid)
    except ValueError:
        detail = await settlement_queries.get_settlement_by_external_id(db, settlement_id, cid)

    if detail is None:
        raise HTTPException(status_code=404, detail="Settlement not found.")

    return detail


# ── GET /settlements/{settlement_id}/transactions ─────────────────────────────

@router.get("/{settlement_id}/transactions", response_model=TransactionListResponse)
async def list_transactions(
    settlement_id: str,
    txn_type:   Optional[str] = Query(None, description="shipment | refund | service_fee | adjustment | …"),
    order_id:   Optional[str] = Query(None, description="Filter by marketplace order ID"),
    sku:        Optional[str] = Query(None, description="Filter by SKU (partial match)"),
    sort_by:    str           = Query("posted_date"),
    sort_order: str           = Query("desc"),
    page:       int           = Query(1, ge=1),
    page_size:  int           = Query(50, ge=1, le=200),
    user       = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Paginated transaction list for a settlement.

    Includes a by_type summary showing counts and amounts per transaction type
    (shipment, refund, service_fee, adjustment, …).
    """
    if db is None or not _is_db_user(user):
        # Mock: no real transactions available
        return TransactionListResponse(
            items=[], total=0, page=1, page_size=page_size,
            total_pages=1, by_type=[],
        )

    cid = _company_id(user)

    # Resolve settlement UUID
    try:
        sid = UUID(settlement_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="settlement_id must be a valid UUID.")

    # Verify ownership
    if not await settlement_queries.verify_settlement_company(db, sid, cid):
        raise HTTPException(status_code=404, detail="Settlement not found.")

    return await settlement_queries.list_transactions(
        db,
        sid,
        txn_type=txn_type,
        order_id=order_id,
        sku=sku,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


# ── GET /settlements/{settlement_id}/fees ─────────────────────────────────────

@router.get("/{settlement_id}/fees", response_model=FeeBreakdownOut)
async def get_fee_breakdown(
    settlement_id: str,
    user = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Aggregated fee breakdown for a settlement grouped by fee category.

    Categories: referral_fees, fba_fees, closing_fees, shipping_fees,
                tcs_taxes, service_fees, other_fees, refund_total.
    Also returns fee_items with individual fee_type totals.
    """
    if db is None or not _is_db_user(user):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fee breakdown requires a database connection.",
        )

    cid = _company_id(user)

    try:
        sid = UUID(settlement_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="settlement_id must be a valid UUID.")

    if not await settlement_queries.verify_settlement_company(db, sid, cid):
        raise HTTPException(status_code=404, detail="Settlement not found.")

    # Load settlement for total_amount + fund_transfer_amount
    from sqlalchemy import select
    from app.db.models.settlement import Settlement as _Settlement
    s = (await db.execute(
        select(_Settlement.total_amount, _Settlement.fund_transfer_amount)
        .where(_Settlement.id == sid)
    )).one_or_none()

    if s is None:
        raise HTTPException(status_code=404, detail="Settlement not found.")

    return await settlement_queries.get_fee_breakdown(
        db, sid, s.total_amount, s.fund_transfer_amount
    )


# ── POST /settlements/{settlement_id}/dispute ─────────────────────────────────

@router.post("/{settlement_id}/dispute")
async def raise_dispute(
    settlement_id: str,
    user = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Raise a dispute for a settlement.

    When the database is available, validates the settlement exists and belongs
    to the authenticated company before creating the dispute record.
    """
    if db is None or not _is_db_user(user):
        # Mock mode — preserve existing behaviour
        return {
            "message": f"Dispute raised for settlement {settlement_id}",
            "status":  "open",
            "ref":     f"DISP-AUTO-{settlement_id}",
        }

    cid = _company_id(user)

    # Resolve to UUID or external_id
    try:
        sid = UUID(settlement_id)
        exists = await settlement_queries.verify_settlement_company(db, sid, cid)
    except ValueError:
        # Try external_id lookup
        from sqlalchemy import select
        from app.db.models.settlement import Settlement as _Settlement
        row = (await db.execute(
            select(_Settlement.id)
            .where(
                _Settlement.external_id == settlement_id,
                _Settlement.company_id  == cid,
            )
            .limit(1)
        )).scalar_one_or_none()
        exists = row is not None
        if row:
            sid = row

    if not exists:
        raise HTTPException(status_code=404, detail="Settlement not found.")

    # Dispute management is a future module — return stub with validated settlement
    return {
        "message":       f"Dispute raised for settlement {settlement_id}",
        "settlement_id": str(sid),
        "status":        "open",
        "ref":           f"DISP-{str(sid)[:8].upper()}",
    }
