import uuid
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw import FeesRaw, OrdersRaw, SettlementsRaw

# ── Column mappings (lowercase-stripped keys → canonical name) ─────────────────
# Orders (FulfilmentReports_Orders — sheet: "Orders")
_ORDERS_COLS = {
    "order_item_id": "order_item_id",
    "order_id": "order_id",
    "sku": "sku",
    "fsn": "fsn",
    "product_title": "product_title",
    "quantity": "quantity",
    "order_date": "order_date",
    "order_item_status": "order_item_status",
    "dispatched_date": "dispatch_date",
    "order_delivery_date": "delivery_date",
    "order_approval_date": "dispatch_date",     # fallback
    # space-separated variants
    "order item id": "order_item_id",
    "order id": "order_id",
    "product title": "product_title",
    "order date": "order_date",
    "dispatch date": "dispatch_date",
    "delivery date": "delivery_date",
    "order item status": "order_item_status",
}

# Fees (Invoices_CommissionInvoiceTransactionDetails — sheet: "Commission Invoice Transactions")
# Actual column names (normalized):
#   "order item id/ listing id/ campaign id/transaction id"
#   "fee name", "fee amount (rs.)", "total fee amount(rs.)", "fee waiver amount(rs.)"
#   "cgst amount", "sgst/utgst amount", "igst amount", "total tax amount (rs.)"
#   "date"
_FEES_COLS = {
    "order item id/ listing id/ campaign id/transaction id": "order_item_id",
    "fee name": "fee_name",
    "fee amount (rs.)": "fee_amount",
    "total fee amount(rs.)": "fee_amount",      # net after waiver
    "fee waiver amount(rs.)": "fee_waiver_amount",
    "cgst amount": "cgst",
    "sgst/utgst amount": "sgst",
    "igst amount": "igst",
    "total tax amount (rs.)": "tax_amount",
    "date": "fee_date",
    # snake_case variants
    "order_item_id": "order_item_id",
    "fee_name": "fee_name",
    "fee_amount": "fee_amount",
    "fee_waiver_amount": "fee_waiver_amount",
    "tax_amount": "tax_amount",
    # generic variants
    "order item id": "order_item_id",
    "tax amount": "tax_amount",
    "transaction date": "fee_date",
    "invoice date": "fee_date",
}

# Settlements (PaymentReports_SettledTransactions — sheet: "Orders")
# Actual column names (normalized after stripping \n):
#   "neft id", " payment date", "bank settlement value (rs.)  = sum(j:r)"
#   "order id", "order item id", "sale amount (rs.)"
#   "marketplace fee (rs.) = sum (v:ai)", "commission (rs.)", "shipping fee (rs.)"
#   "tcs (rs.)", "gst on mp fees (rs.)", "total offer amount (rs.)"
#   "seller sku", "dispatch date", "order date"
_SETTLEMENTS_COLS = {
    "neft id": "neft_id",
    "payment date": "settlement_date",
    "order id": "order_id",
    "order item id": "order_item_id",
    "sale amount (rs.)": "selling_price",
    "commission (rs.)": "commission_fee",
    "shipping fee (rs.)": "shipping_charges",
    "total offer amount (rs.)": "offer_adjustments",
    "tcs (rs.)": "taxes",
    "seller sku": "sku",
    # snake_case variants
    "neft_id": "neft_id",
    "settlement_date": "settlement_date",
    "settlement_amount": "settlement_amount",
    "order_id": "order_id",
    "order_item_id": "order_item_id",
    "selling_price": "selling_price",
    "marketplace_fee": "marketplace_fee",
    "shipping_charges": "shipping_charges",
    "offer_adjustments": "offer_adjustments",
    "taxes": "taxes",
    "sku": "sku",
    "fsn": "fsn",
    # space variants
    "settlement date": "settlement_date",
    "settlement amount": "settlement_amount",
    "selling price": "selling_price",
    "marketplace fee": "marketplace_fee",
    "shipping charges": "shipping_charges",
    "offer adjustments": "offer_adjustments",
    "neft reference id": "neft_id",
}

# The "bank settlement value" column name contains \n and formula refs; match by prefix
_SETTLEMENT_AMOUNT_PREFIX = "bank settlement value"

# ── Sheet detection ────────────────────────────────────────────────────────────
_ORDERS_SHEET_HINTS      = ["orders", "order", "fulfilment", "fulfillment"]
_FEES_SHEET_HINTS        = ["commission", "fee", "invoice", "charges"]
# Settlements file uses "Orders" sheet — add as last-resort hint
_SETTLEMENTS_SHEET_HINTS = ["settlement", "settled", "payment", "payout", "orders"]

# ── Header-row keywords (≥2 matches = header row) ─────────────────────────────
_ORDERS_KEYWORDS     = ["order_item_id", "order_id", "sku", "status", "order item id"]
_FEES_KEYWORDS       = ["order item id", "fee", "commission", "cgst", "sgst"]
_SETTLEMENTS_KEYWORDS = ["neft", "order item id", "order id", "sale amount", "settlement"]


def _pick_sheet(xl: pd.ExcelFile, hints: list[str]) -> str | int:
    for hint in hints:
        for name in xl.sheet_names:
            if hint in name.lower():
                return name
    return 0


def _find_header_row(xl: pd.ExcelFile, sheet: str | int, keywords: list[str]) -> int:
    probe = pd.read_excel(xl, sheet_name=sheet, header=None, dtype=str, nrows=15)
    for i, row in probe.iterrows():
        row_str = " ".join(str(v).lower() for v in row.values if pd.notna(v))
        if sum(1 for kw in keywords if kw in row_str) >= 2:
            return i
    return 0


def _clean_col_name(col: str) -> str:
    """Normalize column name: strip, lowercase, collapse whitespace/newlines."""
    return " ".join(col.replace("\n", " ").split()).lower()


def _normalise(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    df.columns = [_clean_col_name(str(c)) for c in df.columns]
    # Handle "bank settlement value ..." prefix for settlement amount
    for col in df.columns:
        if col.startswith(_SETTLEMENT_AMOUNT_PREFIX) and col not in col_map:
            col_map = {**col_map, col: "settlement_amount"}
    # Handle "marketplace fee ..." prefix
    for col in df.columns:
        if col.startswith("marketplace fee") and col not in col_map:
            col_map = {**col_map, col: "marketplace_fee"}
    return df.rename(columns=col_map)


def _read_excel(file_bytes: bytes, sheet_hints: list[str], keywords: list[str]) -> pd.DataFrame:
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = _pick_sheet(xl, sheet_hints)
    header_row = _find_header_row(xl, sheet, keywords)
    df = pd.read_excel(xl, sheet_name=sheet, header=header_row, dtype=str)
    return df.dropna(how="all").reset_index(drop=True)


def _read_file(
    file_bytes: bytes, file_name: str, sheet_hints: list[str], keywords: list[str]
) -> pd.DataFrame:
    if file_name.lower().endswith((".xlsx", ".xls")):
        return _read_excel(file_bytes, sheet_hints, keywords)
    return pd.read_csv(BytesIO(file_bytes), dtype=str)


def _clean_val(value) -> str | None:
    """Strip whitespace and stray quotes; return None for blanks/NaN."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    s = str(value).strip().strip('"')
    return s if s else None


def _to_raw_json(row: dict) -> dict:
    return {k: _clean_val(v) for k, v in row.items()}


async def ingest_orders(
    session: AsyncSession, file_bytes: bytes, file_name: str
) -> tuple[uuid.UUID, int]:
    batch_id = uuid.uuid4()
    df = _normalise(
        _read_file(file_bytes, file_name, _ORDERS_SHEET_HINTS, _ORDERS_KEYWORDS),
        _ORDERS_COLS,
    )
    now = datetime.now(timezone.utc)
    rows = [
        OrdersRaw(batch_id=batch_id, file_name=file_name, uploaded_at=now,
                  row_number=i + 1, raw_json=_to_raw_json(row))
        for i, row in enumerate(df.to_dict("records"))
    ]
    session.add_all(rows)
    await session.commit()
    return batch_id, len(rows)


async def ingest_fees(
    session: AsyncSession, file_bytes: bytes, file_name: str
) -> tuple[uuid.UUID, int]:
    batch_id = uuid.uuid4()
    df = _normalise(
        _read_file(file_bytes, file_name, _FEES_SHEET_HINTS, _FEES_KEYWORDS),
        _FEES_COLS,
    )
    now = datetime.now(timezone.utc)
    rows = [
        FeesRaw(batch_id=batch_id, file_name=file_name, uploaded_at=now,
                row_number=i + 1, raw_json=_to_raw_json(row))
        for i, row in enumerate(df.to_dict("records"))
    ]
    session.add_all(rows)
    await session.commit()
    return batch_id, len(rows)


async def ingest_settlements(
    session: AsyncSession, file_bytes: bytes, file_name: str
) -> tuple[uuid.UUID, int]:
    batch_id = uuid.uuid4()
    df = _normalise(
        _read_file(file_bytes, file_name, _SETTLEMENTS_SHEET_HINTS, _SETTLEMENTS_KEYWORDS),
        _SETTLEMENTS_COLS,
    )
    now = datetime.now(timezone.utc)
    rows = [
        SettlementsRaw(batch_id=batch_id, file_name=file_name, uploaded_at=now,
                       row_number=i + 1, raw_json=_to_raw_json(row))
        for i, row in enumerate(df.to_dict("records"))
    ]
    session.add_all(rows)
    await session.commit()
    return batch_id, len(rows)
