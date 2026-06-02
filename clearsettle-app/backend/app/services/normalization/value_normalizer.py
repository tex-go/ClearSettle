"""
Value Normalizer.

Normalizes individual cell values into canonical forms:
  - Dates → ISO 8601 string (YYYY-MM-DD)
  - Amounts → Decimal (sign-corrected for debits)
  - Order/settlement statuses → lowercase canonical enum strings
  - Fee type names → canonical lowercase string
  - Currency codes → ISO 4217 uppercase
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


# ── Date normalization ────────────────────────────────────────────────────────

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%b-%Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%d-%m-%y",
    "%d/%m/%y",
]


def normalize_date(value: Any) -> Optional[str]:
    """Return ISO date string 'YYYY-MM-DD' or None."""
    if value is None:
        return None
    from datetime import date as _date, datetime as _dt
    if isinstance(value, _dt):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, _date):
        return value.strftime("%Y-%m-%d")

    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "null", "n/a", "-"):
        return None

    # Try ISO first (fast path)
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]

    for fmt in _DATE_FORMATS:
        try:
            return _dt.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


# ── Amount normalization ──────────────────────────────────────────────────────

def normalize_amount(value: Any) -> Optional[Decimal]:
    """
    Parse a raw cell value to Decimal.
    Handles: "1,234.56", "(1234.56)", "-1234", "₹ 1234", "1234.56 INR".
    Returns None for blank/non-numeric values.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, Decimal):
        return value

    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "null", "n/a", "-", ""):
        return None

    # Strip currency symbols and labels
    s = re.sub(r"[₹$€£¥\s]", "", s)
    s = re.sub(r"[A-Z]{3}$", "", s)   # strip trailing INR, USD, etc.
    s = s.replace(",", "")            # remove thousand separators

    # Handle accounting negatives: (1234.56) → -1234.56
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]

    try:
        return Decimal(s)
    except InvalidOperation:
        return None


# ── Status normalization ──────────────────────────────────────────────────────

_ORDER_STATUS_MAP = {
    "delivered":   ["delivered", "dlv", "deliver", "completed", "complete", "done"],
    "returned":    ["returned", "return", "rto", "reverse", "reverted"],
    "cancelled":   ["cancelled", "canceled", "cancel", "cnl", "cnld"],
    "shipped":     ["shipped", "dispatched", "dispatch", "in transit", "intransit", "out for delivery"],
    "pending":     ["pending", "not yet dispatched", "awaiting", "unshipped", "processing"],
    "refunded":    ["refunded", "refund"],
}

_SETTLEMENT_STATUS_MAP = {
    "settled":     ["settled", "paid", "remitted", "credited", "transferred", "done"],
    "pending":     ["pending", "unsettled", "awaiting", "hold", "processing"],
    "failed":      ["failed", "failure", "rejected", "declined"],
}


def normalize_status(raw: Any, kind: str = "order") -> Optional[str]:
    """
    Normalize an order/settlement status string to a canonical value.
    kind: 'order' or 'settlement'
    """
    if raw is None:
        return None
    s = str(raw).lower().strip()
    if not s or s in ("nan", "none", "-"):
        return None

    mapping = _ORDER_STATUS_MAP if kind == "order" else _SETTLEMENT_STATUS_MAP
    for canonical, aliases in mapping.items():
        for alias in aliases:
            if alias in s:
                return canonical
    return s  # return as-is if no mapping found


# ── Fee type normalization ────────────────────────────────────────────────────

_FEE_TYPE_MAP = {
    "commission":         ["commission", "referral fee", "referral-fee", "platform commission", "platform fee"],
    "fixed_fee":          ["fixed fee", "closing fee", "pick and pack fee", "fulfillment fee",
                           "fba-per-unit-fulfillment-fee", "tech fee"],
    "shipping_fee":       ["shipping fee", "shipping charge", "shipping charges", "forward shipping charge",
                           "forward shipping fee"],
    "reverse_shipping":   ["reverse shipping fee", "reverse shipping charge", "return shipping fee",
                           "return shipping charge", "reverse logistics"],
    "collection_fee":     ["collection fee", "payment gateway fee", "cod fee", "payment collection fee"],
    "tcs":                ["tcs", "tax collected at source", "tcs igst", "tcs cgst", "tcs sgst"],
    "tds":                ["tds", "tds on commission", "tax deducted at source"],
    "gst_on_fees":        ["gst", "gst amount", "gst on fees", "igst", "cgst", "sgst"],
    "wallet_redeem":      ["wallet redeem", "wallet credit"],
    "safe_t_claim":       ["safe-t", "safe-t-reimbursement", "safet"],
    "reimbursement":      ["reimbursement", "warehouse damage", "disposal-fee"],
    "penalty":            ["penalty", "penalty amount", "seller penalty", "seller fine"],
    "other":              ["other fees", "other charges", "other deductions", "adjustments", "miscellaneous"],
}

_FEE_REVERSE: dict = {}
for canonical, aliases in _FEE_TYPE_MAP.items():
    for a in aliases:
        _FEE_REVERSE[a.lower()] = canonical
    _FEE_REVERSE[canonical] = canonical


def normalize_fee_type(raw: Any) -> str:
    if raw is None:
        return "other"
    s = str(raw).lower().strip()
    if s in _FEE_REVERSE:
        return _FEE_REVERSE[s]
    for alias, canonical in _FEE_REVERSE.items():
        if alias in s:
            return canonical
    return s or "other"


# ── Currency normalization ────────────────────────────────────────────────────

_CURRENCY_MAP = {
    "inr": "INR", "₹": "INR", "rs": "INR", "rs.": "INR", "rupee": "INR", "rupees": "INR",
    "usd": "USD", "$": "USD",
    "eur": "EUR", "€": "EUR",
    "gbp": "GBP", "£": "GBP",
}


def normalize_currency(raw: Any, default: str = "INR") -> str:
    if raw is None:
        return default
    s = str(raw).strip().lower()
    return _CURRENCY_MAP.get(s, s.upper() if s else default)
