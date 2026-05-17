"""
Amazon SP API services package.

Modules
-------
constants      → Marketplace IDs, endpoints, rate limits, report types
auth           → LWA OAuth flow (token exchange, refresh, valid-token helper)
sp_api_client  → SPAPIClient (retry-safe, throttle-aware HTTP wrapper)
               → SpApiError hierarchy (RateLimitError, AuthError, TransientError …)
reports        → Reports API v2021-06-30 (request, poll, download)
orders         → Orders API v0 (list orders, order items)
finances       → Finances API v0 (settlement groups, financial events)

Quick-import surface
--------------------
Most callers only need a subset of symbols.  Import directly from the relevant
sub-module to keep dependency graphs clean.

Example:

    from app.services.amazon.auth import get_valid_access_token
    from app.services.amazon.sp_api_client import SPAPIClient
    from app.services.amazon.orders import get_orders
"""
