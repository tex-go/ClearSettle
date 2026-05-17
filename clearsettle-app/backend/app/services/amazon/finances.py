"""
Amazon SP API — Finances API v0.

Covers financial event groups (settlement periods) and individual financial
events (charges, refunds, service fees, etc.).

This module is intentionally minimal in Session 4.
Full reconciliation parsing is implemented in a future session.

Rate limit: 0.5 req/s, burst 30 for both endpoints.
"""
import logging
from datetime import datetime, timedelta
from typing import Generator

from app.services.amazon.sp_api_client import SPAPIClient

logger = logging.getLogger(__name__)

FINANCES_BASE = "/finances/v0"


# ── Financial event groups (settlement periods) ───────────────────────────────

def get_financial_event_groups(
    client:     SPAPIClient,
    *,
    days_back:  int = 30,
    max_results: int = 100,
) -> list[dict]:
    """
    Fetch financial event groups (settlement periods) posted in the last
    *days_back* days.

    Each group represents one Amazon settlement and contains:
      - FinancialEventGroupId
      - ProcessingStatus (Open | Closed)
      - FundTransferDate, FundTransferAmount
      - OriginalTotal, ConvertedTotal
      - AccountTail (last 4 of bank account)

    Returns a flat list of group dicts.
    """
    posted_after = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_groups: list[dict] = []

    for page in _paginate_event_groups(client, posted_after=posted_after, max_results=max_results):
        all_groups.extend(page)

    logger.info("Fetched %d financial event groups (last %d days)", len(all_groups), days_back)
    return all_groups


def get_financial_events_by_group(
    client:   SPAPIClient,
    group_id: str,
) -> dict:
    """
    Fetch all individual financial events for one settlement group.

    Returns the raw payload dict which contains sub-keys:
      ShipmentEventList, RefundEventList, GuaranteeClaimEventList,
      ServiceFeeEventList, ProductAdsPaymentEventList, etc.

    Full parsing into DB rows is reserved for the reconciliation session.
    """
    all_events: dict = {}
    next_token: str | None = None

    while True:
        params: dict = {"FinancialEventGroupId": group_id}
        if next_token:
            params["NextToken"] = next_token

        data    = client.get(f"{FINANCES_BASE}/financialEvents", params=params)
        payload = data.get("payload", {}).get("FinancialEvents", {})

        # Merge list keys across pages
        for key, value in payload.items():
            if isinstance(value, list):
                all_events.setdefault(key, []).extend(value)
            else:
                all_events[key] = value

        next_token = data.get("payload", {}).get("NextToken")
        if not next_token:
            break

    return all_events


def get_financial_events_by_order(
    client:   SPAPIClient,
    order_id: str,
) -> dict:
    """Fetch financial events for a specific order ID."""
    data = client.get(
        f"{FINANCES_BASE}/financialEvents",
        params={"AmazonOrderId": order_id},
    )
    return data.get("payload", {}).get("FinancialEvents", {})


# ── Pagination helpers ────────────────────────────────────────────────────────

def _paginate_event_groups(
    client:       SPAPIClient,
    posted_after: str,
    max_results:  int,
) -> Generator[list[dict], None, None]:
    next_token: str | None = None

    while True:
        params: dict = {"PostedAfter": posted_after, "MaxResultsPerPage": max_results}
        if next_token:
            params["NextToken"] = next_token

        data       = client.get(f"{FINANCES_BASE}/financialEventGroups", params=params)
        payload    = data.get("payload", {})
        groups     = payload.get("FinancialEventGroupList", [])
        next_token = payload.get("NextToken")

        yield groups

        if not next_token:
            break
