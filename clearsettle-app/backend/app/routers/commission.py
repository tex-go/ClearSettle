"""Commission Audit — real-DB referral-fee overcharge detection.

Phase 1: bulk-dispute now writes real DiscrepancyEvent rows (source=leakage_audit)
instead of using mock data, making commission overcharges visible in the
Recovery Center workflow.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.flipkart_db import fk_session
from app.db.models.discrepancy_event import (
    DiscrepancyEvent,
    SOURCE_LEAKAGE_AUDIT,
    STATE_DETECTED,
)
from app.db.models.fee import Fee
from app.db.models.settlement_transaction import SettlementTransaction
from app.services import flipkart_queries

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


def _cid(user) -> Optional[UUID]:
    if not user.companies:
        return None
    return user.companies[0].id


@router.get("/")
async def get_commissions(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _empty_summary = {"total_overcharge": 0.0, "flagged_count": 0, "affected_orders": 0}
    cid = _cid(user)
    if cid is None:
        return {"items": [], "summary": _empty_summary}

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
        async with fk_session() as fk_db:
            return await flipkart_queries.get_commission_data(fk_db)

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
        rev = rev_rows.get((row.platform, sku))
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
async def bulk_dispute(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 1: Create DiscrepancyEvent records (source=leakage_audit) for every
    flagged commission overcharge.  Events appear immediately in Recovery Center.
    Skips SKUs that already have an unresolved COMMISSION_OVERCHARGE event.
    """
    cid = _cid(user)
    if cid is None:
        return {"message": "No company found", "count": 0, "total": 0.0}

    fee_q = (
        select(
            Fee.platform,
            SettlementTransaction.sku,
            func.coalesce(func.sum(func.abs(Fee.amount)), 0).label("chgFee"),
        )
        .join(SettlementTransaction, Fee.transaction_id == SettlementTransaction.id)
        .where(Fee.company_id == cid, Fee.fee_type.in_(list(_REFERRAL_TYPES)))
        .group_by(Fee.platform, SettlementTransaction.sku)
    )
    fee_rows = (await db.execute(fee_q)).all()

    rev_q = (
        select(
            SettlementTransaction.platform,
            SettlementTransaction.sku,
            func.coalesce(func.sum(SettlementTransaction.principal_amount), 0).label("base"),
        )
        .where(SettlementTransaction.company_id == cid,
               SettlementTransaction.transaction_type == "shipment")
        .group_by(SettlementTransaction.platform, SettlementTransaction.sku)
    )
    rev_rows = {(r.platform, r.sku): r for r in (await db.execute(rev_q)).all()}

    created, total_overcharge = 0, 0.0
    for row in fee_rows:
        plat = (row.platform or "unknown").lower()
        sku = row.sku or "Unknown SKU"
        chg_fee = float(row.chgFee or 0)
        rev = rev_rows.get((row.platform, sku))
        base = float(rev.base or 0) if rev else 0.0
        pub_rate = _PUB_RATE.get(plat, 13.0)
        chg_rate = chg_fee / base * 100 if base > 0 else 0.0
        exp_fee = base * pub_rate / 100
        over = max(0.0, chg_fee - exp_fee)
        if not (chg_rate > pub_rate + 0.5 if pub_rate > 0 else False):
            continue

        existing = (await db.execute(
            select(DiscrepancyEvent).where(
                DiscrepancyEvent.company_id == cid,
                DiscrepancyEvent.discrepancy_type == "COMMISSION_OVERCHARGE",
                DiscrepancyEvent.platform == plat,
                DiscrepancyEvent.sku == sku,
                DiscrepancyEvent.is_resolved.is_(False),
            )
        )).scalar_one_or_none()
        if existing:
            continue

        db.add(DiscrepancyEvent(
            company_id=cid,
            platform=plat,
            discrepancy_type="COMMISSION_OVERCHARGE",
            severity="warning",
            source=SOURCE_LEAKAGE_AUDIT,
            workflow_state=STATE_DETECTED,
            description=(
                f"{plat.title()} charged {chg_rate:.1f}% commission on SKU {sku} "
                f"vs published rate of {pub_rate:.1f}%. Overcharge: ₹{over:.2f}."
            ),
            expected_amount=exp_fee,
            actual_amount=chg_fee,
            variance_amount=over,
            sku=sku,
            is_resolved=False,
        ))
        created += 1
        total_overcharge += over

    await db.commit()
    return {
        "message": f"Filed {created} commission overcharge dispute(s)",
        "count": created,
        "total": round(total_overcharge, 2),
    }


@router.post("/dispute-sku")
async def dispute_single_sku(
    platform: str,
    sku: str,
    overcharge: float,
    description: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """File a DiscrepancyEvent for a single flagged SKU from the Commission table."""
    cid = _cid(user)
    if cid is None:
        return {"message": "No company found"}

    event = DiscrepancyEvent(
        company_id=cid,
        platform=platform.lower(),
        discrepancy_type="COMMISSION_OVERCHARGE",
        severity="warning",
        source=SOURCE_LEAKAGE_AUDIT,
        workflow_state=STATE_DETECTED,
        description=description,
        variance_amount=overcharge,
        sku=sku,
        is_resolved=False,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"message": "Dispute filed", "id": str(event.id)}
