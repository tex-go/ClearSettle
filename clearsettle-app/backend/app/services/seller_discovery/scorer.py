"""
Lead Scoring Engine — Phase 8.

Pure Python — no external API calls, no DB queries.
Works on a SellerLead ORM instance and returns a numeric score.

Scoring model:
  Weighted multi-factor score 0–100.
  Penalty: fake accounts score 0.
  Bonus: AI confidence adds up to +5.

Priority tiers:
  hot  ≥ 70   — immediate outreach candidate
  warm ≥ 40   — worth nurturing
  cold ≥ 20   — save for later
  skip  < 20  — low-value, exclude from queues

Entry points:
  score_lead(lead)              → (score, priority, breakdown_dict)
  apply_score_to_lead(db, lead) → None  (persists + commits)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_ECOM_KW = {
    "shop", "store", "order", "cod", "delivery", "buy", "products",
    "collection", "wholesale", "manufacturer", "supplier", "brand",
    "fashion", "clothing", "jewellery", "jewelry", "footwear",
}
_MARKETPLACE_KW = {
    "amazon", "flipkart", "meesho", "myntra", "nykaa", "ajio",
    "snapdeal", "paytm mall", "jiomart",
}
_INDIA_KW = {
    "india", "🇮🇳", "pan india", "whatsapp", "gpay", "paytm", "upi",
    "rupee", "₹", "mumbai", "delhi", "bangalore", "tirupur", "surat",
    "chennai", "hyderabad", "kolkata", "jaipur", "ahmedabad", "pune",
}
_SHOPIFY_KW = {"myshopify", "shopify"}


def score_lead(lead) -> tuple[float, str, dict]:
    """
    Compute a 0-100 lead score.

    Returns (score: float, priority: str, breakdown: dict[str, float]).
    Thread-safe: reads only from the lead object, no DB I/O.
    """
    bio     = (lead.bio     or "").lower()
    website = (lead.website or "").lower()
    fc      = lead.followers_count or 0
    factors: dict[str, float] = {}

    # ── 1. Website (10 pts) ───────────────────────────────────────────────────
    factors["website_exists"] = 10.0 if lead.website else 0.0

    # ── 2. Ecommerce keywords in bio + website (15 pts) ──────────────────────
    matched = sum(1 for k in _ECOM_KW if k in bio or k in website)
    factors["ecommerce_keywords"] = min(15.0, matched * 2.5)

    # ── 3. Shopify detection (10 pts) ─────────────────────────────────────────
    factors["shopify_detected"] = 10.0 if any(k in website for k in _SHOPIFY_KW) else 0.0

    # ── 4. Marketplace keywords (10 pts) ──────────────────────────────────────
    has_mkt = any(k in bio or k in website for k in _MARKETPLACE_KW)
    factors["marketplace_keywords"] = 10.0 if has_mkt else 0.0

    # ── 5. Follower count sweet spot 1k–200k (10 pts) ────────────────────────
    if 1_000 <= fc <= 50_000:
        factors["follower_quality"] = 10.0
    elif 50_001 <= fc <= 200_000:
        factors["follower_quality"] = 8.0
    elif fc > 200_000:
        factors["follower_quality"] = 4.0  # likely celeb/brand, not SMB seller
    elif fc >= 200:
        factors["follower_quality"] = 5.0
    else:
        factors["follower_quality"] = 0.0

    # ── 6. Engagement rate (8 pts) ────────────────────────────────────────────
    er = float(lead.engagement_rate or 0)
    if er >= 0.04:
        factors["engagement_rate"] = 8.0
    elif er >= 0.02:
        factors["engagement_rate"] = 5.0
    elif er >= 0.005:
        factors["engagement_rate"] = 2.0
    else:
        factors["engagement_rate"] = 0.0

    # ── 7. India relevance (12 pts) ───────────────────────────────────────────
    if lead.ai_is_india_seller:
        factors["india_relevance"] = 12.0
    elif lead.country and "india" in lead.country.lower():
        factors["india_relevance"] = 12.0
    elif any(k in bio for k in _INDIA_KW):
        factors["india_relevance"] = 8.0
    else:
        factors["india_relevance"] = 0.0

    # ── 8. Bio quality (8 pts) ───────────────────────────────────────────────
    bio_len = len(lead.bio or "")
    if bio_len >= 100:
        factors["bio_quality"] = 8.0
    elif bio_len >= 50:
        factors["bio_quality"] = 5.0
    elif bio_len >= 15:
        factors["bio_quality"] = 2.0
    else:
        factors["bio_quality"] = 0.0

    # ── 9. Business legitimacy composite (7 pts) ─────────────────────────────
    legit = 0.0
    if lead.full_name and len(lead.full_name) > 2:
        legit += 2.5
    if lead.website:
        legit += 2.0
    if not lead.ai_is_fake_account:
        legit += 2.5
    factors["business_legitimacy"] = min(7.0, legit)

    # ── 10. Contact availability (10 pts) ────────────────────────────────────
    contact = 0.0
    if lead.email:
        contact += 5.0
    if lead.whatsapp:
        contact += 5.0
    factors["contact_available"] = min(10.0, contact)

    # ── AI confidence bonus (up to +5) ───────────────────────────────────────
    ai_bonus = float(lead.ai_confidence_score or 0) * 5.0

    # ── Fake account penalty ─────────────────────────────────────────────────
    if lead.ai_is_fake_account:
        factors = {k: 0.0 for k in factors}
        ai_bonus = 0.0

    raw = sum(factors.values()) + ai_bonus
    score = round(min(100.0, max(0.0, raw)), 2)

    if score >= 70:
        priority = "hot"
    elif score >= 40:
        priority = "warm"
    elif score >= 20:
        priority = "cold"
    else:
        priority = "skip"

    return score, priority, factors


async def apply_score_to_lead(db, lead) -> None:
    """
    Compute and persist the score to a SellerLead.

    Commits and refreshes `lead` in-place.
    Safe to call repeatedly — always overwrites previous score.
    """
    score, priority, breakdown = score_lead(lead)

    lead.lead_score           = score
    lead.priority_level       = priority
    lead.score_breakdown_json = json.dumps({k: round(v, 2) for k, v in breakdown.items()})
    lead.updated_at           = datetime.utcnow()

    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    logger.debug("Scored lead %s: %.1f (%s)", lead.id, score, priority)
