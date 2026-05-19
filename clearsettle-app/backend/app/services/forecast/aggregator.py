"""
Pulls raw financial data from settlements and fees, aggregates by period.

Aggregation logic:
  inflows  = sum of fund_transfer_amount for closed/completed settlements
  outflows = sum of |fees_total| (fees are stored as negative on Fee rows)
  net      = inflows - outflows
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.settlement import Settlement

logger = logging.getLogger(__name__)

_PERIOD_TRUNCATE = {
    "daily":     "day",
    "weekly":    "week",
    "monthly":   "month",
    "quarterly": "quarter",
}


async def aggregate_settlements(
    db: AsyncSession,
    company_id: UUID,
    *,
    start_date: date,
    end_date: date,
    period_type: str = "monthly",
) -> list[dict[str, Any]]:
    """
    Return one dict per period bucket containing aggregated cash flow numbers.

    Each dict:
      period_start, period_end, inflows, outflows, net, settlements_count,
      fees_total, currency, platform_breakdown
    """
    trunc = _PERIOD_TRUNCATE.get(period_type, "month")

    result = await db.execute(
        select(
            func.date_trunc(trunc, Settlement.fund_transfer_date).label("bucket"),
            func.sum(
                func.coalesce(Settlement.fund_transfer_amount, Decimal("0"))
            ).label("inflows"),
            func.sum(
                func.coalesce(Settlement.fees_total, Decimal("0"))
            ).label("fees_total"),
            func.count(Settlement.id).label("count"),
            Settlement.platform,
            Settlement.currency,
        )
        .where(
            Settlement.company_id == company_id,
            Settlement.status.in_(["closed", "completed", "open"]),
            Settlement.fund_transfer_date >= datetime.combine(start_date, datetime.min.time()),
            Settlement.fund_transfer_date <= datetime.combine(end_date, datetime.max.time()),
        )
        .group_by("bucket", Settlement.platform, Settlement.currency)
        .order_by("bucket")
    )
    rows = result.all()

    # Group by bucket → aggregate across platforms
    buckets: dict[str, dict] = {}
    for row in rows:
        if row.bucket is None:
            continue
        key = row.bucket.date().isoformat()
        if key not in buckets:
            buckets[key] = {
                "period_start":       row.bucket.date().isoformat(),
                "inflows":            Decimal("0"),
                "outflows":           Decimal("0"),
                "fees_total":         Decimal("0"),
                "settlements_count":  0,
                "currency":           row.currency or "INR",
                "platform_breakdown": {},
            }
        bucket = buckets[key]
        bucket["inflows"]           += row.inflows or Decimal("0")
        bucket["fees_total"]        += row.fees_total or Decimal("0")
        bucket["settlements_count"] += int(row.count or 0)
        # Platform breakdown — inflows only
        platform = row.platform or "unknown"
        bucket["platform_breakdown"][platform] = (
            float(bucket["platform_breakdown"].get(platform, 0)) +
            float(row.inflows or 0)
        )

    # outflows = fees (fees are a deduction)
    for b in buckets.values():
        b["outflows"]      = abs(b["fees_total"])
        b["net"]           = float(b["inflows"]) - float(b["outflows"])
        b["inflows"]       = float(b["inflows"])
        b["outflows"]      = float(b["outflows"])
        b["fees_total"]    = float(b["fees_total"])

    return list(buckets.values())


async def get_current_balance(
    db: AsyncSession,
    company_id: UUID,
    *,
    as_of: date | None = None,
) -> float:
    """Approximate current balance = sum of all fund_transfer_amount to date."""
    cutoff = datetime.combine(as_of or date.today(), datetime.max.time())
    result = await db.execute(
        select(func.sum(func.coalesce(Settlement.fund_transfer_amount, Decimal("0"))))
        .where(
            Settlement.company_id == company_id,
            Settlement.status.in_(["closed", "completed", "open"]),
            Settlement.fund_transfer_date <= cutoff,
        )
    )
    total = result.scalar_one_or_none() or Decimal("0")
    return float(total)
