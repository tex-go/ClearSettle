"""CRUD for CashFlowSnapshot — stores generated aggregates."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.cash_flow_snapshot import CashFlowSnapshot

logger = logging.getLogger(__name__)


def snapshot_to_dict(s: CashFlowSnapshot) -> dict:
    return {
        "id":                s.id.__str__(),
        "company_id":        str(s.company_id),
        "snapshot_date":     s.snapshot_date.isoformat(),
        "period_type":       s.period_type,
        "opening_balance":   float(s.opening_balance),
        "inflows":           float(s.inflows),
        "outflows":          float(s.outflows),
        "net_cash_flow":     float(s.net_cash_flow),
        "closing_balance":   float(s.closing_balance),
        "settlements_count": s.settlements_count,
        "fees_total":        float(s.fees_total),
        "currency":          s.currency,
        "platform_breakdown_json": s.platform_breakdown_json,
        "ai_shortage_risk":  s.ai_shortage_risk,
        "ai_insights_json":  s.ai_insights_json,
        "ai_generated_at":   s.ai_generated_at.isoformat() if s.ai_generated_at else None,
        "created_at":        s.created_at.isoformat(),
        "updated_at":        s.updated_at.isoformat(),
    }


async def upsert_snapshot(
    db: AsyncSession,
    company_id: UUID,
    *,
    snapshot_date: date,
    period_type: str,
    data: dict[str, Any],
) -> CashFlowSnapshot:
    result = await db.execute(
        select(CashFlowSnapshot).where(
            CashFlowSnapshot.company_id   == company_id,
            CashFlowSnapshot.snapshot_date == snapshot_date,
            CashFlowSnapshot.period_type  == period_type,
        )
    )
    snap = result.scalar_one_or_none()

    if snap is None:
        snap = CashFlowSnapshot(
            company_id    = company_id,
            snapshot_date = snapshot_date,
            period_type   = period_type,
        )

    snap.opening_balance      = Decimal(str(data.get("opening_balance", 0)))
    snap.inflows              = Decimal(str(data.get("inflows", 0)))
    snap.outflows             = Decimal(str(data.get("outflows", 0)))
    snap.net_cash_flow        = Decimal(str(data.get("net", 0)))
    snap.closing_balance      = Decimal(str(data.get("closing_balance", 0)))
    snap.settlements_count    = int(data.get("settlements_count", 0))
    snap.fees_total           = Decimal(str(data.get("fees_total", 0)))
    snap.currency             = data.get("currency", "INR")
    snap.platform_breakdown_json = data.get("platform_breakdown")
    snap.updated_at           = datetime.utcnow()

    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap


async def list_snapshots(
    db: AsyncSession,
    company_id: UUID,
    *,
    period_type: str = "monthly",
    start_date: date | None = None,
    end_date:   date | None = None,
    limit: int = 24,
) -> list[CashFlowSnapshot]:
    filters = [
        CashFlowSnapshot.company_id  == company_id,
        CashFlowSnapshot.period_type == period_type,
    ]
    if start_date:
        filters.append(CashFlowSnapshot.snapshot_date >= start_date)
    if end_date:
        filters.append(CashFlowSnapshot.snapshot_date <= end_date)

    result = await db.execute(
        select(CashFlowSnapshot)
        .where(*filters)
        .order_by(CashFlowSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_latest_snapshot(
    db: AsyncSession,
    company_id: UUID,
    period_type: str = "monthly",
) -> CashFlowSnapshot | None:
    result = await db.execute(
        select(CashFlowSnapshot)
        .where(
            CashFlowSnapshot.company_id  == company_id,
            CashFlowSnapshot.period_type == period_type,
        )
        .order_by(CashFlowSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
