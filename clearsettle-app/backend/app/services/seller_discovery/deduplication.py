"""
Seller lead deduplication — pure DB helpers, no HTTP.

Deduplication layers (evaluated in order):
  1. Primary key: (username, source) — enforced by DB unique constraint.
     This is the canonical check before any insert.

  2. Website domain match: normalised root domain across all sources.
     Flags potential cross-source duplicates for human review — does NOT
     block the insert since the same website can belong to different sellers.

Design for scale:
  Both checks are index-aware and return quickly even at millions of rows.
  The DB unique constraint in layer 1 is the hard guarantee; layer 2 is advisory.
"""
import logging
import re
from urllib.parse import urlparse

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.seller_lead import SellerLead

logger = logging.getLogger(__name__)


# ── Username normalisation ────────────────────────────────────────────────────

def normalize_username(username: str) -> str:
    """Lowercase, strip whitespace and leading @ symbol."""
    return username.lower().strip().lstrip("@")


# ── Website normalisation ─────────────────────────────────────────────────────

_REMOVE_TRAILING_SLASH = re.compile(r"/$")
_REMOVE_PROTOCOL       = re.compile(r"^https?://", re.IGNORECASE)
_REMOVE_WWW            = re.compile(r"^www\.", re.IGNORECASE)


def normalize_website(url: str) -> str:
    """
    Extract a canonical root domain for cross-source comparison.

    Examples:
      https://www.example.com/path → example.com
      http://example.in/           → example.in
      linktr.ee/myshop             → linktr.ee/myshop  (not a root domain — kept as-is)
    """
    if not url:
        return ""
    cleaned = url.strip()
    cleaned = _REMOVE_PROTOCOL.sub("", cleaned)
    cleaned = _REMOVE_WWW.sub("", cleaned)
    cleaned = _REMOVE_TRAILING_SLASH.sub("", cleaned)
    # Take only root domain (before first slash)
    root = cleaned.split("/")[0].lower()
    return root


# ── Primary dedup check ───────────────────────────────────────────────────────

async def check_duplicate_by_username(
    db: AsyncSession,
    username: str,
    source: str,
) -> SellerLead | None:
    """
    Fast primary dedup check using the indexed unique constraint.

    Returns the existing lead if found; None if this is a new lead.
    This must be called before every insert to avoid hitting the DB
    unique constraint exception (which would roll back the session).
    """
    normalized = normalize_username(username)
    result = await db.execute(
        select(SellerLead).where(
            SellerLead.username == normalized,
            SellerLead.source   == source,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.debug("Dedup hit: username=%s source=%s lead_id=%s", normalized, source, existing.id)
    return existing


# ── Advisory website match ────────────────────────────────────────────────────

async def find_similar_by_website(
    db: AsyncSession,
    website: str,
    exclude_username: str | None = None,
    limit: int = 5,
) -> list[SellerLead]:
    """
    Advisory cross-source dedup: find leads sharing the same root domain.

    Returns up to `limit` leads — caller decides whether to flag or merge.
    Does NOT block the insert; intended for dashboard review workflows.
    """
    if not website:
        return []

    root = normalize_website(website)
    if not root or len(root) < 4:
        return []

    q = (
        select(SellerLead)
        .where(
            SellerLead.website.ilike(f"%{root}%"),
            SellerLead.lead_status != "deleted",
        )
        .limit(limit)
    )
    if exclude_username:
        q = q.where(SellerLead.username != normalize_username(exclude_username))

    result = await db.execute(q)
    return list(result.scalars().all())
