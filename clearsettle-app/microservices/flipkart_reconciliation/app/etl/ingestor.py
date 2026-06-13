import uuid
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw import FeesRaw, OrdersRaw, SettlementsRaw

# ── Column mappings (cleaned lowercase keys → canonical name) ─────────────────

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
    "order_approval_date": "dispatch_date",
    "order item id": "order_item_id",
    "order id": "order_id",
    "product title": "product_title",
    "order date": "order_date",
    "dispatch date": "dispatch_date",
    "delivery date": "delivery_date",
    "order item status": "order_item_status",
}

# Fees (Invoices_CommissionInvoiceTransactionDetails)
# Actual header row 0: Service Type | Order Item ID/ Listing ID/... | Fee Name | Total Fee Amount | Fee Amount | ...
_FEES_COLS = {
    "order item id/ listing id/ campaign id/transaction id": "order_item_id",
    "fee name": "fee_name",
    "fee amount (rs.)": "fee_amount",
    "total fee amount(rs.)": "fee_amount",
    "fee waiver amount(rs.)": "fee_waiver_amount",
    "cgst amount": "cgst",
    "sgst/utgst amount": "sgst",
    "igst amount": "igst",
    "total tax amount (rs.)": "tax_amount",
    "date": "fee_date",
    "order_item_id": "order_item_id",
    "fee_name": "fee_name",
    "fee_amount": "fee_amount",
    "fee_waiver_amount": "fee_waiver_amount",
    "tax_amount": "tax_amount",
    "order item id": "order_item_id",
    "tax amount": "tax_amount",
    "transaction date": "fee_date",
    "invoice date": "fee_date",
}

# Settlements (PaymentReports_SettledTransactions — sheet "Orders", header row 1)
# The file has 3-row merged header: row0=groups, row1=field names, row2=sub-fields/totals
# After reading with header=1 and skipping row2 (sub-header), actual data starts.
#
# Full column set (V2 — captures all BSV formula components):
#   NEFT ID, Neft Type, Payment Date, Bank Settlement Value (Rs.) = SUM(J:R)
#   Input GST + TCS Credits, Income Tax Credits [TDS]
#   Order ID, Order item ID, Sale Amount (Rs.), Total Offer Amount (Rs.), My share (Rs.)
#   Customer Add-ons Amount (Rs.), Marketplace Fee (Rs.) = SUM(V:AI), Taxes (Rs.)
#   Offer Adjustments (Rs.), Protection Fund (Rs.), Refund (Rs.)
#   Commission (Rs.), Fixed Fee (Rs.), Collection Fee (Rs.), Shipping Fee (Rs.)
#   Reverse Shipping Fee (Rs.), TCS (Rs.), TDS (Rs.), GST on MP Fees (Rs.)
#   Seller SKU, Order Date

_SETTLEMENTS_COLS = {
    # Payment details
    "neft id": "neft_id",
    "neft_id": "neft_id",
    "neft reference id": "neft_id",
    "neft type": "neft_type",
    "payment date": "settlement_date",
    "settlement date": "settlement_date",
    "settlement_date": "settlement_date",
    # Order identifiers
    "order id": "order_id",
    "order_id": "order_id",
    "order item id": "order_item_id",
    "order_item_id": "order_item_id",
    # Transaction summary components (all map to canonical V2 names)
    "sale amount (rs.)": "sale_amount",
    "selling price": "sale_amount",
    "selling_price": "sale_amount",
    "total offer amount (rs.)": "total_offer_amount",
    "my share (rs.)": "my_share",
    "customer add-ons amount (rs.)": "customer_addons_amount",
    "offer adjustments (rs.)": "offer_adjustments",
    "protection fund (rs.)": "protection_fund",
    "refund (rs.)": "refund",
    # Tax components
    "tcs (rs.)": "tcs",
    "tds (rs.)": "tds",
    "gst on mp fees (rs.)": "gst_on_mp_fees",
    # MP fee sub-components
    "fixed fee (rs.)": "fixed_fee",
    "collection fee (rs.)": "collection_fee",
    "reverse shipping fee (rs.)": "reverse_shipping_fee",
    # Item details
    "seller sku": "sku",
    "sku": "sku",
    # Legacy / snake_case variants
    "marketplace_fee": "marketplace_fee",
    "settlement_amount": "settlement_amount",
    "offer_adjustments": "offer_adjustments",
    "taxes": "taxes_legacy",  # old "taxes" field — ignored in V2 formula
}

# Prefix matches for column names containing formulas / newlines
_SETTLEMENT_AMOUNT_PREFIX = "bank settlement value"
_MARKETPLACE_FEE_PREFIX = "marketplace fee"

# ── Sheet detection ────────────────────────────────────────────────────────────
_ORDERS_SHEET_HINTS = ["orders", "order", "fulfilment", "fulfillment"]
_FEES_SHEET_HINTS = ["commission invoice transactions", "commission", "fee", "invoice", "charges"]
_SETTLEMENTS_SHEET_HINTS = ["settlement", "settled", "payment", "payout", "orders"]

# ── Header-row keyword matching (≥2 matches = header row) ────────────────────
_ORDERS_KEYWORDS = ["order_item_id", "order_id", "sku", "status", "order item id"]
_FEES_KEYWORDS = ["order item id", "fee", "commission", "cgst", "sgst"]
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
    return " ".join(col.replace("\n", " ").split()).lower()


def _normalise(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    df.columns = [_clean_col_name(str(c)) for c in df.columns]
    # Prefix-match for bank settlement value and marketplace fee columns
    resolved_map = dict(col_map)
    for col in df.columns:
        if col not in resolved_map:
            if col.startswith(_SETTLEMENT_AMOUNT_PREFIX):
                resolved_map[col] = "settlement_amount"
            elif col.startswith(_MARKETPLACE_FEE_PREFIX):
                resolved_map[col] = "marketplace_fee"
    return df.rename(columns=resolved_map)


def _read_excel(file_bytes: bytes, sheet_hints: list[str], keywords: list[str]) -> pd.DataFrame:
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheet = _pick_sheet(xl, sheet_hints)
    header_row = _find_header_row(xl, sheet, keywords)
    df = pd.read_excel(xl, sheet_name=sheet, header=header_row, dtype=str)
    # For settlement file: row immediately after the header is a sub-header row
    # ("Total (Rs.)\n", "Free Shipping Offer (Rs.)", etc.) — drop it.
    # Detect by checking if the first column value matches a known sub-header pattern.
    if len(df) > 0:
        first_val = str(df.iloc[0, 0]).strip().lower()
        if "total" in first_val or first_val in ("nan", ""):
            df = df.iloc[1:].reset_index(drop=True)
    return df.dropna(how="all").reset_index(drop=True)


def _read_file(
    file_bytes: bytes, file_name: str, sheet_hints: list[str], keywords: list[str]
) -> pd.DataFrame:
    if file_name.lower().endswith((".xlsx", ".xls")):
        return _read_excel(file_bytes, sheet_hints, keywords)
    return pd.read_csv(BytesIO(file_bytes), dtype=str)


def _clean_val(value) -> str | None:
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
