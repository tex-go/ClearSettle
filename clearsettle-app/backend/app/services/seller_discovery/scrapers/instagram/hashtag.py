"""
Hashtag discovery strategy.

Drives the complete hashtag-to-profiles flow:
  1. Open the Instagram hashtag page (via scraper browser context).
  2. Extract post author usernames from the page.
  3. Scroll / paginate to collect up to max_profiles usernames.
  4. Deduplicate the username list.
  5. Return the list — orchestrator then calls scrape_profile() for each.

This module contains ONLY flow coordination logic.
No Playwright code lives here — the scraper (Phase 5) provides the page HTML.
This keeps the strategy testable without a browser.

Compliance notes:
  - Each page request is gated by the rate limiter (polite delay + jitter).
  - Stops immediately when max_profiles is reached.
  - Never stores raw HTML beyond the current call stack.
"""
from __future__ import annotations

import logging

from app.services.seller_discovery.scrapers.rate_limiter import AsyncTokenBucket
from app.services.seller_discovery.scrapers.result_models import RawProfile, ScrapeResult

logger = logging.getLogger(__name__)


class HashtagDiscoveryStrategy:
    """
    Discover seller leads from a single Instagram hashtag.

    Injected dependencies:
      scraper      — AbstractScraper implementation (provided in Phase 5)
      rate_limiter — AsyncTokenBucket shared across the orchestrator session

    Usage:
        strategy = HashtagDiscoveryStrategy(scraper, rate_limiter)
        usernames = await strategy.discover_usernames("#ethnicwear", max_profiles=200)
        for username in usernames:
            profile = await scraper.scrape_profile(username)
    """

    MAX_SCROLL_PAGES = 10   # safety limit — avoids infinite pagination loops

    def __init__(self, scraper, rate_limiter: AsyncTokenBucket):
        # scraper typed as Any here (AbstractScraper not imported to avoid circular)
        self._scraper = scraper
        self._limiter = rate_limiter

    async def discover_usernames(
        self,
        hashtag: str,
        max_profiles: int = 100,
    ) -> list[str]:
        """
        Return up to max_profiles unique usernames found under the hashtag.

        Steps:
          1. Normalise hashtag (strip #, lowercase).
          2. Fetch hashtag page HTML via scraper.
          3. Parse usernames from page.
          4. Scroll/paginate up to MAX_SCROLL_PAGES or max_profiles hit.

        Returns an empty list if the scraper is not yet implemented (Phase 5)
        or if the hashtag returns no results.
        """
        tag = _normalize_hashtag(hashtag)
        logger.info("HashtagStrategy: starting discovery for #%s max=%d", tag, max_profiles)

        usernames: list[str] = []
        seen: set[str] = set()

        for page_num in range(self.MAX_SCROLL_PAGES):
            if len(usernames) >= max_profiles:
                logger.info("HashtagStrategy: reached limit of %d profiles", max_profiles)
                break

            await self._limiter.acquire()

            try:
                # scraper.scrape_hashtag_page() will be implemented in Phase 5.
                # The method returns a list of usernames directly from the HTML.
                page_usernames: list[str] = await self._scraper.scrape_hashtag_page(
                    tag, page=page_num
                )
            except NotImplementedError:
                logger.warning(
                    "HashtagStrategy: scraper not yet implemented (Phase 5). "
                    "No profiles collected for #%s.", tag,
                )
                break
            except Exception as exc:
                logger.error("HashtagStrategy: page %d error for #%s: %s", page_num, tag, exc)
                break

            if not page_usernames:
                logger.debug("HashtagStrategy: no more usernames on page %d", page_num)
                break

            new_count = 0
            for u in page_usernames:
                if u not in seen and len(usernames) < max_profiles:
                    seen.add(u)
                    usernames.append(u)
                    new_count += 1

            logger.debug(
                "HashtagStrategy: page %d — %d new usernames (total %d)",
                page_num, new_count, len(usernames),
            )

            if new_count == 0:
                break   # all duplicates — no more unique accounts to scrape

        logger.info("HashtagStrategy: discovered %d unique usernames for #%s", len(usernames), tag)
        return usernames

    async def run(
        self,
        hashtag: str,
        max_profiles: int = 100,
    ) -> ScrapeResult:
        """
        Full hashtag discovery run: discover usernames → scrape each profile.

        This is the method called by the orchestrator for job_type='hashtag'.
        """
        usernames = await self.discover_usernames(hashtag, max_profiles)

        profiles: list[RawProfile] = []
        for username in usernames:
            await self._limiter.acquire()
            try:
                profile = await self._scraper.scrape_profile(username)
                if profile and not profile.is_private:
                    profile.discovery_source  = "hashtag"
                    profile.discovery_keyword = hashtag
                    profiles.append(profile)
            except NotImplementedError:
                break
            except Exception as exc:
                logger.warning("HashtagStrategy: profile scrape failed for @%s: %s", username, exc)
                continue

        return ScrapeResult(
            profiles    = profiles,
            total_found = len(usernames),
            reached_limit = len(usernames) >= max_profiles,
        )


class CompetitorFollowerStrategy:
    """
    Discover leads from a competitor brand's public follower list.

    Flow:
      1. Open competitor's follower list.
      2. Collect follower usernames.
      3. For each follower, scrape profile.
      4. Filter by profile signals (follower count, bio keywords, etc.).

    Full implementation in Phase 5. Stub here for architecture completeness.
    """

    def __init__(self, scraper, rate_limiter: AsyncTokenBucket):
        self._scraper = scraper
        self._limiter = rate_limiter

    async def run(self, competitor_username: str, max_profiles: int = 100) -> ScrapeResult:
        logger.warning(
            "CompetitorFollowerStrategy: not yet implemented — "
            "requires Playwright (Phase 5)."
        )
        return ScrapeResult(
            error="CompetitorFollowerStrategy not implemented until Phase 5."
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_hashtag(tag: str) -> str:
    """Strip # prefix, lowercase, remove whitespace."""
    return tag.strip().lstrip("#").lower().replace(" ", "")
