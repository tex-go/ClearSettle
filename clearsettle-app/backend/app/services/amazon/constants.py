"""
Amazon SP API constants.

Centralising these here means adding a new marketplace or adjusting a rate
limit is a one-file change.
"""

# ── LWA (Login with Amazon) ───────────────────────────────────────────────────

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

# ── SP API regional endpoints ─────────────────────────────────────────────────
# India (IN) belongs to the EU selling region.
SP_API_ENDPOINTS: dict[str, str] = {
    "na": "https://sellingpartnerapi-na.amazon.com",
    "eu": "https://sellingpartnerapi-eu.amazon.com",
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}

DEFAULT_REGION   = "eu"
DEFAULT_ENDPOINT = SP_API_ENDPOINTS[DEFAULT_REGION]

# ── Marketplace IDs ───────────────────────────────────────────────────────────
# Full reference: https://developer-docs.amazon.com/sp-api/docs/marketplace-ids

MARKETPLACE_IDS: dict[str, str] = {
    # India (EU region)
    "amazon.in":    "A21TJRUUN4KGV",
    # North America
    "amazon.com":   "ATVPDKIKX0DER",
    "amazon.ca":    "A2EUQ1WTGCTBG2",
    "amazon.com.mx":"A1AM78C64UM0Y8",
    # Europe
    "amazon.co.uk": "A1F83G8C2ARO7P",
    "amazon.de":    "A1PA6795UKMFR9",
    "amazon.fr":    "A13V1IB3VIYZZH",
    "amazon.it":    "APJ6JRA9NG5V4",
    "amazon.es":    "A1RKKUPIHCS9HS",
    # Far East
    "amazon.co.jp": "A1VC38T7YXB528",
    "amazon.com.au":"A39IBJ37TRP1C6",
}

DEFAULT_MARKETPLACE_ID = MARKETPLACE_IDS["amazon.in"]   # India

# ── SP API rate limits (requests/sec, burst) ──────────────────────────────────
# Used by the throttle-aware client to space requests.
# Source: https://developer-docs.amazon.com/sp-api/docs/usage-plans-and-rate-limits-in-the-sp-api

RATE_LIMITS: dict[str, dict] = {
    # Orders API
    "/orders/v0/orders":             {"rate": 0.0167, "burst": 20},
    "/orders/v0/orders/{orderId}":   {"rate": 0.5,    "burst": 30},

    # Finances API
    "/finances/v0/financialEventGroups": {"rate": 0.5, "burst": 30},
    "/finances/v0/financialEvents":      {"rate": 0.5, "burst": 30},

    # Reports API
    "/reports/2021-06-30/reports":       {"rate": 0.0167, "burst": 15},
    "/reports/2021-06-30/reports/{id}":  {"rate": 2.0,    "burst": 15},
    "/reports/2021-06-30/documents/{id}": {"rate": 0.0167, "burst": 15},

    # Catalog API
    "/catalog/2022-04-01/items":         {"rate": 2.0, "burst": 2},
    "/catalog/2022-04-01/items/{asin}":  {"rate": 2.0, "burst": 2},
}

# ── HTTP configuration ────────────────────────────────────────────────────────

DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRIES             = 3
RETRY_BACKOFF_BASE      = 1.0   # seconds; doubled on each attempt (1, 2, 4 …)
MAX_RETRY_DELAY         = 60.0  # cap per-attempt sleep at 60 s

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# ── Report types ──────────────────────────────────────────────────────────────

class ReportType:
    SETTLEMENT_V2_FLAT_FILE = "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE"
    SETTLEMENT_V2_XML       = "GET_V2_SETTLEMENT_REPORT_DATA_XML"
    FBA_INVENTORY           = "GET_AFN_INVENTORY_DATA"
    ORDERS_FLAT_FILE        = "GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL"
    MTR_B2B                 = "GET_B2B_GST_MTR_B2B_CUSTOM"
    MTR_B2C                 = "GET_B2B_GST_MTR_B2C_CUSTOM"
    GST_STOCK_TRANSFER      = "GET_GST_STR_ADHOC"


class ReportStatus:
    IN_QUEUE  = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    CANCELLED   = "CANCELLED"
    DONE        = "DONE"
    FATAL       = "FATAL"
    TERMINAL_STATUSES = {DONE, CANCELLED, FATAL}
