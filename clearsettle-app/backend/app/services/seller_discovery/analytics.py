"""
Analytics queries for the Seller Discovery Engine — Phase 11.

All functions accept an open AsyncSession.
All return plain dicts/lists — no Pydantic models, to keep the layer thin.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.seller_lead import DiscoveryJob, DiscoveryKeyword, SellerLead


async def get_overview(db: AsyncSession) -> dict:
    """High-level KPI snapshot."""
    total_leads = (await db.execute(
        select(func.count(SellerLead.id))
        .where(SellerLead.lead_status != "deleted")
    )).scalar_one() or 0

    qualified = (await db.execute(
        select(func.count(SellerLead.id))
        .where(SellerLead.lead_status.in_(["qualified", "approved", "contact_ready"]))
    )).scalar_one() or 0

    classified = (await db.execute(
        select(func.count(SellerLead.id))
        .where(SellerLead.ai_classified_at.isnot(None))
    )).scalar_one() or 0

    hot_leads = (await db.execute(
        select(func.count(SellerLead.id))
        .where(SellerLead.priority_level == "hot")
    )).scalar_one() or 0

    total_jobs = (await db.execute(select(func.count(DiscoveryJob.id)))).scalar_one() or 0

    active_jobs = (await db.execute(
        select(func.count(DiscoveryJob.id))
        .where(DiscoveryJob.status == "running")
    )).scalar_one() or 0

    review_queue = (await db.execute(
        select(func.count(SellerLead.id))
        .where(SellerLead.lead_status.in_(["new", "review_pending"]))
    )).scalar_one() or 0

    outreach_ready = (await db.execute(
        select(func.count(SellerLead.id))
        .where(SellerLead.lead_status.in_(["contact_ready", "qualified"]))
    )).scalar_one() or 0

    return {
        "total_leads":         total_leads,
        "qualified_leads":     qualified,
        "classified_leads":    classified,
        "hot_leads":           hot_leads,
        "total_jobs":          total_jobs,
        "active_jobs":         active_jobs,
        "review_queue_size":   review_queue,
        "outreach_ready":      outreach_ready,
        "classification_rate": round(classified / max(total_leads, 1) * 100, 1),
        "qualification_rate":  round(qualified  / max(total_leads, 1) * 100, 1),
    }


async def get_leads_per_day(db: AsyncSession, days: int = 30) -> list[dict]:
    """Daily lead discovery counts for the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = await db.execute(
        select(
            func.date(SellerLead.created_at).label("day"),
            func.count(SellerLead.id).label("count"),
        )
        .where(SellerLead.created_at >= cutoff)
        .group_by(func.date(SellerLead.created_at))
        .order_by(func.date(SellerLead.created_at))
    )
    return [{"day": str(r.day), "count": r.count} for r in rows]


async def get_source_breakdown(db: AsyncSession) -> list[dict]:
    """Lead counts by discovery source."""
    rows = await db.execute(
        select(
            SellerLead.source,
            func.count(SellerLead.id).label("total"),
            func.sum(case((SellerLead.ai_is_ecommerce == True, 1), else_=0)).label("ecommerce"),
        )
        .where(SellerLead.lead_status != "deleted")
        .group_by(SellerLead.source)
        .order_by(func.count(SellerLead.id).desc())
    )
    return [
        {"source": r.source, "total": r.total, "ecommerce": int(r.ecommerce or 0)}
        for r in rows
    ]


async def get_score_distribution(db: AsyncSession) -> list[dict]:
    """Lead counts by priority bucket (hot/warm/cold/skip/unscored)."""
    rows = await db.execute(
        select(
            SellerLead.priority_level,
            func.count(SellerLead.id).label("count"),
        )
        .where(SellerLead.lead_status != "deleted")
        .group_by(SellerLead.priority_level)
    )
    order = {"hot": 0, "warm": 1, "cold": 2, "skip": 3, None: 4}
    items = [{"priority": r.priority_level or "unscored", "count": r.count} for r in rows]
    items.sort(key=lambda x: order.get(x["priority"] if x["priority"] != "unscored" else None, 4))
    return items


async def get_status_breakdown(db: AsyncSession) -> list[dict]:
    """Lead counts by lifecycle status."""
    rows = await db.execute(
        select(
            SellerLead.lead_status,
            func.count(SellerLead.id).label("count"),
        )
        .group_by(SellerLead.lead_status)
        .order_by(func.count(SellerLead.id).desc())
    )
    return [{"status": r.lead_status, "count": r.count} for r in rows]


async def get_category_breakdown(db: AsyncSession) -> list[dict]:
    """AI category distribution for classified leads."""
    rows = await db.execute(
        select(
            SellerLead.ai_category,
            func.count(SellerLead.id).label("count"),
        )
        .where(
            SellerLead.ai_category.isnot(None),
            SellerLead.lead_status != "deleted",
        )
        .group_by(SellerLead.ai_category)
        .order_by(func.count(SellerLead.id).desc())
        .limit(10)
    )
    return [{"category": r.ai_category, "count": r.count} for r in rows]


async def get_keyword_performance(db: AsyncSession) -> list[dict]:
    """Top-20 keywords by leads found."""
    rows = await db.execute(
        select(
            DiscoveryKeyword.keyword,
            DiscoveryKeyword.source,
            DiscoveryKeyword.crawl_count,
            DiscoveryKeyword.leads_found,
            DiscoveryKeyword.is_active,
            DiscoveryKeyword.last_crawled_at,
        )
        .order_by(DiscoveryKeyword.leads_found.desc())
        .limit(20)
    )
    return [
        {
            "keyword":        r.keyword,
            "source":         r.source,
            "crawl_count":    r.crawl_count,
            "leads_found":    r.leads_found,
            "leads_per_crawl": round(r.leads_found / max(r.crawl_count, 1), 1),
            "is_active":      r.is_active,
            "last_crawled_at": r.last_crawled_at.isoformat() if r.last_crawled_at else None,
        }
        for r in rows
    ]


async def get_job_stats(db: AsyncSession) -> list[dict]:
    """Job success/failure rates by source."""
    rows = await db.execute(
        select(
            DiscoveryJob.source,
            func.count(DiscoveryJob.id).label("total"),
            func.sum(case((DiscoveryJob.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((DiscoveryJob.status == "failed",    1), else_=0)).label("failed"),
            func.sum(DiscoveryJob.leads_found).label("leads_found"),
        )
        .group_by(DiscoveryJob.source)
    )
    return [
        {
            "source":       r.source,
            "total_jobs":   r.total,
            "completed":    int(r.completed or 0),
            "failed":       int(r.failed or 0),
            "success_rate": round(int(r.completed or 0) / max(r.total, 1) * 100, 1),
            "leads_found":  int(r.leads_found or 0),
        }
        for r in rows
    ]


async def get_full_analytics(db: AsyncSession) -> dict:
    """Single call that aggregates all analytics sections."""
    overview, leads_per_day, source, score_dist, status, category, keywords, jobs = (
        await get_overview(db),
        await get_leads_per_day(db),
        await get_source_breakdown(db),
        await get_score_distribution(db),
        await get_status_breakdown(db),
        await get_category_breakdown(db),
        await get_keyword_performance(db),
        await get_job_stats(db),
    )
    return {
        "overview":            overview,
        "leads_per_day":       leads_per_day,
        "source_breakdown":    source,
        "score_distribution":  score_dist,
        "status_breakdown":    status,
        "category_breakdown":  category,
        "keyword_performance": keywords,
        "job_stats":           jobs,
    }
