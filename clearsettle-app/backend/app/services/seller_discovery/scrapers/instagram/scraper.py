"""
Instagram Playwright scraper — Phase 5 implementation.

Architecture:
  - Async context manager: browser launched on __aenter__, closed on __aexit__
  - Single Chromium browser + one persistent BrowserContext per job run
  - New Page per request; closed after use (prevents state bleed between profiles)
  - playwright-stealth applied per-page to defeat bot detection fingerprinting
  - Response interception preferred over HTML parsing (more stable vs. DOM changes)
  - Polite delay + jitter between every request (AbstractScraper._polite_delay)

Detection avoidance (layered):
  1. playwright-stealth — patches navigator, webdriver, plugins, languages, hardware
  2. Randomised viewport dimensions per session
  3. Realistic User-Agent (Chrome 124 on Linux)
  4. Randomised delay 2–5 s between requests (from ScraperConfig)
  5. Proxy support: HTTP or SOCKS5 via config.proxy_url
  6. Cookie/storage persistence via config.session_data_json

Session persistence:
  Call save_session() to get a JSON string of cookies + localStorage.
  Store it in ScraperConfig.session_data_json for the next run.
  This preserves login state (if logged in) and reduces challenge frequency.

Error classification:
  _BLOCK_SIGNALS — patterns in page URL or title that indicate rate-limiting or
  challenge pages. scrape_profile() raises ScraperBlockedError on these so the
  orchestrator can back off or rotate proxy.

Compliance:
  - Only public profiles are scraped (private → returns None)
  - No mass-follow, no DM, no interaction — read-only
  - Request rate governed by rate limiter (default 0.5 req/s)

Registration:
  Calls register_scraper("instagram", InstagramScraper) on module import so
  get_scraper_class("instagram") works without explicit import at call sites.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any

from app.services.seller_discovery.scrapers.base import (
    AbstractScraper,
    ScraperConfig,
    register_scraper,
)
from app.services.seller_discovery.scrapers.instagram import parser
from app.services.seller_discovery.scrapers.rate_limiter import make_rate_limiter
from app.services.seller_discovery.scrapers.result_models import RawProfile, ScrapeResult

logger = logging.getLogger(__name__)

# Instagram URL patterns
_IG_BASE          = "https://www.instagram.com"
_PROFILE_INFO_URL = "/api/v1/users/web_profile_info/"
_HASHTAG_INFO_URL = "/api/v1/tags/web_info/"
_GRAPHQL_URL      = "/graphql/query"

# Response URL substrings that indicate the account is being challenged / blocked
_BLOCK_SIGNALS = (
    "challenge",
    "accounts/login",
    "checkpoint",
    "sorry",
)

# How long to wait after navigating before reading intercepted responses
_NAV_SETTLE_MS = 2500


class ScraperBlockedError(Exception):
    """Raised when Instagram returns a challenge / rate-limit page."""


class InstagramScraper(AbstractScraper):
    """
    Playwright-based Instagram scraper.

    Lifecycle:
        async with InstagramScraper(config) as scraper:
            result = await scraper.scrape("#ethnicwear", strategy="hashtag")
    """

    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        self._playwright     = None
        self._browser        = None
        self._context        = None
        self._stealth_fn     = None    # async fn(page) from playwright-stealth
        self._browser_ready  = False

    # ── Context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "InstagramScraper":
        await self._launch_browser()
        return self

    async def __aexit__(self, *args) -> None:
        if not self._closed:
            await self.close()
            self._closed = True

    # ── Browser lifecycle ─────────────────────────────────────────────────────

    async def _launch_browser(self) -> None:
        if self._browser_ready:
            return

        from playwright.async_api import async_playwright

        # Stealth — optional; log warning if not installed
        try:
            from playwright_stealth import stealth_async
            self._stealth_fn = stealth_async
            logger.debug("playwright-stealth loaded")
        except ImportError:
            self._stealth_fn = None
            logger.warning(
                "playwright-stealth not installed — bot detection risk elevated. "
                "Add playwright-stealth to requirements.txt."
            )

        self._playwright = await async_playwright().start()

        launch_args = {
            "headless": self.config.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-extensions",
            ],
        }
        if self.config.proxy_url:
            launch_args["proxy"] = {"server": self.config.proxy_url}

        self._browser = await self._playwright.chromium.launch(**launch_args)

        # Randomise viewport per session to vary fingerprint
        viewport = {
            "width":  random.randint(1280, 1920),
            "height": random.randint(768,  1080),
        }
        context_args: dict[str, Any] = {
            "viewport":    viewport,
            "user_agent":  self.config.user_agent,
            "locale":      "en-US",
            "timezone_id": "Asia/Kolkata",
            "java_script_enabled": True,
        }
        if self.config.proxy_url:
            context_args["proxy"] = {"server": self.config.proxy_url}

        self._context = await self._browser.new_context(**context_args)

        # Restore persisted session (cookies + localStorage)
        if self.config.session_data_json:
            await self._restore_session(self.config.session_data_json)

        self._browser_ready = True
        logger.info(
            "InstagramScraper: browser ready (headless=%s proxy=%s)",
            self.config.headless, bool(self.config.proxy_url),
        )

    async def _restore_session(self, session_json: str) -> None:
        try:
            data = json.loads(session_json)
            cookies = data.get("cookies", [])
            if cookies:
                await self._context.add_cookies(cookies)
            logger.debug("Session restored: %d cookies", len(cookies))
        except Exception as exc:
            logger.warning("Failed to restore session: %s", exc)

    async def save_session(self) -> str:
        """
        Serialise current cookies to JSON.
        Store the result in ScraperConfig.session_data_json for the next run.
        """
        if not self._context:
            return "{}"
        cookies = await self._context.cookies()
        return json.dumps({"cookies": cookies})

    async def close(self) -> None:
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._browser = None
        self._context = None
        self._playwright = None
        self._browser_ready = False
        logger.debug("InstagramScraper: browser closed")

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape(self, target: str, strategy: str) -> ScrapeResult:
        """
        Dispatch to the appropriate discovery strategy.

        strategy = "hashtag"            → HashtagDiscoveryStrategy
        strategy = "competitor_followers" → CompetitorFollowerStrategy
        strategy = "direct"             → single profile scrape
        """
        await self._launch_browser()

        from app.core.config import get_settings
        settings     = get_settings()
        rate_limiter = make_rate_limiter(rate_rps=settings.discovery_rate_limit_rps)

        if strategy == self.STRATEGY_HASHTAG:
            from app.services.seller_discovery.scrapers.instagram.hashtag import (
                HashtagDiscoveryStrategy,
            )
            strat = HashtagDiscoveryStrategy(self, rate_limiter)
            return await strat.run(target, max_profiles=self.config.max_results)

        elif strategy == self.STRATEGY_COMPETITOR:
            from app.services.seller_discovery.scrapers.instagram.hashtag import (
                CompetitorFollowerStrategy,
            )
            strat = CompetitorFollowerStrategy(self, rate_limiter)
            return await strat.run(
                target.lstrip("@"), max_profiles=self.config.max_results
            )

        elif strategy == self.STRATEGY_DIRECT:
            profile = await self.scrape_profile(target.lstrip("@"))
            return ScrapeResult(
                profiles    = [profile] if profile else [],
                total_found = 1,
            )

        else:
            return ScrapeResult(error=f"Unknown strategy: {strategy!r}")

    async def scrape_profile(self, username: str) -> RawProfile | None:
        """
        Scrape a single public Instagram profile.

        Strategy:
          1. Open a new page, apply stealth.
          2. Register a response listener for the web_profile_info API call.
          3. Navigate to the profile page.
          4. Wait for the API response to arrive (or timeout after 8 s).
          5. Parse the intercepted JSON → RawProfile.
          6. Fallback: parse embedded JSON from page HTML.
          7. Return None for private, deleted, or unparseable profiles.
        """
        await self._launch_browser()

        page           = await self._context.new_page()
        captured_json: dict = {}

        async def on_response(response) -> None:
            try:
                url = response.url
                if _PROFILE_INFO_URL in url or (
                    _GRAPHQL_URL in url and "userInfo" in url
                ):
                    body = await response.json()
                    captured_json.update(body)
            except Exception:
                pass

        page.on("response", on_response)

        if self._stealth_fn:
            await self._stealth_fn(page)

        profile: RawProfile | None = None
        try:
            url      = f"{_IG_BASE}/{username}/"
            response = await page.goto(
                url,
                wait_until = "domcontentloaded",
                timeout    = 30_000,
            )

            # Detect login/challenge redirect
            final_url = page.url
            if any(sig in final_url for sig in _BLOCK_SIGNALS):
                logger.warning(
                    "scrape_profile: block detected for @%s — final_url=%s",
                    username, final_url,
                )
                raise ScraperBlockedError(f"Instagram blocked request for @{username}")

            if response and response.status == 404:
                logger.debug("scrape_profile: @%s not found (404)", username)
                return None

            # Wait for the async API call to complete
            await page.wait_for_timeout(_NAV_SETTLE_MS)

            # Try captured API response first (most reliable)
            if captured_json:
                user = (
                    captured_json.get("data", {}).get("user")
                    or captured_json.get("graphql", {}).get("user")
                )
                if user:
                    profile = parser.parse_from_api_response(user, username)

            # Fallback: embedded JSON in page HTML
            if profile is None:
                html    = await page.content()
                profile = parser.parse_profile_page(html, username)

            if profile is None:
                logger.debug("scrape_profile: could not parse @%s", username)
                return None

            if profile.is_private:
                logger.debug("scrape_profile: @%s is private — skipping", username)
                return None

            logger.debug(
                "scrape_profile: @%s scraped — followers=%s is_business=%s",
                username, profile.followers_count, profile.is_business,
            )
            return profile

        except ScraperBlockedError:
            raise
        except asyncio.TimeoutError:
            logger.warning("scrape_profile: timeout for @%s", username)
            return None
        except Exception as exc:
            logger.warning("scrape_profile: error for @%s — %s", username, exc)
            return None
        finally:
            try:
                await page.close()
            except Exception:
                pass
            await self._polite_delay()

    async def scrape_hashtag_page(self, tag: str, page: int = 0) -> list[str]:
        """
        Extract post-author usernames from an Instagram hashtag page.

        page=0  → top posts section (most relevant for discovery)
        page>0  → scrolled deeper into recent posts

        Strategy:
          1. Navigate to /explore/tags/{tag}/
          2. Intercept the hashtag API response.
          3. Scroll the page (page * 3 viewport heights) to trigger more loads.
          4. Parse intercepted JSON → list of usernames.
          5. Fallback to HTML parser if no API response captured.
        """
        await self._launch_browser()

        browser_page   = await self._context.new_page()
        captured_json: dict = {}

        async def on_response(response) -> None:
            try:
                url = response.url
                if _HASHTAG_INFO_URL in url or (
                    _GRAPHQL_URL in url and "FeedTopicPageContentQuery" in url
                ):
                    body = await response.json()
                    captured_json.update(body)
            except Exception:
                pass

        browser_page.on("response", on_response)

        if self._stealth_fn:
            await self._stealth_fn(browser_page)

        usernames: list[str] = []
        try:
            url = f"{_IG_BASE}/explore/tags/{tag}/"
            await browser_page.goto(
                url,
                wait_until = "domcontentloaded",
                timeout    = 30_000,
            )

            final_url = browser_page.url
            if any(sig in final_url for sig in _BLOCK_SIGNALS):
                logger.warning("scrape_hashtag_page: block detected for #%s", tag)
                raise ScraperBlockedError(f"Instagram blocked hashtag request for #{tag}")

            # Scroll to load additional posts on subsequent pages
            scroll_count = page * 3
            for _ in range(scroll_count):
                await browser_page.evaluate(
                    "window.scrollBy(0, window.innerHeight * 0.8)"
                )
                await browser_page.wait_for_timeout(
                    random.randint(800, 1400)
                )

            await browser_page.wait_for_timeout(_NAV_SETTLE_MS)

            # Parse intercepted API response (preferred)
            if captured_json:
                usernames = parser.parse_hashtag_api_response(captured_json)

            # Fallback: HTML parser
            if not usernames:
                html      = await browser_page.content()
                usernames = parser.parse_hashtag_page(html)

            logger.debug(
                "scrape_hashtag_page: #%s page=%d → %d usernames",
                tag, page, len(usernames),
            )

        except ScraperBlockedError:
            raise
        except asyncio.TimeoutError:
            logger.warning("scrape_hashtag_page: timeout for #%s page=%d", tag, page)
        except Exception as exc:
            logger.warning(
                "scrape_hashtag_page: error for #%s page=%d — %s", tag, page, exc
            )
        finally:
            try:
                await browser_page.close()
            except Exception:
                pass
            await self._polite_delay()

        return usernames


# ── Auto-register ─────────────────────────────────────────────────────────────

register_scraper("instagram", InstagramScraper)
logger.debug("InstagramScraper registered (Phase 5 — Playwright)")
