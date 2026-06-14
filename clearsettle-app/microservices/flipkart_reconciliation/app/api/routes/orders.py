from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.business import OrderFinancials
from app.schemas.reconciliation import OrderFinancialsResponse

router = APIRouter()

# These schema fields are declared Decimal (non-nullable) but may be NULL in the DB
# when a row was inserted without the Python-side default being applied (e.g. via raw SQL).
_NON_OPTIONAL_DECIMAL_FIELDS = frozenset({
    "total_offer_amount", "my_share", "marketplace_fee",
    "tcs", "tds", "gst_on_mp_fees", "refund",
    "invoice_fee_total", "invoice_gst_total",
    "commission_fee", "shipping_fee", "other_fee",
})


def _to_response(record: OrderFinancials) -> OrderFinancialsResponse:
    data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
    data["status"] = data.pop("reconciliation_status")
    for field in _NON_OPTIONAL_DECIMAL_FIELDS:
        if data.get(field) is None:
            data[field] = Decimal("0")
    return OrderFinancialsResponse.model_validate(data)


@router.get("/order-item/{order_item_id}", response_model=OrderFinancialsResponse)
async def get_order_item(
    order_item_id: str,
    session: AsyncSession = Depends(get_session),
):
    row = (await session.execute(
        select(OrderFinancials).where(OrderFinancials.order_item_id == order_item_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(404, f"Order item {order_item_id!r} not found in reconciled data")
    return _to_response(row)


@router.get("/order/{order_id}", response_model=list[OrderFinancialsResponse])
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(OrderFinancials).where(OrderFinancials.order_id == order_id)
    )).scalars().all()
    if not rows:
        raise HTTPException(404, f"Order {order_id!r} not found in reconciled data")
    return [_to_response(r) for r in rows]
