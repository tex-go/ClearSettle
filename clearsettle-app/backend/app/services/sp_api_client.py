"""
Backward-compatibility shim — all implementation has moved to app.services.amazon.*.

New code should import directly from the sub-modules:

    from app.services.amazon.auth import get_valid_access_token
    from app.services.amazon.sp_api_client import SPAPIClient
    from app.services.amazon.orders import get_orders
    from app.services.amazon.finances import get_financial_event_groups
    from app.services.amazon.reports import request_report, get_report_status
"""

from app.services.amazon.auth import (          # noqa: F401
    build_authorization_url,
    exchange_code_for_tokens,
    generate_oauth_state,
    get_valid_access_token,
    refresh_access_token,
)
from app.services.amazon.sp_api_client import SPAPIClient, SpApiError  # noqa: F401
from app.services.amazon.orders import get_orders
from app.services.amazon.finances import get_financial_event_groups
from app.services.amazon.constants import ReportType


def fetch_orders(connection, days_back: int = 30) -> list[dict]:
    """Backward-compat wrapper — prefer get_orders(SPAPIClient(conn), ...) in new code."""
    return get_orders(SPAPIClient(connection), days_back=days_back)


def fetch_financial_events(connection, days_back: int = 30) -> dict:
    """Backward-compat wrapper — prefer get_financial_event_groups(SPAPIClient(conn)) in new code."""
    groups = get_financial_event_groups(SPAPIClient(connection), days_back=days_back)
    return {"financial_event_groups": groups}


def request_settlement_report(connection) -> str:
    """Backward-compat wrapper."""
    from app.services.amazon.reports import request_report
    return request_report(SPAPIClient(connection), ReportType.SETTLEMENT_V2_FLAT_FILE)


def get_report_status(connection, report_id: str) -> dict:
    """Backward-compat wrapper."""
    from app.services.amazon.reports import get_report_status as _get
    return _get(SPAPIClient(connection), report_id)
