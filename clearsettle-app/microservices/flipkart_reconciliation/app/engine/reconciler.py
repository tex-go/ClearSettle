from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, union
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import OrderFinancials, ReconciliationStatus
from app.models.etl import FeesEtl, OrdersEtl, SettlementsEtl

_COMMISSION_KEYWORDS = ("commission", "fixed fee", "marketplace fee", "platform fee")
_SHIPPING_KEYWORDS = ("shipping", "courier", "delivery", "logistics", "sdd fee")


def _classify_fee(fee_name: str | None) -> str:
    if not fee_name:
        return "other"
    name = fee_name.lower()
    if any(k in name for k in _COMMISSION_KEYWORDS):
        return "commission"
    if any(k in name for k in _SHIPPING_KEYWORDS):
        return "shipping"
    return "other"


async def reconcile_order_item(session: AsyncSession, order_item_id: str) -> OrderFinancials:
    order = (await session.execute(
        select(OrdersEtl)
        .where(OrdersEtl.order_item_id == order_item_id, OrdersEtl.is_valid.is_(True))
        .limit(1)
    )).scalar_one_or_none()

    fees = (await session.execute(
        select(FeesEtl).where(FeesEtl.order_item_id == order_item_id, FeesEtl.is_valid.is_(True))
    )).scalars().all()

    settlement = (await session.execute(
        select(SettlementsEtl)
        .where(SettlementsEtl.order_item_id == order_item_id, SettlementsEtl.is_valid.is_(True))
        .limit(1)
    )).scalar_one_or_none()

    commission_fee = Decimal("0")
    shipping_fee = Decimal("0")
    other_fee = Decimal("0")
    tax_amount = Decimal("0")

    for f in fees:
        net = (f.fee_amount or Decimal("0")) - (f.fee_waiver_amount or Decimal("0"))
        category = _classify_fee(f.fee_name)
        if category == "commission":
            commission_fee += net
        elif category == "shipping":
            shipping_fee += net
        else:
            other_fee += net
        tax_amount += f.tax_amount or Decimal("0")

    selling_price = settlement.selling_price if settlement else None
    settlement_amount = settlement.settlement_amount if settlement else None

    # Flipkart fee amounts are already negative (deductions), so add them
    expected_settlement = (
        selling_price + commission_fee + shipping_fee + other_fee + tax_amount
        if selling_price is not None
        else None
    )

    if order is None and settlement is None:
        status = ReconciliationStatus.MISSING_ORDER
    elif settlement is None:
        status = ReconciliationStatus.MISSING_SETTLEMENT
    elif not fees:
        status = ReconciliationStatus.MISSING_FEE_RECORD
    elif expected_settlement is None:
        status = ReconciliationStatus.MISSING_FEE_RECORD
    else:
        diff = settlement_amount - expected_settlement
        if diff == 0:
            status = ReconciliationStatus.MATCHED
        elif expected_settlement > settlement_amount:
            status = ReconciliationStatus.SHORT_PAID
        else:
            status = ReconciliationStatus.OVER_PAID

    difference = (
        settlement_amount - expected_settlement
        if settlement_amount is not None and expected_settlement is not None
        else None
    )

    now = datetime.now(timezone.utc)
    row = dict(
        order_item_id=order_item_id,
        order_id=(order.order_id if order else None) or (settlement.order_id if settlement else None),
        sku=(order.sku if order else None) or (settlement.sku if settlement else None),
        fsn=(order.fsn if order else None) or (settlement.fsn if settlement else None),
        product_title=order.product_title if order else None,
        order_date=order.order_date if order else None,
        delivery_date=order.delivery_date if order else None,
        selling_price=selling_price,
        marketplace_fee=settlement.marketplace_fee if settlement else Decimal("0"),
        commission_fee=commission_fee,
        shipping_fee=shipping_fee,
        tax_amount=tax_amount,
        other_fee=other_fee,
        settlement_amount=settlement_amount,
        settlement_date=settlement.settlement_date if settlement else None,
        expected_settlement=expected_settlement,
        difference=difference,
        reconciliation_status=status.value,
        last_reconciled_at=now,
        updated_at=now,
    )

    stmt = (
        insert(OrderFinancials)
        .values(**row)
        .on_conflict_do_update(
            index_elements=["order_item_id"],
            set_={k: v for k, v in row.items() if k not in ("order_item_id", "created_at")},
        )
        .returning(OrderFinancials)
    )
    record = (await session.execute(stmt)).scalar_one()
    await session.commit()
    return record


async def reconcile_batch(session: AsyncSession, order_item_ids: list[str]) -> list[OrderFinancials]:
    return [await reconcile_order_item(session, oid) for oid in order_item_ids]


async def get_all_order_item_ids(session: AsyncSession) -> list[str]:
    stmt = union(
        select(OrdersEtl.order_item_id).where(OrdersEtl.is_valid.is_(True)),
        select(FeesEtl.order_item_id).where(FeesEtl.is_valid.is_(True)),
        select(SettlementsEtl.order_item_id).where(SettlementsEtl.is_valid.is_(True)),
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]
