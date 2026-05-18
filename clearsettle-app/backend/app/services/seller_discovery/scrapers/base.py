"""
AbstractScraper — interface contract for all scraper implementations.

Design principles:
  - Async context manager so browser/session resources are always released.
  - Strategy pattern: scrape(target, strategy) dispatches to hashtag/profile/follower flows.
  - Config object holds all environment-sensitive values (proxy, delay, UA).
  - No concrete HTTP or browser code here — only the contract.

Extension guide (Phase 5+):
  1. Subclass AbstractScraper.
  2. Implement scrape(), scrape_profile(), close().
  3. Register in SCRAPER_REGISTRY below.
  4. Orchestrator auto-selects implementation by job.source.
"""
from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.services.seller_discovery.scrapers.result_models import RawProfile, ScrapeResult

logger = logging.getLogger(__name__)


# ── Scraper configuration ─────────────────────────────────────────────────────

@dataclass
class ScraperConfig:
    """
    All environment/runtime knobs for one scraper instance.

    Loaded from Settings at orchestrator startup — never hardcoded.
    """
    max_results:        int   = 500     # hard cap per scrape() call
    request_delay_min:  float = 2.0     # seconds — randomised between min/max
    request_delay_max:  float = 5.0
    proxy_url:          str | None = None  # "http://user:pass@host:port"
    headless:           bool  = True
    user_agent:         str   = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    # Persisted browser state (cookies, localStorage) — JSON string or None
    session_data_json:  str | None = None
    # Additional per-source overrides — free-form dict
    extra:              dict = field(default_factory=dict)


# ── Abstract base ─────────────────────────────────────────────────────────────

class AbstractScraper(ABC):
    """
    Base class for all discovery scrapers.

    Usage:
        async with SomeConcreteS scraper(config) as scraper:
            result = await scraper.scrape("#ethnicwear", strategy="hashtag")
    """

    STRATEGY_HASHTAG    = "hashtag"
    STRATEGY_COMPETITOR = "competitor_followers"
    STRATEGY_DIRECT     = "direct"

    def __init__(self, config: ScraperConfig):
        self.config = config
        self._closed = False

    # ── Public API ────────────────────────────────────────────────────────────

    @abstractmethod
    async def scrape(self, target: str, strategy: str) -> ScrapeResult:
        """
        Execute a discovery run.

        target   — hashtag string ("#ethnicwear"), competitor username, or profile URL
        strategy — one of STRATEGY_* constants
        """

    @abstractmethod
    async def scrape_profile(self, username: str) -> RawProfile | None:
        """Scrape a single public profile by username. Returns None if not found / private."""

    @abstractmethod
    async def close(self) -> None:
        """Release all browser / session resources."""

    # ── Context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "AbstractScraper":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._closed:
            await self.close()
            self._closed = True

    # ── Shared utilities ──────────────────────────────────────────────────────

    async def _polite_delay(self) -> None:
        """
        Randomised delay between requests.

        Stays within config.request_delay_min … request_delay_max.
        Called by concrete scrapers between every network request to avoid
        rate-limit bans and maintain compliance with platform TOS.
        """
        delay = random.uniform(self.config.request_delay_min, self.config.request_delay_max)
        logger.debug("Polite delay: %.2fs", delay)
        await asyncio.sleep(delay)


# ── Scraper registry ──────────────────────────────────────────────────────────

# Maps job.source → scraper class.
# Phase 5 registers InstagramScraper here.
# Phase N registers LinkedInScraper, GoogleMapsScraper, etc.
SCRAPER_REGISTRY: dict[str, type[AbstractScraper]] = {}


def register_scraper(source: str, cls: type[AbstractScraper]) -> None:
    """Register a concrete scraper implementation for a source identifier."""
    SCRAPER_REGISTRY[source] = cls
    logger.debug("Scraper registered: source=%s class=%s", source, cls.__name__)


def get_scraper_class(source: str) -> type[AbstractScraper]:
    """
    Look up a registered scraper class by source name.
    Raises ValueError if none is registered — caller should fail the job gracefully.
    """
    cls = SCRAPER_REGISTRY.get(source)
    if cls is None:
        available = list(SCRAPER_REGISTRY.keys()) or ["none registered yet"]
        raise ValueError(
            f"No scraper registered for source='{source}'. "
            f"Available: {available}. "
            f"Phase 5 adds the Instagram implementation."
        )
    return cls
