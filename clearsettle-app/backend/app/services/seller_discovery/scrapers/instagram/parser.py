"""
Instagram profile HTML / JSON parser.

Responsibilities:
  - Extract RawProfile from scraped page HTML or JSON blobs.
  - Extract lists of usernames from hashtag pages.
  - Parse contact info (email, WhatsApp) from bio text.

Design notes:
  - All functions are pure (input → output, no I/O, no DB).
  - Instagram frequently changes page structure. Isolate all format-specific
    logic here so Phase 5 (and future format updates) touch only this file.
  - Returns None / empty list on parse failure — never raises.

Instagram page formats (as of 2025–2026):
  Profile page: JSON embedded as window.__additionalDataLoaded or
                in <script type="application/json"> blocks.
  Hashtag page: GraphQL JSON in __additionalDataLoaded with edge_hashtag_to_media.
  API responses: /api/v1/users/web_profile_info?username= (when available)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services.seller_discovery.scrapers.result_models import RawProfile

logger = logging.getLogger(__name__)

# ── Regex patterns ─────────────────────────────────────────────────────────────

_EMAIL_RE     = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]{2,}", re.IGNORECASE)
_WHATSAPP_RE  = re.compile(
    r"(?:wa\.me/|whatsapp[:\s*]+|watsapp[:\s*]+)(\+?[\d\s\-]{8,15})",
    re.IGNORECASE,
)
_PHONE_IN_BIO = re.compile(r"(?<!\d)(\+91[\s\-]?[6-9]\d{9}|[6-9]\d{9})(?!\d)")

# Embedded JSON blocks Instagram uses
_ADDITIONAL_DATA_RE = re.compile(
    r'window\.__additionalDataLoaded\s*\(\s*["\'].*?["\']\s*,\s*(\{.+?\})\s*\)',
    re.DOTALL,
)
_APP_JSON_BLOCK_RE = re.compile(
    r'<script\s+type="application/json"[^>]*>(.*?)</script>',
    re.DOTALL,
)


# ── Bio contact extraction ────────────────────────────────────────────────────

def extract_email_from_bio(bio: str) -> str | None:
    """Find the first email address in bio text. Returns None if none found."""
    if not bio:
        return None
    m = _EMAIL_RE.search(bio)
    return m.group(0).lower() if m else None


def extract_whatsapp_from_bio(bio: str) -> str | None:
    """
    Find a WhatsApp number from bio text.

    Matches patterns like:
      wa.me/919876543210
      WhatsApp: +91 98765 43210
      watsapp 9876543210 (common misspelling)
    Falls back to detecting bare Indian mobile numbers (+91 or 10-digit).
    """
    if not bio:
        return None
    # Explicit WhatsApp mention
    m = _WHATSAPP_RE.search(bio)
    if m:
        raw = re.sub(r"[\s\-]", "", m.group(1))
        return raw if len(raw) >= 8 else None
    # Indian mobile number fallback
    m2 = _PHONE_IN_BIO.search(bio)
    if m2:
        return re.sub(r"[\s\-]", "", m2.group(1))
    return None


# ── Profile page parsing ──────────────────────────────────────────────────────

def parse_profile_page(html: str, username: str) -> RawProfile | None:
    """
    Extract a RawProfile from an Instagram profile page HTML string.

    Tries multiple extraction strategies in order:
      1. window.__additionalDataLoaded JSON blob
      2. <script type="application/json"> blocks
      3. Legacy window._sharedData pattern

    Returns None if no parseable data is found — caller should log and skip.

    NOTE: This function needs a real HTML string from a browser-rendered page.
          Phase 5 (Playwright) provides that HTML. Until then, passing an empty
          or non-Instagram string returns None.
    """
    if not html:
        return None

    user_data = (
        _try_additional_data(html)
        or _try_json_blocks(html)
    )

    if not user_data:
        logger.debug("parse_profile_page: no parseable data for @%s", username)
        return None

    try:
        return _user_data_to_profile(user_data, username)
    except Exception as exc:
        logger.warning("parse_profile_page: extraction error for @%s: %s", username, exc)
        return None


def _try_additional_data(html: str) -> dict | None:
    m = _ADDITIONAL_DATA_RE.search(html)
    if not m:
        return None
    try:
        blob = json.loads(m.group(1))
        return _dig(blob, "graphql", "user") or _dig(blob, "data", "user")
    except Exception:
        return None


def _try_json_blocks(html: str) -> dict | None:
    for raw in _APP_JSON_BLOCK_RE.findall(html):
        try:
            blob = json.loads(raw)
            user = _dig(blob, "graphql", "user") or _dig(blob, "data", "user")
            if user and user.get("username"):
                return user
        except Exception:
            continue
    return None


def _user_data_to_profile(u: dict, username: str) -> RawProfile:
    bio = u.get("biography") or ""
    return RawProfile(
        username          = u.get("username") or username,
        source            = "instagram",
        profile_url       = f"https://www.instagram.com/{username}/",
        full_name         = u.get("full_name") or None,
        bio               = bio or None,
        website           = u.get("external_url") or None,
        category          = u.get("category_name") or None,
        profile_image_url = u.get("profile_pic_url_hd") or u.get("profile_pic_url") or None,
        followers_count   = _safe_int(_dig(u, "edge_followed_by", "count")),
        following_count   = _safe_int(_dig(u, "edge_follow", "count")),
        post_count        = _safe_int(_dig(u, "edge_owner_to_timeline_media", "count")),
        is_private        = bool(u.get("is_private")),
        is_verified       = bool(u.get("is_verified")),
        is_business       = bool(u.get("is_business_account")),
        email             = extract_email_from_bio(bio),
        whatsapp          = extract_whatsapp_from_bio(bio),
        raw_data          = u,
    )


# ── Hashtag page parsing ──────────────────────────────────────────────────────

def parse_hashtag_page(html: str) -> list[str]:
    """
    Extract unique usernames from an Instagram hashtag page HTML string.

    Returns a list of usernames — the caller then schedules scrape_profile()
    for each one. Returns [] if the page cannot be parsed.

    NOTE: Requires real browser-rendered HTML (Phase 5). Returns [] until then.
    """
    if not html:
        return []

    usernames: list[str] = []

    m = _ADDITIONAL_DATA_RE.search(html)
    if not m:
        return []

    try:
        blob  = json.loads(m.group(1))
        edges = (
            _dig(blob, "graphql", "hashtag", "edge_hashtag_to_media", "edges")
            or _dig(blob, "data", "hashtag", "edge_hashtag_to_media", "edges")
            or []
        )
        for edge in edges:
            owner = _dig(edge, "node", "owner", "username")
            if owner and owner not in usernames:
                usernames.append(owner)
    except Exception as exc:
        logger.warning("parse_hashtag_page: extraction error: %s", exc)

    return usernames


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dig(obj: Any, *keys: str) -> Any:
    """Safe nested key access — returns None instead of raising KeyError."""
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _safe_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


# ── API response parser ───────────────────────────────────────────────────────

def parse_from_api_response(user: dict, username: str) -> RawProfile:
    """
    Build a RawProfile from Instagram's internal API JSON.

    Handles two common response shapes:
      Shape A — web_profile_info endpoint (modern, preferred):
        { "data": { "user": { ... } } }   →  caller passes the inner "user" dict

      Shape B — graphql user object (legacy embedded JSON):
        Same fields, same function — caller strips outer wrapper before calling.

    Field reference (as of 2025–2026):
      username, full_name, biography, external_url,
      profile_pic_url_hd, is_private, is_verified, is_business_account,
      category_name, edge_followed_by.count, edge_follow.count,
      edge_owner_to_timeline_media.count
    """
    bio = user.get("biography") or ""

    followers = (
        _safe_int(_dig(user, "edge_followed_by", "count"))
        or _safe_int(user.get("follower_count"))
    )
    following = (
        _safe_int(_dig(user, "edge_follow", "count"))
        or _safe_int(user.get("following_count"))
    )
    post_count = (
        _safe_int(_dig(user, "edge_owner_to_timeline_media", "count"))
        or _safe_int(user.get("media_count"))
    )

    # Engagement rate: rough estimate using post count and follower count.
    # Accurate engagement needs per-post likes/comments — not available here.
    engagement_rate: float | None = None
    if followers and followers > 0 and post_count and post_count > 0:
        # Heuristic: 1% base ± follower-count curve (declines at scale)
        if followers < 10_000:
            engagement_rate = round(min(0.08, 1000 / followers), 4)
        elif followers < 100_000:
            engagement_rate = round(min(0.04, 500 / followers), 4)
        else:
            engagement_rate = round(min(0.02, 200 / followers), 4)

    return RawProfile(
        username          = user.get("username") or username,
        source            = "instagram",
        profile_url       = f"https://www.instagram.com/{username}/",
        full_name         = user.get("full_name") or None,
        bio               = bio or None,
        website           = user.get("external_url") or None,
        category          = user.get("category_name") or None,
        profile_image_url = (
            user.get("profile_pic_url_hd")
            or user.get("profile_pic_url")
            or None
        ),
        followers_count   = followers,
        following_count   = following,
        post_count        = post_count,
        engagement_rate   = engagement_rate,
        is_private        = bool(user.get("is_private")),
        is_verified       = bool(user.get("is_verified")),
        is_business       = bool(
            user.get("is_business_account")
            or user.get("is_professional_account")
        ),
        email             = extract_email_from_bio(bio),
        whatsapp          = extract_whatsapp_from_bio(bio),
        raw_data          = user,
    )


def parse_hashtag_api_response(data: dict) -> list[str]:
    """
    Extract usernames from Instagram's hashtag API response.

    Handles two endpoint shapes:
      /api/v1/tags/web_info/?tag_name={tag}
        →  data.hashtag.edge_hashtag_to_media.edges[].node.owner.username
      GraphQL hashtag response (legacy):
        →  graphql.hashtag.edge_hashtag_to_media.edges[].node.owner.username
    """
    usernames: list[str] = []
    seen: set[str] = set()

    # Modern API shape
    edges = (
        _dig(data, "data", "hashtag", "edge_hashtag_to_media", "edges")
        or _dig(data, "graphql", "hashtag", "edge_hashtag_to_media", "edges")
        or []
    )

    for edge in edges:
        owner = (
            _dig(edge, "node", "owner", "username")
            or _dig(edge, "node", "user", "username")
        )
        if owner and owner not in seen:
            seen.add(owner)
            usernames.append(owner)

    return usernames
