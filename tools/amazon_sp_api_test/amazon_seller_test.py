"""
amazon_seller_test.py — Test the Sellers API via getMarketplaceParticipations.

What this tests:
  GET /sellers/v1/marketplaceParticipations
    → Lists all marketplaces the seller participates in
    → Verifies OAuth + SigV4 signing works end-to-end
    → Shows participation status per marketplace

Run:
    python amazon_seller_test.py
"""

from __future__ import annotations

import sys
from typing import Any

from _sp_client import (
    SPAPIConfig,
    SPAPIClient,
    MARKETPLACE_NAMES,
    Printer,
)


# ─────────────────────────────────────────────────────────────────────────────
# Response parsing
# ─────────────────────────────────────────────────────────────────────────────

def _parse_participations(body: Any) -> list[dict]:
    """
    Parse the marketplaceParticipations response body.
    Returns a flat list of {marketplace_id, country, name, is_participating, ...}.
    """
    if not isinstance(body, dict):
        return []

    payload = body.get("payload", [])
    results = []
    for item in payload:
        marketplace = item.get("marketplace", {})
        participation = item.get("participation", {})
        mid = marketplace.get("id", "")
        results.append({
            "marketplace_id":    mid,
            "name":              marketplace.get("name", MARKETPLACE_NAMES.get(mid, "Unknown")),
            "country_code":      marketplace.get("countryCode", "?"),
            "default_currency":  marketplace.get("defaultCurrencyCode", "?"),
            "default_language":  marketplace.get("defaultLanguageCode", "?"),
            "is_participating":  participation.get("isParticipating", False),
            "has_suspended_listings": participation.get("hasSuspendedListings", False),
        })
    return results


def _participation_icon(p: dict) -> str:
    if not p["is_participating"]:
        return "⭕"
    if p["has_suspended_listings"]:
        return "⚠️ "
    return "✅"


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_marketplace_participations(client: SPAPIClient) -> list[dict]:
    """Call getMarketplaceParticipations and return parsed marketplace list."""
    Printer.section("GET /sellers/v1/marketplaceParticipations")

    resp = client.get("/sellers/v1/marketplaceParticipations")
    Printer.result(resp)

    if not resp.ok:
        if resp.status_code == 403:
            Printer.fail(
                "403 Forbidden",
                "The seller has not authorised this app or the SP-API app is in "
                "'Draft' state. Publish the app or use self-authorisation."
            )
        elif resp.status_code == 401:
            Printer.fail("401 Unauthorized", "Check LWA credentials and AWS SigV4 signing.")
        elif resp.status_code == 0:
            Printer.fail("Connection error", resp.error or "check SP_API_ENDPOINT")
        return []

    participations = _parse_participations(resp.body)
    return participations


def print_participations(participations: list[dict]) -> None:
    """Display marketplace participation table."""
    if not participations:
        Printer.warn("No marketplaces found", "verify the seller account has marketplace access")
        return

    Printer.section("Marketplace Participation")
    print(
        f"    {'ID':<20} {'Country':>8}  {'Currency':>8}  "
        f"{'Participating':>14}  {'Name'}"
    )
    print(f"    {'─'*20} {'─'*8}  {'─'*8}  {'─'*14}  {'─'*30}")

    for p in participations:
        icon = _participation_icon(p)
        suspended = "  [SUSPENDED LISTINGS]" if p["has_suspended_listings"] else ""
        print(
            f"    {p['marketplace_id']:<20} "
            f"{p['country_code']:>8}  "
            f"{p['default_currency']:>8}  "
            f"{'Yes' if p['is_participating'] else 'No':>14}  "
            f"{p['name']}{suspended}"
        )

    active = sum(1 for p in participations if p["is_participating"])
    suspended_count = sum(1 for p in participations if p["has_suspended_listings"])
    print()
    Printer.kv("Total marketplaces",    str(len(participations)))
    Printer.kv("Active participations", str(active))
    if suspended_count:
        Printer.kv("Suspended listings",   f"{suspended_count} marketplace(s)")


def test_india_marketplace(participations: list[dict]) -> bool:
    """Specifically check for India marketplace A21TJRUUN4KGV."""
    Printer.section("India Marketplace Check (A21TJRUUN4KGV)")

    india = next(
        (p for p in participations if p["marketplace_id"] == "A21TJRUUN4KGV"),
        None
    )
    if india is None:
        Printer.warn(
            "India marketplace not found",
            "The authorised seller may not have an Amazon India account. "
            "This is expected if using a different marketplace."
        )
        return True  # Not an error — just informational

    icon = _participation_icon(india)
    Printer.kv("Marketplace ID",   india["marketplace_id"])
    Printer.kv("Name",             india["name"])
    Printer.kv("Country",          india["country_code"])
    Printer.kv("Currency",         india["default_currency"])
    Printer.kv("Participating",    "Yes" if india["is_participating"] else "No")

    if india["is_participating"]:
        Printer.ok("India marketplace active")
        if india["has_suspended_listings"]:
            Printer.warn(
                "Suspended listings detected",
                "Some listings are suspended — check Seller Central."
            )
        return True
    else:
        Printer.warn(
            "Not participating in India",
            "Seller is registered but not actively selling on Amazon India."
        )
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    Printer.header("ClearSettle  Amazon SP-API — Seller API Test")

    try:
        config = SPAPIConfig.from_env()
    except EnvironmentError as e:
        Printer.fail("Environment", str(e))
        Printer.footer("Fix .env and re-run.")
        return 1

    client = SPAPIClient(config)

    participations = test_marketplace_participations(client)

    if not participations:
        Printer.footer("Seller API test FAILED — could not retrieve marketplaces.")
        return 1

    print_participations(participations)
    test_india_marketplace(participations)

    Printer.divider()
    Printer.footer(
        f"Seller API test PASSED — "
        f"{sum(1 for p in participations if p['is_participating'])} "
        f"active marketplace(s) found."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
