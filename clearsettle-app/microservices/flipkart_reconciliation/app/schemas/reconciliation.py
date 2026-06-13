from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.business import ReconciliationStatus


class OrderFinancialsResponse(BaseModel):
    order_item_id: str
    order_id: str | None
    sku: str | None
    fsn: str | None
    product_title: str | None
    order_date: date | None
    delivery_date: date | None
    selling_price: Decimal | None
    marketplace_fee: Decimal
    commission_fee: Decimal
    shipping_fee: Decimal
    tax_amount: Decimal
    other_fee: Decimal
    settlement_amount: Decimal | None
    settlement_date: date | None
    expected_settlement: Decimal | None
    difference: Decimal | None
    status: ReconciliationStatus
    last_reconciled_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if hasattr(obj, "reconciliation_status"):
            obj.__dict__.setdefault("status", obj.reconciliation_status)
        return super().model_validate(obj, **kwargs)


class ReconciliationSummary(BaseModel):
    total_items: int
    matched: int
    short_paid: int
    over_paid: int
    missing_settlement: int
    missing_order: int
    missing_fee_record: int
    total_leakage: Decimal
