"""
AI Lead Classifier — Phase 7.

Uses Anthropic Claude Haiku to classify seller leads.

Cost protection:
  - Skips leads with no meaningful profile data.
  - Callers cap the number of leads classified per job (default 10).

Retry policy:
  - Up to 3 attempts on RateLimitError with exponential back-off.
  - JSONDecodeError returns a fallback result (no retry) so a bad response
    never blocks the pipeline.

Entry points:
  classify_lead(lead)                      → dict | None
  apply_classification_to_lead(db, lead)   → bool  (persists result)
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import anthropic

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 600

_VALID_CATEGORIES = {"d2c", "marketplace", "shopify", "instagram_shop", "reseller", "brand", "unknown"}
_VALID_BIZ_TYPES  = {"fashion", "electronics", "food", "beauty", "home", "toys", "sports", "jewelry", "other"}
_VALID_STAGES     = {"seed", "growth", "scale", "unknown"}

_PROMPT = """\
You are classifying an Instagram business account for a B2B sales CRM that helps Indian ecommerce sellers manage reconciliation on Amazon, Flipkart, and Meesho.

Profile:
Username: {username}
Full Name: {full_name}
Bio: {bio}
Website: {website}
Followers: {followers}
Following: {following}
Engagement Rate: {engagement_pct}
Category: {category}

Respond with ONLY a JSON object — no markdown fences, no explanation:
{{
  "is_ecommerce": <true if they sell physical products online>,
  "is_india_seller": <true if India-based>,
  "is_fake_account": <true if spam/bot/celebrity with irrelevant content>,
  "category": "<d2c|marketplace|shopify|instagram_shop|reseller|brand|unknown>",
  "estimated_biz_type": "<fashion|electronics|food|beauty|home|toys|sports|jewelry|other>",
  "revenue_stage": "<seed|growth|scale|unknown>",
  "relevance_score": <0.0-1.0 — how valuable for Amazon/Flipkart seller services>,
  "confidence_score": <0.0-1.0>,
  "tags": [<up to 5 short descriptive tags>],
  "outreach_suggestion": "<one-sentence personalized opener for a sales rep>"
}}

Relevance scoring guide:
  1.0 = active D2C brand selling on Indian marketplaces, 5k-200k followers
  0.7 = likely ecommerce seller, some marketplace signals
  0.4 = possible seller, unclear signals
  0.1 = celebrity/influencer/non-seller
  0.0 = fake, spam, or completely irrelevant"""


async def classify_lead(lead) -> dict | None:
    """
    Classify a SellerLead using Claude.

    Returns a classification dict or None if classification should be skipped
    (no API key, insufficient data, or unrecoverable error).
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.debug("No ANTHROPIC_API_KEY — skipping classification for %s", lead.username)
        return None

    bio = lead.bio or ""
    if len(bio) < 5 and not lead.website and not lead.full_name:
        logger.debug("Skipping %s — insufficient profile data", lead.username)
        return None

    prompt = _PROMPT.format(
        username=lead.username,
        full_name=lead.full_name or "",
        bio=bio[:500],
        website=lead.website or "",
        followers=lead.followers_count or 0,
        following=lead.following_count or 0,
        engagement_pct=f"{float(lead.engagement_rate or 0):.2%}",
        category=lead.category or "",
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    for attempt in range(3):
        try:
            response = await client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown fences if model wraps in ```json … ```
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) >= 2 else raw

            result = json.loads(raw)
            _coerce(result)
            logger.info(
                "Classified %s: ecom=%s india=%s score=%.2f conf=%.2f",
                lead.username,
                result["is_ecommerce"],
                result["is_india_seller"],
                result["relevance_score"],
                result["confidence_score"],
            )
            return result

        except anthropic.RateLimitError:
            wait = 2 ** attempt
            logger.warning("Rate-limited classifying %s (attempt %d) — sleeping %ds", lead.username, attempt + 1, wait)
            await asyncio.sleep(wait)

        except json.JSONDecodeError as exc:
            logger.warning("Bad JSON from classifier for %s: %s", lead.username, exc)
            return _fallback()

        except anthropic.APIStatusError as exc:
            logger.error("Anthropic API error for %s: %s %s", lead.username, exc.status_code, exc.message)
            return None

        except Exception as exc:
            logger.exception("Unexpected classifier error for %s: %s", lead.username, exc)
            return None

    return None


def _coerce(r: dict) -> None:
    """Validate and coerce all fields in-place so bad AI output never propagates."""
    r["is_ecommerce"]    = bool(r.get("is_ecommerce", False))
    r["is_india_seller"] = bool(r.get("is_india_seller", False))
    r["is_fake_account"] = bool(r.get("is_fake_account", False))

    r["relevance_score"]  = max(0.0, min(1.0, float(r.get("relevance_score", 0.5))))
    r["confidence_score"] = max(0.0, min(1.0, float(r.get("confidence_score", 0.5))))

    if r.get("category") not in _VALID_CATEGORIES:
        r["category"] = "unknown"
    if r.get("estimated_biz_type") not in _VALID_BIZ_TYPES:
        r["estimated_biz_type"] = "other"
    if r.get("revenue_stage") not in _VALID_STAGES:
        r["revenue_stage"] = "unknown"

    tags = r.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    r["tags"] = [str(t)[:50] for t in tags[:5]]
    r["outreach_suggestion"] = str(r.get("outreach_suggestion", ""))[:500]


def _fallback() -> dict:
    return {
        "is_ecommerce": False,
        "is_india_seller": False,
        "is_fake_account": False,
        "category": "unknown",
        "estimated_biz_type": "other",
        "revenue_stage": "unknown",
        "relevance_score": 0.1,
        "confidence_score": 0.1,
        "tags": [],
        "outreach_suggestion": "",
    }


async def apply_classification_to_lead(db, lead) -> bool:
    """
    Run classify_lead() and persist the result to seller_leads.

    Returns True if classification was applied, False otherwise.
    Commits and refreshes `lead` in-place.
    """
    result = await classify_lead(lead)
    if not result:
        return False

    lead.ai_is_ecommerce        = result["is_ecommerce"]
    lead.ai_is_india_seller     = result["is_india_seller"]
    lead.ai_is_fake_account     = result["is_fake_account"]
    lead.ai_category            = result["category"]
    lead.ai_estimated_biz_type  = result["estimated_biz_type"]
    lead.ai_revenue_stage       = result["revenue_stage"]
    lead.ai_relevance_score     = result["relevance_score"]
    lead.ai_confidence_score    = result["confidence_score"]
    lead.ai_tags_json           = json.dumps(result["tags"])
    lead.ai_outreach_suggestion = result["outreach_suggestion"]
    lead.ai_classified_at       = datetime.utcnow()
    lead.updated_at             = datetime.utcnow()

    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return True
