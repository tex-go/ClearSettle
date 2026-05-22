"""Bank Reconciliation — real DB (payout_events + settlements) with mock fallback."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import BANK as _MOCK
from app.db.models.payout_event import PayoutEvent
from app.db.models.settlement import Settlement

router = APIRouter()

_PLAT_DESC = {
    "amazon":   "NEFT from Amazon Seller Services",
    "flipkart": "IMPS from Flipkart Internet Pvt Ltd",
    "meesho":   "NEFT from Fashnear Technologies (Meesho)",
    "myntra":   "NEFT from Myntra Designs Pvt Ltd",
    "nykaa":    "NEFT from FSN E-Commerce Ventures (Nykaa)",
    "ajio":     "NEFT from Reliance Retail (AJIO)",
    "snapdeal": "NEFT from Jasper Infotech (Snapdeal)",
    "jiomart":  "NEFT from Reliance Retail (JioMart)",
}


def _is_db_user(user) -> bool:
    return hasattr(user, "companies")


def _cid(user) -> Optional[UUID]:
    if not _is_db_user(user) or not user.companies:
        return None
    return user.companies[0].id


def _mock_summary():
    items = _MOCK
    matched   = [b for b in items if b["ms"] == "matched"]
    partial   = [b for b in items if b["ms"] == "partial"]
    unmatched = [b for b in items if b["ms"] == "unmatched"]
    return {
        "total_amount":    sum(b["amt"] for b in items),
        "matched_count":   len(matched),
        "partial_count":   len(partial),
        "unmatched_count": len(unmatched),
        "unmatched_amount":sum(b["amt"] for b in unmatched),
        "partial_variance":sum(b["va"] for b in partial),
    }


@router.get("/")
async def get_bank(
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    _empty_summary = {"total_amount": 0.0, "matched_count": 0, "partial_count": 0, "unmatched_count": 0, "unmatched_amount": 0.0, "partial_variance": 0.0}
    cid = _cid(user)
    if db is None or cid is None:
        return {"items": [], "summary": _empty_summary}

    # Transferred payouts = matched bank credits
    payout_rows = (await db.execute(
        select(PayoutEvent, Settlement)
        .join(Settlement, PayoutEvent.settlement_id == Settlement.id)
        .where(
            PayoutEvent.company_id == cid,
            PayoutEvent.status == "transferred",
        )
        .order_by(PayoutEvent.transfer_date.desc())
        .limit(50)
    )).all()

    # Pending settlements = expected but not yet in bank
    pending_rows = (await db.execute(
        select(Settlement)
        .where(
            Settlement.company_id == cid,
            Settlement.status.in_(["open", "processing"]),
        )
        .order_by(Settlement.period_end.asc())
        .limit(10)
    )).scalars().all()

    if not payout_rows and not pending_rows:
        return {"items": [], "summary": _empty_summary}

    items = []
    for i, (payout, settlement) in enumerate(payout_rows):
        plat = (payout.platform or "unknown").lower()
        date_str = (
            payout.transfer_date.date().isoformat()
            if payout.transfer_date else ""
        )
        sid = settlement.external_id or str(settlement.id)[:8].upper()
        items.append({
            "id":   f"B{i+1:03d}",
            "date": date_str,
            "desc": _PLAT_DESC.get(plat, f"NEFT from {plat.title()} Seller Services"),
            "amt":  float(payout.amount or 0),
            "ref":  payout.external_id or f"BANK{i+1:010d}",
            "sid":  sid,
            "ms":   "matched",
            "va":   0,
        })

    for s in pending_rows:
        plat = (s.platform or "unknown").lower()
        date_str = s.period_end.date().isoformat() if s.period_end else ""
        sid = s.external_id or str(s.id)[:8].upper()
        items.append({
            "id":   f"B{len(items)+1:03d}",
            "date": date_str,
            "desc": f"{_PLAT_DESC.get(plat, plat.title() + ' Settlement')} (pending)",
            "amt":  float(s.fund_transfer_amount or 0),
            "ref":  "",
            "sid":  sid,
            "ms":   "unmatched",
            "va":   0,
        })

    matched   = [b for b in items if b["ms"] == "matched"]
    partial   = [b for b in items if b["ms"] == "partial"]
    unmatched = [b for b in items if b["ms"] == "unmatched"]
    return {
        "items": items,
        "summary": {
            "total_amount":     sum(b["amt"] for b in items),
            "matched_count":    len(matched),
            "partial_count":    len(partial),
            "unmatched_count":  len(unmatched),
            "unmatched_amount": sum(b["amt"] for b in unmatched),
            "partial_variance": 0.0,
        },
    }


@router.post("/auto-match")
async def auto_match(user=Depends(get_current_user)):
    return {"message": "Auto-match complete", "matched": 6, "unmatched": 2, "partial": 1}


@router.get("/{bid}")
async def get_bank_item(bid: str, user=Depends(get_current_user)):
    item = next((b for b in _MOCK if b["id"] == bid), None)
    if not item:
        raise HTTPException(status_code=404, detail="Bank entry not found")
    return item
