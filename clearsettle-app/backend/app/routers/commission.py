"""Commission Audit — real DB (fees + settlement_transactions) with mock fallback."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import COMMISSIONS as _MOCK
from app.db.models.fee import Fee
from app.db.models.settlement_transaction import SettlementTransaction

router = APIRouter()

_REFERRAL_TYPES = frozenset({"ReferralFee", "Commission"})
_PLAT_ICON = {
    "amazon": "🛒", "flipkart": "🛍️", "meesho": "👗",
    "myntra": "👠", "nykaa": "💄", "ajio": "👔",
    "snapdeal": "🏷️", "jiomart": "🛒",
}
# Published rates per platform (approximate — used for overcharge detection)
_PUB_RATE = {
    "amazon": 13.0, "flipkart": 12.0, "meesho": 0.0,
    "myntra": 18.0, "nykaa": 15.0, "ajio": 20.0,
    "snapdeal": 10.0, "jiomart": 8.0,
}


def _is_db_user(user) -> bool:
    return hasattr(user, "companies")


def _cid(user) -> Optional[UUID]:
    if not _is_db_user(user) or not user.companies:
        return None
    return user.companies[0].id


def _mock_summary():
    flagged = [c for c in _MOCK if c["flag"]]
    return {
        "total_overcharge": sum(c["over"] for c in flagged),
        "flagged_count":    len(flagged),
        "affected_orders":  sum(c["orders"] for c in flagged),
    }


@router.get("/")
async def get_commissions(
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    cid = _cid(user)
    if db is None or cid is None:
        return {"items": _MOCK, "summary": _mock_summary()}

    # Total referral fees charged per platform + sku
    fee_q = (
        select(
            Fee.platform,
            SettlementTransaction.sku,
            func.coalesce(func.sum(func.abs(Fee.amount)), 0).label("chgFee"),
            func.count(Fee.id).label("fee_count"),
        )
        .join(SettlementTransaction, Fee.transaction_id == SettlementTransaction.id)
        .where(
            Fee.company_id == cid,
            Fee.fee_type.in_(list(_REFERRAL_TYPES)),
        )
        .group_by(Fee.platform, SettlementTransaction.sku)
        .order_by(func.sum(func.abs(Fee.amount)).desc())
        .limit(50)
    )
    fee_rows = (await db.execute(fee_q)).all()

    if not fee_rows:
        return {"items": _MOCK, "summary": _mock_summary()}

    # Gross revenue per platform + sku (shipments only)
    rev_q = (
        select(
            SettlementTransaction.platform,
            SettlementTransaction.sku,
            func.coalesce(func.sum(SettlementTransaction.principal_amount), 0).label("base"),
            func.count(SettlementTransaction.id).label("orders"),
        )
        .where(
            SettlementTransaction.company_id == cid,
            SettlementTransaction.transaction_type == "shipment",
        )
        .group_by(SettlementTransaction.platform, SettlementTransaction.sku)
    )
    rev_rows = {(r.platform, r.sku): r for r in (await db.execute(rev_q)).all()}

    items = []
    for row in fee_rows:
        plat = (row.platform or "unknown").lower()
        sku = row.sku or "Unknown SKU"
        chg_fee = float(row.chgFee or 0)
        rev_key = (row.platform, sku)
        rev = rev_rows.get(rev_key)
        base = float(rev.base or 0) if rev else 0.0
        orders = int(rev.orders or 0) if rev else 0
        pub_rate = _PUB_RATE.get(plat, 13.0)
        chg_rate = round(chg_fee / base * 100, 2) if base > 0 else 0.0
        exp_fee = round(base * pub_rate / 100, 2)
        over = max(0.0, round(chg_fee - exp_fee, 2))
        flag = chg_rate > pub_rate + 0.5 if pub_rate > 0 else False
        items.append({
            "plat":    plat.title(),
            "icon":    _PLAT_ICON.get(plat, "🏪"),
            "sku":     sku,
            "prod":    sku,
            "cat":     "Platform Fee",
            "pub":     pub_rate,
            "chg":     chg_rate,
            "orders":  orders,
            "base":    base,
            "expFee":  exp_fee,
            "chgFee":  chg_fee,
            "over":    over,
            "flag":    flag,
        })

    flagged = [i for i in items if i["flag"]]
    return {
        "items": items,
        "summary": {
            "total_overcharge": sum(i["over"] for i in flagged),
            "flagged_count":    len(flagged),
            "affected_orders":  sum(i["orders"] for i in flagged),
        },
    }


@router.post("/bulk-dispute")
async def bulk_dispute(user=Depends(get_current_user)):
    flagged = [c for c in _MOCK if c["flag"]]
    total = sum(c["over"] for c in flagged)
    return {"message": "Bulk dispute raised", "count": len(flagged), "total": total}
