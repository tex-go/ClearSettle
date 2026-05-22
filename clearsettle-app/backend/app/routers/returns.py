"""Returns — real DB (settlement_transactions where type=refund) with mock fallback."""
from __future__ import annotations

from collections import Counter
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import RETURNS as _MOCK
from app.db.models.settlement_transaction import SettlementTransaction

router = APIRouter()

_PLATFORM_ICON = {
    "amazon": "🛒", "flipkart": "🛍️", "meesho": "👗",
    "myntra": "👠", "nykaa": "💄", "ajio": "👔",
    "snapdeal": "🏷️", "jiomart": "🛒",
}


def _is_db_user(user) -> bool:
    return hasattr(user, "companies")


def _cid(user) -> Optional[UUID]:
    if not _is_db_user(user) or not user.companies:
        return None
    return user.companies[0].id


def _tx_to_return(tx: SettlementTransaction, idx: int) -> dict:
    base = float(abs(tx.principal_amount or 0))
    ship = float(abs(tx.shipping_amount or 0))
    total = float(abs(tx.total_amount or 0))
    plat = (tx.platform or "unknown").lower()
    date_str = tx.posted_date.date().isoformat() if tx.posted_date else ""
    return {
        "id":     f"RET-{idx:03d}",
        "plat":   plat.title(),
        "icon":   _PLATFORM_ICON.get(plat, "🏪"),
        "oid":    tx.order_id or "",
        "sku":    tx.sku or "",
        "prod":   tx.order_item_id or tx.sku or "Product",
        "reason": "Return",
        "qty":    int(tx.quantity or 1),
        "base":   base,
        "ship":   ship,
        "total":  total,
        "date":   date_str,
        "status": "processed",
    }


def _mock_summary():
    items = _MOCK
    return {
        "total_count":    len(items),
        "total_deducted": sum(r["total"] for r in items),
        "disputed_count": sum(1 for r in items if r["status"] == "disputed"),
        "by_reason":      dict(Counter(r["reason"] for r in items)),
    }


@router.get("/")
async def get_returns(
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    _empty_summary = {"total_count": 0, "total_deducted": 0.0, "disputed_count": 0, "by_reason": {}}
    cid = _cid(user)
    if db is None or cid is None:
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
        # Try Flipkart P&L data before returning empty
        from app.services.analytics.queries import get_flipkart_returns
        fk_result = await get_flipkart_returns(db, cid)
        if fk_result:
            return fk_result
        return {"items": [], "summary": _empty_summary}

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
