from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s or s.lower() in ("none", "nan", "nat"):
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Last resort: strip time component if present
    if " " in s:
        return parse_date(s.split(" ")[0])
    return None


def parse_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    cleaned = str(value).replace(",", "").replace("₹", "").strip()
    if not cleaned or cleaned.lower() in ("none", "nan", "-", ""):
        return Decimal("0")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def parse_optional_decimal(value) -> Decimal | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("none", "nan", "-", ""):
        return None
    return parse_decimal(value)


def parse_str(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s and s.lower() not in ("none", "nan") else None
