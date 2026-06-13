from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.business import ReconciliationStatus


class OrderFinancialsResponse(BaseModel):
    order_item_id: str
    order_id: str | None
    neft_id: str | None
    neft_type: str | None
    sku: str | None
    fsn: str | None
    product_title: str | None
    order_date: date | None
    delivery_date: date | None
    settlement_date: date | None

    # Settlement components
    sale_amount: Decimal | None
    total_offer_amount: Decimal
    my_share: Decimal
    marketplace_fee: Decimal
    tcs: Decimal
    tds: Decimal
    gst_on_mp_fees: Decimal
    refund: Decimal

    # Invoice components
    invoice_fee_total: Decimal
    invoice_gst_total: Decimal
    commission_fee: Decimal
    shipping_fee: Decimal
    other_fee: Decimal

    # Reconciliation
    settlement_amount: Decimal | None
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
    return_recovery: int
    total_leakage: Decimal
    total_overpaid: Decimal
