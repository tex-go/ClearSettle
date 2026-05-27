"""
Amazon SP API — Orders API v0.

This module is intentionally minimal in Session 4.
Full order ingestion, deduplication, and DB storage are implemented in the
reconciliation session.  The function signatures and pagination pattern are
established here so the reconciliation layer can plug in without refactoring.

Rate limit:  GET /orders/v0/orders     → 0.0167 req/s, burst 20
             GET /orders/v0/orders/{id} → 0.5 req/s, burst 30
"""
import logging
from datetime import datetime, timedelta
from typing import Generator

from app.services.amazon.constants import DEFAULT_MARKETPLACE_ID
from app.services.amazon.sp_api_client import SPAPIClient

logger = logging.getLogger(__name__)

ORDERS_BASE = "/orders/v0"


def get_orders(
    client:         SPAPIClient,
    *,
    days_back:      int = 30,
    marketplace_id: str | None = None,
    order_statuses: list[str] | None = None,
    max_results_per_page: int = 100,
) -> list[dict]:
    """
    Fetch all orders created in the last *days_back* days.

    Handles pagination automatically.  Returns a flat list of order dicts.

    Args:
        client:              Authenticated SPAPIClient.
        days_back:           Number of days of history to fetch.
        marketplace_id:      Defaults to India marketplace.
        order_statuses:      Filter by statuses (e.g. ["Shipped", "Delivered"]).
                             Defaults to all statuses.
        max_results_per_page: Amazon maximum is 100.

    Returns:
        List of order dicts exactly as returned by the Orders API.
    """
    created_after = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_orders: list[dict] = []

    for page in _paginate_orders(
        client,
        created_after=created_after,
        marketplace_id=marketplace_id or DEFAULT_MARKETPLACE_ID,
        order_statuses=order_statuses,
        max_results_per_page=max_results_per_page,
    ):
        all_orders.extend(page)

    logger.info("Fetched %d orders (last %d days)", len(all_orders), days_back)
    return all_orders


def get_order(client: SPAPIClient, order_id: str) -> dict:
    """Fetch a single order by Amazon order ID (e.g. 405-XXXXXXX-XXXXXXX)."""
    data = client.get(f"{ORDERS_BASE}/orders/{order_id}")
    return data.get("payload", data)


def get_order_items(client: SPAPIClient, order_id: str) -> list[dict]:
    """Fetch line items for a single order."""
    all_items: list[dict] = []
    next_token: str | None = None

    while True:
        params: dict = {}
        if next_token:
            params["NextToken"] = next_token

        data       = client.get(f"{ORDERS_BASE}/orders/{order_id}/orderItems", params=params)
        payload    = data.get("payload", {})
        all_items.extend(payload.get("OrderItems", []))
        next_token = payload.get("NextToken")

        if not next_token:
            break

    return all_items


# ── Pagination helper ─────────────────────────────────────────────────────────

def _paginate_orders(
    client:           SPAPIClient,
    created_after:    str,
    marketplace_id:   str,
    order_statuses:   list[str] | None,
    max_results_per_page: int,
) -> Generator[list[dict], None, None]:
    """Yield successive pages of orders."""
    next_token: str | None = None

    while True:
        params: dict = {
            "MarketplaceIds":    marketplace_id,
            "CreatedAfter":      created_after,
            "MaxResultsPerPage": max_results_per_page,
        }
        if order_statuses:
            # SP API accepts comma-separated values
            params["OrderStatuses"] = ",".join(order_statuses)
        if next_token:
            params["NextToken"] = next_token

        data       = client.get(f"{ORDERS_BASE}/orders", params=params)
        payload    = data.get("payload", {})
        orders     = payload.get("Orders", [])
        next_token = payload.get("NextToken")

        yield orders

        if not next_token:
            break
