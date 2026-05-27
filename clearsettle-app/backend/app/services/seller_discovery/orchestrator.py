"""
Discovery job orchestrator — Phase 6 update.

Changes from Phase 5:
  - Emits SSE events via event_bus throughout every pipeline stage.
  - Execution is gated by the concurrency semaphore in queue_manager.
  - run_job_background() now goes through queue_manager.dispatch_job().

Pipeline events emitted (in order):
  job_started → profile_found* → lead_created* | lead_duplicate* → progress* →
  job_completed | job_failed → (stream_end sent by SSE endpoint)

Entry points:
  run_discovery_job(job_id, db)  ← internal; receives open session
  (queue_manager.dispatch_job handles background entry + semaphore)
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import AsyncSessionLocal
from app.services.seller_discovery import event_bus, job_manager, keyword_store, lead_store
from app.services.seller_discovery.scrapers.base import ScraperConfig, get_scraper_class
from app.services.seller_discovery.scrapers.rate_limiter import make_rate_limiter

logger = logging.getLogger(__name__)

# Auto-register scrapers
def _register_scrapers() -> None:
    try:
        from app.services.seller_discovery.scrapers.instagram import scraper as _ig  # noqa: F401
    except ImportError:
        logger.debug("Instagram scraper not importable")

_register_scrapers()


# ── Public entry point ────────────────────────────────────────────────────────

async def run_discovery_job(job_id: UUID, db: AsyncSession) -> None:
    """
    Main pipeline. Accepts an open session — caller owns lifecycle.
    Called by queue_manager.dispatch_job() which owns the semaphore.
    """
    # ── 1. Load job ───────────────────────────────────────────────────────────
    job = await job_manager.get_job(db, job_id)
    if not job:
        logger.error("Orchestrator: job %s not found", job_id)
        return

    if job.status not in ("queued",):
        logger.warning("Orchestrator: job %s status=%s — skipping", job_id, job.status)
        return

    # ── 2. Start ──────────────────────────────────────────────────────────────
    job = await job_manager.start_job(db, job)
    await event_bus.emit(job_id, {
        "type":     "job_started",
        "job_id":   str(job_id),
        "keyword":  job.keyword,
        "strategy": job.job_type,
        "source":   job.source,
    })

    settings      = get_settings()
    leads_found   = 0
    leads_created = 0
    leads_dupes   = 0

    try:
        # ── 3. Scraper config ─────────────────────────────────────────────────
        config = ScraperConfig(
            max_results       = min(job.max_leads, settings.discovery_max_leads_per_job),
            request_delay_min = 2.0,
            request_delay_max = max(2.0, 1.0 / settings.discovery_rate_limit_rps),
            proxy_url         = settings.scraper_proxy_url or None,
            headless          = True,
        )

        # ── 4. Resolve scraper ────────────────────────────────────────────────
        scraper_cls = get_scraper_class(job.source)

        # ── 5. Scrape ─────────────────────────────────────────────────────────
        logger.info("Orchestrator: %s job=%s keyword='%s'", job.source, job_id, job.keyword)

        async with scraper_cls(config) as scraper:
            result = await scraper.scrape(target=job.keyword, strategy=job.job_type)

        if result.error:
            raise RuntimeError(f"Scraper error: {result.error}")

        leads_found = result.total_found

        # ── 6. Store profiles ─────────────────────────────────────────────────
        for profile in result.profiles:
            await event_bus.emit(job_id, {
                "type":      "profile_found",
                "username":  profile.username,
                "followers": profile.followers_count,
            })

            try:
                lead, created = await lead_store.create_or_update_lead(
                    db, data=profile.to_lead_dict(), job_id=job_id,
                )
                if created:
                    leads_created += 1
                    await event_bus.emit(job_id, {
                        "type":     "lead_created",
                        "username": profile.username,
                        "lead_id":  str(lead.id),
                    })
                else:
                    leads_dupes += 1
                    await event_bus.emit(job_id, {
                        "type":     "lead_duplicate",
                        "username": profile.username,
                    })

                # Progress update every 10 leads
                total_processed = leads_created + leads_dupes
                if total_processed % 10 == 0:
                    await event_bus.emit(job_id, {
                        "type":          "progress",
                        "leads_found":   leads_found,
                        "leads_created": leads_created,
                        "leads_dupes":   leads_dupes,
                    })
                    await job_manager.increment_counters(
                        db, job_id,
                        leads_found        = 10,
                        leads_created      = leads_created,
                        leads_skipped_dupe = leads_dupes,
                    )
                    leads_created = 0
                    leads_dupes   = 0

            except Exception as exc:
                logger.warning("Failed to store @%s: %s", profile.username, exc)
                await event_bus.emit(job_id, {
                    "type":     "lead_skipped",
                    "username": profile.username,
                    "reason":   str(exc)[:200],
                })
                continue

        # ── 7. Keyword stats ──────────────────────────────────────────────────
        if job.keyword_id:
            kw = await keyword_store.get_keyword(db, job.keyword_id)
            if kw:
                await keyword_store.mark_crawled(db, kw, leads_found=leads_found)

        # ── 8. Complete ───────────────────────────────────────────────────────
        await job_manager.complete_job(
            db, job,
            leads_found        = leads_found,
            leads_created      = leads_created,
            leads_skipped_dupe = leads_dupes,
            leads_classified   = 0,
        )
        await event_bus.emit(job_id, {
            "type":          "job_completed",
            "leads_found":   leads_found,
            "leads_created": leads_created,
        })
        logger.info(
            "Orchestrator: job %s done — found=%d created=%d dupes=%d",
            job_id, leads_found, leads_created, leads_dupes,
        )

    except ValueError as exc:
        error_msg = str(exc)
        logger.warning("Orchestrator: job %s — %s", job_id, error_msg)
        await event_bus.emit(job_id, {"type": "job_failed", "error": error_msg})
        await job_manager.fail_job(db, job, error=error_msg)

    except Exception as exc:
        exc_str = str(exc)
        if "blocked" in exc_str.lower() or "ScraperBlockedError" in type(exc).__name__:
            error_msg = f"Blocked by Instagram (rate-limit / challenge). {exc_str}"
            logger.warning("Orchestrator: job %s blocked", job_id)
            await event_bus.emit(job_id, {"type": "blocked", "message": error_msg})
        else:
            error_msg = f"{type(exc).__name__}: {exc_str}"
            logger.exception("Orchestrator: job %s failed", job_id)
            await event_bus.emit(job_id, {"type": "job_failed", "error": error_msg})
        await job_manager.fail_job(db, job, error=error_msg)

    finally:
        await event_bus.close(job_id)
