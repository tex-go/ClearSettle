"""Recovery Tracker — real DB (discrepancy_events) with empty fallback when DB absent."""
from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.db.models.discrepancy_event import DiscrepancyEvent

router = APIRouter()

_ROUTE_BY_TYPE = {
    "OVERCHARGE_REFERRAL_FEE": "Platform",
    "OVERCHARGE_FBA_FEE":      "Platform",
    "PAYOUT_AMOUNT_MISMATCH":  "Platform",
    "MISSING_PAYOUT":          "Platform",
    "DUPLICATE_DEDUCTION":     "Platform",
    "PENALTY_MISMATCH":        "Platform",
    "UNEXPECTED_FEE":          "Legal",
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


def _disc_to_recovery(d: DiscrepancyEvent) -> dict:
    created = d.created_at or datetime.utcnow()
    expected_date = (created + timedelta(days=21)).date()
    today = date.today()
    days_left = (expected_date - today).days if not d.is_resolved else None
    disc_type = d.discrepancy_type or ""
    status = "won" if d.is_resolved else ("open" if days_left and days_left > 0 else "pending")
    return {
        "id":        str(d.id),
        "ref":       "CS-" + str(d.id)[:10].upper(),
        "type":      _TYPE_LABEL.get(disc_type, disc_type.replace("_", " ").title()),
        "platform":  (d.platform or "unknown").title(),
        "sku":       None,
        "amount":    float(abs(d.variance_amount or 0)),
        "status":    status,
        "raised":    created.date().isoformat(),
        "expected":  expected_date.isoformat(),
        "route":     _ROUTE_BY_TYPE.get(disc_type, "Platform"),
        "days_left": days_left,
        "notes":     d.description or "",
        "severity":  d.severity or "warning",
    }


_EMPTY_SUMMARY = {"total_amount": 0.0, "won_amount": 0.0, "open_amount": 0.0, "gst_amount": 0.0}


@router.get("/")
async def get_recovery(
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    cid = _cid(user)
    if db is None or cid is None:
        return {"items": [], "summary": _EMPTY_SUMMARY}

    rows = (await db.execute(
        select(DiscrepancyEvent)
        .where(DiscrepancyEvent.company_id == cid)
        .order_by(DiscrepancyEvent.created_at.desc())
        .limit(100)
    )).scalars().all()

    items = [_disc_to_recovery(d) for d in rows]
    won_items  = [r for r in items if r["status"] == "won"]
    open_items = [r for r in items if r["status"] == "open"]
    return {
        "items": items,
        "summary": {
            "total_amount": sum(r["amount"] for r in items),
            "won_amount":   sum(r["amount"] for r in won_items),
            "open_amount":  sum(r["amount"] for r in open_items),
            "gst_amount":   0.0,
        },
    }


class RecoveryUpdate(BaseModel):
    note: Optional[str] = None
    new_status: Optional[str] = None


@router.put("/{rid}/update")
async def update_recovery(
    rid: str,
    body: RecoveryUpdate,
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    cid = _cid(user)
    if db is None or cid is None:
        return {"message": "Recovery " + rid + " updated (no DB)", "note": body.note}

    try:
        uid = UUID(rid)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    row = (await db.execute(
        select(DiscrepancyEvent)
        .where(DiscrepancyEvent.id == uid, DiscrepancyEvent.company_id == cid)
    )).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    if body.note:
        row.description = body.note
    if body.new_status == "won":
        row.is_resolved = True
    elif body.new_status in ("open", "pending"):
        row.is_resolved = False

    await db.commit()
    return {"message": "Recovery case updated", "id": rid}


@router.post("/{rid}/legal-notice")
async def legal_notice(rid: str, user=Depends(get_current_user)):
    return {"message": "Legal notice drafted for " + rid, "status": "ready_for_review"}
