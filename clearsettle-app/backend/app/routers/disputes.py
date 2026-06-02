"""Disputes — DiscrepancyEvent CRUD + list.

Phase 1: replaced get_db_optional with get_db (the two were identical);
removed all unreachable 'if db is None' branches.  New POST /disputes/ sets
source=manual and workflow_state=detected.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.models.discrepancy_event import DiscrepancyEvent, SOURCE_MANUAL, STATE_DETECTED

router = APIRouter()

_ICON = {
    "amazon": "🛒", "flipkart": "🛍️", "meesho": "👗",
    "myntra": "👠", "nykaa": "💄", "ajio": "👔",
    "snapdeal": "🏷️", "jiomart": "🛒",
}
_TYPE_LABEL = {
    "MISSING_PAYOUT":          "Missing Payout",
    "PAYOUT_AMOUNT_MISMATCH":  "Payout Amount Mismatch",
    "OVERCHARGE_REFERRAL_FEE": "Commission Overcharge",
    "OVERCHARGE_FBA_FEE":      "FBA Fee Overcharge",
    "DUPLICATE_DEDUCTION":     "Duplicate Deduction",
    "UNEXPECTED_FEE":          "Unexpected Fee",
    "PENALTY_MISMATCH":        "Penalty Charge",
}


def _is_db_user(user) -> bool:
    return hasattr(user, "companies")


def _cid(user) -> Optional[UUID]:
    if not _is_db_user(user) or not user.companies:
        return None
    return user.companies[0].id


def _disc_to_item(d: DiscrepancyEvent) -> dict:
    created = d.created_at or datetime.utcnow()
    expected = created + timedelta(days=14)
    disc_type = d.discrepancy_type or ""
    return {
        "id":         str(d.id),
        "plat":       (d.platform or "unknown").title(),
        "icon":       _ICON.get((d.platform or "").lower(), "🏪"),
        "type":       _TYPE_LABEL.get(disc_type, disc_type.replace("_", " ").title()),
        "amt":        float(abs(d.variance_amount or 0)),
        "desc":       d.description or "",
        "status":     "won" if d.is_resolved else "open",
        "severity":   d.severity or "warning",
        "raised":     created.date().isoformat(),
        "expected":   expected.date().isoformat(),
        "ref":        "CS-" + str(d.id)[:8].upper(),
        "resolution": d.description if d.is_resolved else None,
    }


_EMPTY_SUMMARY = {"total_amount": 0.0, "open_count": 0, "won_count": 0, "won_amount": 0.0}


@router.get("/")
async def get_disputes(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cid = _cid(user)
    if cid is None:
        return {"items": [], "summary": _EMPTY_SUMMARY}

    rows = (await db.execute(
        select(DiscrepancyEvent)
        .where(DiscrepancyEvent.company_id == cid)
        .order_by(DiscrepancyEvent.created_at.desc())
        .limit(100)
    )).scalars().all()

    items = [_disc_to_item(d) for d in rows]
    won = [i for i in items if i["status"] == "won"]
    return {
        "items": items,
        "summary": {
            "total_amount": sum(i["amt"] for i in items),
            "open_count":   sum(1 for i in items if i["status"] == "open"),
            "won_count":    len(won),
            "won_amount":   sum(i["amt"] for i in won),
        },
    }


class NewDispute(BaseModel):
    platform: str
    dispute_type: str
    settlement_id: str
    amount: float
    description: str


@router.post("/")
async def create_dispute(
    body: NewDispute,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cid = _cid(user)
    if cid is None:
        raise HTTPException(status_code=422, detail="No company associated with this account")

    event = DiscrepancyEvent(
        company_id=cid,
        platform=body.platform,
        discrepancy_type=body.dispute_type,
        description=body.description,
        variance_amount=body.amount,
        severity="warning",
        source=SOURCE_MANUAL,
        workflow_state=STATE_DETECTED,
        is_resolved=False,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _disc_to_item(event)


@router.get("/{did}")
async def get_dispute(
    did: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cid = _cid(user)
    if cid is None:
        raise HTTPException(status_code=422, detail="No company associated with this account")

    try:
        uid = UUID(did)
    except ValueError:
        raise HTTPException(status_code=404, detail="Dispute not found")

    row = (await db.execute(
        select(DiscrepancyEvent)
        .where(DiscrepancyEvent.id == uid, DiscrepancyEvent.company_id == cid)
    )).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return _disc_to_item(row)


class DisputeUpdate(BaseModel):
    note: Optional[str] = None
    resolved: Optional[bool] = None


@router.put("/{did}/update")
async def update_dispute(
    did: str,
    body: DisputeUpdate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cid = _cid(user)
    if cid is None:
        raise HTTPException(status_code=422, detail="No company associated with this account")

    try:
        uid = UUID(did)
    except ValueError:
        raise HTTPException(status_code=404, detail="Dispute not found")

    row = (await db.execute(
        select(DiscrepancyEvent)
        .where(DiscrepancyEvent.id == uid, DiscrepancyEvent.company_id == cid)
    )).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if body.note:
        row.description = body.note
    if body.resolved is not None:
        row.is_resolved = body.resolved

    await db.commit()
    return {"message": "Dispute updated", "id": did}
