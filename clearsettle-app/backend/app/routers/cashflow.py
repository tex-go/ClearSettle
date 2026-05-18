"""Cash Flow Forecast — real DB (payout_events + open settlements) with mock fallback."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.data.mock_data import CASHFLOW as _MOCK
from app.db.models.payout_event import PayoutEvent
from app.db.models.settlement import Settlement

router = APIRouter()

_PLAT_LABEL = {
    "amazon": "Amazon", "flipkart": "Flipkart", "meesho": "Meesho",
    "myntra": "Myntra", "nykaa": "Nykaa", "ajio": "AJIO",
    "snapdeal": "Snapdeal", "jiomart": "JioMart",
}


def _is_db_user(user) -> bool:
    return hasattr(user, "companies")


def _cid(user) -> Optional[UUID]:
    if not _is_db_user(user) or not user.companies:
        return None
    return user.companies[0].id


def _mock_summary():
    expected = [e for e in _MOCK if e["type"] in ("expected", "predicted")]
    upcoming = sorted(expected, key=lambda x: x["date"])
    return {
        "expected_total": sum(e["amt"] for e in expected),
        "upcoming_count": len(upcoming),
        "next_settlement": upcoming[0] if upcoming else None,
    }


@router.get("/")
async def get_cashflow(
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    cid = _cid(user)
    if db is None or cid is None:
        return {"events": _MOCK, "summary": _mock_summary()}

    # Transferred payouts → type "paid"
    paid_rows = (await db.execute(
        select(PayoutEvent)
        .where(
            PayoutEvent.company_id == cid,
            PayoutEvent.status == "transferred",
        )
        .order_by(PayoutEvent.transfer_date.desc())
        .limit(30)
    )).scalars().all()

    # Open / processing settlements → type "expected"
    pending_rows = (await db.execute(
        select(Settlement)
        .where(
            Settlement.company_id == cid,
            Settlement.status.in_(["open", "processing"]),
        )
        .order_by(Settlement.period_end.asc())
        .limit(20)
    )).scalars().all()

    if not paid_rows and not pending_rows:
        return {"events": _MOCK, "summary": _mock_summary()}

    events = []

    for p in paid_rows:
        date_str = (
            p.transfer_date.date().isoformat()
            if p.transfer_date else
            p.created_at.date().isoformat() if hasattr(p, "created_at") and p.created_at else ""
        )
        plat_label = _PLAT_LABEL.get((p.platform or "").lower(), (p.platform or "").title())
        events.append({
            "date":  date_str,
            "label": f"{plat_label} Payout",
            "amt":   float(p.amount or 0),
            "type":  "paid",
        })

    for s in pending_rows:
        date_str = s.period_end.date().isoformat() if s.period_end else ""
        plat_label = _PLAT_LABEL.get((s.platform or "").lower(), (s.platform or "").title())
        label = f"{plat_label} {s.external_id or 'Settlement'}"
        events.append({
            "date":  date_str,
            "label": label,
            "amt":   float(s.fund_transfer_amount or 0),
            "type":  "expected",
        })

    events.sort(key=lambda x: x["date"])

    expected = [e for e in events if e["type"] in ("expected", "predicted")]
    upcoming = sorted(expected, key=lambda x: x["date"])

    return {
        "events": events,
        "summary": {
            "expected_total": sum(e["amt"] for e in expected),
            "upcoming_count": len(upcoming),
            "next_settlement": upcoming[0] if upcoming else None,
        },
    }
