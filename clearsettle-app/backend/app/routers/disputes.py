"""Disputes — real DB (discrepancy_events) with mock fallback."""
from __future__ import annotations

import copy
import time
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import DISPUTES as _MOCK
from app.db.models.discrepancy_event import DiscrepancyEvent

router = APIRouter()
_mock_disputes = copy.deepcopy(_MOCK)

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
        "id":         str(d.id)[:8].upper(),
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


def _mock_summary():
    items = _mock_disputes
    won = [d for d in items if d["status"] == "won"]
    return {
        "total_amount":  sum(d["amt"] for d in items),
        "open_count":    sum(1 for d in items if d["status"] in ("open", "pending")),
        "won_count":     len(won),
        "won_amount":    sum(d["amt"] for d in won),
    }


@router.get("/")
async def get_disputes(
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    cid = _cid(user)
    if db is None or cid is None:
        return {"items": _mock_disputes, "summary": _mock_summary()}

    rows = (await db.execute(
        select(DiscrepancyEvent)
        .where(DiscrepancyEvent.company_id == cid)
        .order_by(DiscrepancyEvent.created_at.desc())
        .limit(100)
    )).scalars().all()

    if not rows:
        return {"items": _mock_disputes, "summary": _mock_summary()}

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
):
    ref = "DISP-" + str(int(time.time()))[-4:]
    new = {
        "id": ref, "plat": body.platform, "icon": _ICON.get(body.platform.lower(), "🏪"),
        "type": body.dispute_type, "amt": body.amount,
        "desc": body.description, "status": "open",
        "raised":     datetime.utcnow().date().isoformat(),
        "expected":   (datetime.utcnow() + timedelta(days=14)).date().isoformat(),
        "ref": ref, "resolution": None,
    }
    _mock_disputes.append(new)
    return new


@router.get("/{did}")
async def get_dispute(did: str, user=Depends(get_current_user)):
    item = next((d for d in _mock_disputes if d["id"] == did), None)
    if not item:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return item


class DisputeUpdate(BaseModel):
    note: Optional[str] = None


@router.put("/{did}/update")
async def update_dispute(did: str, body: DisputeUpdate, user=Depends(get_current_user)):
    return {"message": "Dispute " + did + " updated", "note": body.note}
