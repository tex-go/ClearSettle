"""
GET /api-health

Runs every major read-only API service function against the live database
for the authenticated user and returns a pass/fail report with response times.

Use this as a single-URL sanity check after deploys or schema migrations.
"""
from __future__ import annotations

import time
import traceback
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_optional
from app.services.analytics import queries as aq

router = APIRouter()


def _company_id(user):
    if not hasattr(user, "companies") or not user.companies:
        return None
    return user.companies[0].id


async def _probe(label: str, coro) -> dict:
    t0 = time.perf_counter()
    try:
        result = await coro
        ms = round((time.perf_counter() - t0) * 1000, 1)
        # Summarise result so the payload stays compact
        summary = None
        if isinstance(result, dict):
            summary = {k: v for k, v in result.items() if k not in ("series", "items", "fee_items")}
        return {"label": label, "status": "pass", "ms": ms, "summary": summary}
    except Exception as exc:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "label":   label,
            "status":  "fail",
            "ms":      ms,
            "error":   str(exc),
            "trace":   traceback.format_exc(limit=5),
        }


@router.get("")
async def full_api_health(
    user=Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Probes every major service function and returns a health report.

    Each probe entry contains:
      - label       : human-readable endpoint name
      - status      : "pass" | "fail" | "skip"
      - ms          : wall-clock milliseconds
      - summary     : top-level keys from the response (series/items omitted)
      - error/trace : present only on fail
    """
    cid = _company_id(user)

    if db is None:
        return {
            "mode":   "mock",
            "status": "skip",
            "reason": "DATABASE_URL not configured — running in demo/mock mode. "
                      "All endpoints fall back to mock data; no DB probes run.",
            "probes": [],
        }

    if cid is None:
        return {
            "mode":   "db",
            "status": "error",
            "reason": "Authenticated user has no associated company. "
                      "Cannot run per-company probes.",
            "probes": [],
        }

    date_from = date.today() - timedelta(days=90)
    date_to   = date.today()

    probes_coros = [
        ("Dashboard — summary",           aq.get_dashboard_summary(db, cid)),
        ("Analytics — revenue trends",    aq.get_revenue_trends(db, cid, date_from=date_from, date_to=date_to, granularity="month")),
        ("Analytics — revenue (daily)",   aq.get_revenue_trends(db, cid, date_from=date_from, date_to=date_to, granularity="day")),
        ("Analytics — fee breakdown",     aq.get_fee_breakdown(db, cid, date_from=date_from, date_to=date_to)),
        ("Analytics — payout trends",     aq.get_payout_trends(db, cid, date_from=date_from, date_to=date_to, granularity="month")),
        ("Analytics — refund trends",     aq.get_refund_trends(db, cid, date_from=date_from, date_to=date_to, granularity="month")),
        ("Analytics — marketplace",       aq.get_marketplace_breakdown(db, cid, date_from=date_from, date_to=date_to)),
        ("Analytics — recon health",      aq.get_reconciliation_health(db, cid, days=90)),
        ("Analytics — profitability",     aq.get_profitability_metrics(db, cid, date_from=date_from, date_to=date_to, limit=10)),
    ]

    # Run probes sequentially so DB connection isn't overwhelmed
    probes: list[dict] = []
    for label, coro in probes_coros:
        probes.append(await _probe(label, coro))

    # Also probe the settlements router queries
    try:
        from sqlalchemy import select, func
        from app.db.models.settlement import Settlement
        from app.db.models.settlement_transaction import SettlementTransaction
        from app.db.models.fee import Fee
        from app.db.models.payout_event import PayoutEvent
        from app.db.models.reconciliation_result import ReconciliationResult
        from app.db.models.discrepancy_event import DiscrepancyEvent
        from app.db.models.platform_connection import PlatformConnection
        from app.db.models.sync_job import SyncJob

        t0 = time.perf_counter()
        tables = {
            "settlements":              Settlement,
            "settlement_transactions":  SettlementTransaction,
            "fees":                     Fee,
            "payout_events":            PayoutEvent,
            "reconciliation_results":   ReconciliationResult,
            "discrepancy_events":       DiscrepancyEvent,
            "platform_connections":     PlatformConnection,
            "sync_jobs":                SyncJob,
        }
        counts = {}
        for tname, model in tables.items():
            row = (await db.execute(
                select(func.count(model.id)).where(model.company_id == cid)
            )).scalar_one()
            counts[tname] = int(row)

        ms = round((time.perf_counter() - t0) * 1000, 1)
        probes.append({
            "label":   "DB — row counts per table",
            "status":  "pass",
            "ms":      ms,
            "summary": counts,
        })
    except Exception as exc:
        probes.append({
            "label":  "DB — row counts per table",
            "status": "fail",
            "error":  str(exc),
            "trace":  traceback.format_exc(limit=5),
        })

    passed = sum(1 for p in probes if p["status"] == "pass")
    failed = sum(1 for p in probes if p["status"] == "fail")
    total  = len(probes)
    total_ms = sum(p.get("ms", 0) for p in probes)

    return {
        "mode":       "db",
        "status":     "healthy" if failed == 0 else "degraded",
        "company_id": str(cid),
        "summary": {
            "passed":    passed,
            "failed":    failed,
            "total":     total,
            "total_ms":  round(total_ms, 1),
        },
        "probes": probes,
    }
