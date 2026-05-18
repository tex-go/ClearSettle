"""
Scraper result data models.

RawProfile  — structured data from one scraped public profile.
ScrapeResult — output of a single scrape() call (may contain many profiles).

These are pure dataclasses — no DB or HTTP dependencies.
They form the contract between scrapers and the orchestrator.

The orchestrator maps RawProfile → SellerLead (DB model) via lead_store.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawProfile:
    """
    Normalised representation of one scraped public profile.

    Scrapers produce these; the orchestrator persists them.
    All fields except username and source are optional because
    platform availability varies and profile visibility changes.
    """
    username:          str
    source:            str             # "instagram" | "linkedin" | …

    profile_url:       str | None = None
    full_name:         str | None = None
    bio:               str | None = None
    website:           str | None = None
    category:          str | None = None
    profile_image_url: str | None = None

    followers_count:   int | None = None
    following_count:   int | None = None
    post_count:        int | None = None
    engagement_rate:   float | None = None  # estimated; 0.0 – 1.0

    # Contact — only public, scraped from bio or link-in-bio pages
    email:    str | None = None
    whatsapp: str | None = None

    country:  str | None = None
    language: str | None = None

    # Instagram-specific metadata
    is_private:  bool = False
    is_verified: bool = False
    is_business: bool = False

    # Discovery provenance — set by the strategy, not the parser
    discovery_source:  str | None = None   # "hashtag" | "competitor_followers" | "direct"
    discovery_keyword: str | None = None   # e.g. "#ethnicwear"

    scraped_at: datetime = field(default_factory=datetime.utcnow)

    # Raw response preserved for debugging / re-parsing without a re-scrape
    raw_data: dict = field(default_factory=dict)

    def to_lead_dict(self) -> dict:
        """Map to the dict format expected by lead_store.create_or_update_lead()."""
        return {
            "username":          self.username,
            "source":            self.source,
            "profile_url":       self.profile_url,
            "full_name":         self.full_name,
            "bio":               self.bio,
            "website":           self.website,
            "category":          self.category,
            "profile_image_url": self.profile_image_url,
            "followers_count":   self.followers_count,
            "following_count":   self.following_count,
            "engagement_rate":   self.engagement_rate,
            "email":             self.email,
            "whatsapp":          self.whatsapp,
            "country":           self.country,
            "language":          self.language,
            "discovery_source":  self.discovery_source,
            "discovery_keyword": self.discovery_keyword,
        }


@dataclass
class ScrapeResult:
    """
    Output of one AbstractScraper.scrape() call.

    profiles      — list of RawProfile objects successfully collected
    error         — error string if the run was aborted; None on success
    reached_limit — True if max_results cap was hit (more data available)
    total_found   — total profiles seen (may exceed len(profiles) if capped)
    """
    profiles:      list[RawProfile] = field(default_factory=list)
    error:         str | None = None
    reached_limit: bool = False
    total_found:   int  = 0

    @property
    def succeeded(self) -> bool:
        return self.error is None

    @property
    def profile_count(self) -> int:
        return len(self.profiles)
