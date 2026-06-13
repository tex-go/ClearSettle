import uuid
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw import FeesRaw, OrdersRaw, SettlementsRaw

_ORDERS_COLS = {
    "order item id": "order_item_id",
    "order id": "order_id",
    "sku": "sku",
    "fsn": "fsn",
    "product title": "product_title",
    "quantity": "quantity",
    "order date": "order_date",
    "dispatch date": "dispatch_date",
    "delivery date": "delivery_date",
    "order item status": "order_item_status",
}

_FEES_COLS = {
    "order item id": "order_item_id",
    "fee name": "fee_name",
    "fee amount": "fee_amount",
    "fee waiver amount": "fee_waiver_amount",
    "cgst": "cgst",
    "sgst": "sgst",
    "igst": "igst",
    "tax amount": "tax_amount",
    "date": "fee_date",
}

_SETTLEMENTS_COLS = {
    "neft id": "neft_id",
    "settlement date": "settlement_date",
    "settlement amount": "settlement_amount",
    "order id": "order_id",
    "order item id": "order_item_id",
    "selling price": "selling_price",
    "marketplace fee": "marketplace_fee",
    "taxes": "taxes",
    "offer adjustments": "offer_adjustments",
    "shipping charges": "shipping_charges",
    "sku": "sku",
    "fsn": "fsn",
}


def _read_file(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    if file_name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(file_bytes), dtype=str)
    return pd.read_csv(BytesIO(file_bytes), dtype=str)


def _normalise(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    return df.rename(columns=col_map)


def _to_raw_json(row: dict) -> dict:
    return {k: (None if pd.isna(v) else str(v).strip()) for k, v in row.items()}


async def ingest_orders(
    session: AsyncSession, file_bytes: bytes, file_name: str
) -> tuple[uuid.UUID, int]:
    batch_id = uuid.uuid4()
    df = _normalise(_read_file(file_bytes, file_name), _ORDERS_COLS)
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
    df = _normalise(_read_file(file_bytes, file_name), _FEES_COLS)
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
    df = _normalise(_read_file(file_bytes, file_name), _SETTLEMENTS_COLS)
    now = datetime.now(timezone.utc)
    rows = [
        SettlementsRaw(batch_id=batch_id, file_name=file_name, uploaded_at=now,
                       row_number=i + 1, raw_json=_to_raw_json(row))
        for i, row in enumerate(df.to_dict("records"))
    ]
    session.add_all(rows)
    await session.commit()
    return batch_id, len(rows)
