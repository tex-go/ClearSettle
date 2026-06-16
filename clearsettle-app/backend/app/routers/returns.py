"""Returns — settlement_transactions where type=refund.

Phase 1: added POST /returns/dispute-item so return deductions can be
escalated into the Recovery Center workflow (source=leakage_audit).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.flipkart_db import fk_session
from app.db.models.discrepancy_event import (
    DiscrepancyEvent,
    SOURCE_LEAKAGE_AUDIT,
    STATE_DETECTED,
)
from app.db.models.settlement_transaction import SettlementTransaction
from app.services import flipkart_queries

router = APIRouter()

_PLATFORM_ICON = {
    "amazon": "🛒", "flipkart": "🛍️", "meesho": "👗",
    "myntra": "👠", "nykaa": "💄", "ajio": "👔",
    "snapdeal": "🏷️", "jiomart": "🛒",
}


def _cid(user) -> Optional[UUID]:
    if not user.companies:
        return None
    return user.companies[0].id


def _tx_to_return(tx: SettlementTransaction, idx: int) -> dict:
    base = float(abs(tx.principal_amount or 0))
    ship = float(abs(tx.shipping_amount or 0))
    total = float(abs(tx.total_amount or 0))
    plat = (tx.platform or "unknown").lower()
    date_str = tx.posted_date.date().isoformat() if tx.posted_date else ""
    return {
        "id":          f"RET-{idx:03d}",
        "tx_id":       str(tx.id),
        "plat":        plat.title(),
        "icon":        _PLATFORM_ICON.get(plat, "🏪"),
        "oid":         tx.order_id or "",
        "sku":         tx.sku or "",
        "prod":        tx.order_item_id or tx.sku or "Product",
        "reason":      "Return",
        "qty":         int(tx.quantity or 1),
        "base":        base,
        "ship":        ship,
        "total":       total,
        "date":        date_str,
        "status":      "processed",
        "platform_raw": plat,
    }


@router.get("/")
async def get_returns(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _empty_summary = {"total_count": 0, "total_deducted": 0.0, "disputed_count": 0, "by_reason": {}}
    cid = _cid(user)
    if cid is None:
        return {"items": [], "summary": _empty_summary}

    rows = (await db.execute(
        select(SettlementTransaction)
        .where(
            SettlementTransaction.company_id == cid,
            SettlementTransaction.transaction_type == "refund",
        )
        .order_by(SettlementTransaction.posted_date.desc())
        .limit(200)
    )).scalars().all()

    if not rows:
        from app.services.analytics.queries import get_flipkart_returns
        fk_result = await get_flipkart_returns(db, cid)
        if fk_result:
            return fk_result
        async with fk_session() as fk_db:
            return await flipkart_queries.get_returns_data(fk_db)

    items = [_tx_to_return(tx, i + 1) for i, tx in enumerate(rows)]
    total_deducted = sum(r["total"] for r in items)
    return {
        "items": items,
        "summary": {
            "total_count":    len(items),
            "total_deducted": total_deducted,
            "disputed_count": 0,
            "by_reason":      {"Return": len(items)},
        },
    }


class DisputeReturnRequest(BaseModel):
    tx_id: str
    platform: str
    sku: str
    order_id: str
    amount: float
    reason: str = "Return deduction overcharge"


@router.post("/dispute-item")
async def dispute_return_item(
    body: DisputeReturnRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 1: File a DiscrepancyEvent (source=leakage_audit, type=RETURN_OVERCHARGE)
    for a single return deduction — appears immediately in Recovery Center.
    """
    cid = _cid(user)
    if cid is None:
        return {"message": "No company found"}

    event = DiscrepancyEvent(
        company_id=cid,
        platform=body.platform.lower(),
        discrepancy_type="RETURN_OVERCHARGE",
        severity="warning",
        source=SOURCE_LEAKAGE_AUDIT,
        workflow_state=STATE_DETECTED,
        description=(
            f"Return deduction disputed for Order {body.order_id}, SKU {body.sku}. "
            f"Deducted: ₹{body.amount:.2f}. Reason: {body.reason}."
        ),
        variance_amount=Decimal(str(body.amount)),
        order_id=body.order_id,
        sku=body.sku,
        is_resolved=False,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"message": "Dispute filed", "id": str(event.id)}
