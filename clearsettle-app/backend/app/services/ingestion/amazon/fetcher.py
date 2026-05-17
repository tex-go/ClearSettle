"""
Amazon settlement data fetcher — raw API layer.

Returns raw dicts exactly as the SP API delivers them.
No transformation; all normalisation happens in parser.py.
"""
import logging

from app.services.amazon.finances import get_financial_event_groups, get_financial_events_by_group
from app.services.amazon.sp_api_client import SPAPIClient

logger = logging.getLogger(__name__)


def fetch_settlement_groups(client: SPAPIClient, *, days_back: int = 30) -> list[dict]:
    """
    Fetch financial event groups (settlement periods) for the last N days.

    Returns raw API dicts.  Each dict is one Amazon settlement period
    (FinancialEventGroup).
    """
    groups = get_financial_event_groups(client, days_back=days_back)
    logger.info("Fetched %d settlement groups (last %d days)", len(groups), days_back)
    return groups


def fetch_events_for_group(client: SPAPIClient, group_id: str) -> dict:
    """
    Fetch all individual financial events for one settlement group.

    Returns raw API FinancialEvents dict with keys:
      ShipmentEventList, RefundEventList, ServiceFeeEventList,
      AdjustmentEventList, GuaranteeClaimEventList,
      ProductAdsPaymentEventList, etc.
    """
    events = get_financial_events_by_group(client, group_id)
    total = sum(len(v) for v in events.values() if isinstance(v, list))
    logger.debug("Fetched %d events for group %s", total, group_id)
    return events
