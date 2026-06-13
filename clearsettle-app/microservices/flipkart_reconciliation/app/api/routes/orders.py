from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.business import OrderFinancials
from app.schemas.reconciliation import OrderFinancialsResponse

router = APIRouter()


def _to_response(record: OrderFinancials) -> OrderFinancialsResponse:
    data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
    data["status"] = data.pop("reconciliation_status")
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
