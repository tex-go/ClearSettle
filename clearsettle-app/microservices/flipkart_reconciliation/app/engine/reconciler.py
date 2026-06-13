from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, union
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import OrderFinancials, ReconciliationStatus
from app.models.etl import FeesEtl, OrdersEtl, SettlementsEtl

# ── Fee classification ─────────────────────────────────────────────────────────
_COMMISSION_KEYWORDS = ("commission", "fixed fee", "marketplace fee", "platform fee")
_SHIPPING_KEYWORDS = ("shipping", "courier", "delivery", "logistics", "sdd fee")
# Wallet Redeem is an ad-spend deduction, not an order-level fee — exclude from reconciliation
_EXCLUDE_FEE_NAMES = {"wallet redeem"}

# Tolerance for reconciliation match (Rs.)
_MATCH_TOLERANCE = Decimal("2.00")


def _classify_fee(fee_name: str | None) -> str:
    if not fee_name:
        return "other"
    name = fee_name.lower()
    if any(k in name for k in _COMMISSION_KEYWORDS):
        return "commission"
    if any(k in name for k in _SHIPPING_KEYWORDS):
        return "shipping"
    return "other"


def _d(val) -> Decimal:
    """Safely coerce to Decimal, defaulting to 0."""
    if val is None:
        return Decimal("0")
    return val if isinstance(val, Decimal) else Decimal(str(val))


async def reconcile_order_item(session: AsyncSession, order_item_id: str) -> OrderFinancials:
    order = (await session.execute(
        select(OrdersEtl)
        .where(OrdersEtl.order_item_id == order_item_id, OrdersEtl.is_valid.is_(True))
        .limit(1)
    )).scalar_one_or_none()

    # Exclude Wallet Redeem and other non-order fees from per-order reconciliation
    fees = (await session.execute(
        select(FeesEtl).where(
            FeesEtl.order_item_id == order_item_id,
            FeesEtl.is_valid.is_(True),
        )
    )).scalars().all()
    fees = [f for f in fees if (f.fee_name or "").lower() not in _EXCLUDE_FEE_NAMES]

    settlement = (await session.execute(
        select(SettlementsEtl)
        .where(SettlementsEtl.order_item_id == order_item_id, SettlementsEtl.is_valid.is_(True))
        .limit(1)
    )).scalar_one_or_none()

    # ── Aggregate invoice fees ────────────────────────────────────────────────
    commission_fee = Decimal("0")
    shipping_fee = Decimal("0")
    other_fee = Decimal("0")
    invoice_fee_total = Decimal("0")
    invoice_gst_total = Decimal("0")

    for f in fees:
        net = _d(f.fee_amount) - _d(f.fee_waiver_amount)
        category = _classify_fee(f.fee_name)
        if category == "commission":
            commission_fee += net
        elif category == "shipping":
            shipping_fee += net
        else:
            other_fee += net
        invoice_fee_total += net
        invoice_gst_total += _d(f.tax_amount)

    # ── Pull settlement components ────────────────────────────────────────────
    if settlement:
        sale_amount = settlement.sale_amount          # Sale Amount (Rs.)
        total_offer_amount = _d(settlement.total_offer_amount)
        my_share = _d(settlement.my_share)
        customer_addons = _d(settlement.customer_addons_amount)
        marketplace_fee = _d(settlement.marketplace_fee)
        tcs = _d(settlement.tcs)
        tds = _d(settlement.tds)
        gst_on_mp_fees = _d(settlement.gst_on_mp_fees)
        offer_adjustments = _d(settlement.offer_adjustments)
        protection_fund = _d(settlement.protection_fund)
        refund = _d(settlement.refund)
        settlement_amount = settlement.settlement_amount
    else:
        sale_amount = total_offer_amount = my_share = customer_addons = None
        marketplace_fee = tcs = tds = gst_on_mp_fees = Decimal("0")
        offer_adjustments = protection_fund = refund = Decimal("0")
        settlement_amount = None

    # ── V2 expected settlement formula ────────────────────────────────────────
    # Expected = all settlement pass-through components + invoice fees (the audit target)
    # Difference = actual_BSV - expected → positive means Flipkart paid more than expected
    #
    # Components from settlement (pass-through, agreed values):
    #   sale_amount, total_offer_amount, my_share, customer_addons,
    #   tcs, tds (government levies), offer_adjustments, protection_fund, refund
    # Components from invoice (audit target):
    #   invoice_fee_total, invoice_gst_total
    #
    # If invoice fees == settlement marketplace_fee + gst_on_mp_fees → expected == BSV → MATCHED
    if sale_amount is not None:
        expected_settlement = (
            _d(sale_amount)
            + total_offer_amount
            + my_share
            + customer_addons
            + invoice_fee_total
            + invoice_gst_total
            + tcs
            + tds
            + offer_adjustments
            + protection_fund
            + refund
        )
    else:
        expected_settlement = None

    # ── Classification ────────────────────────────────────────────────────────
    if order is None and settlement is None:
        status = ReconciliationStatus.MISSING_ORDER

    elif settlement is None:
        status = ReconciliationStatus.MISSING_SETTLEMENT

    elif refund < Decimal("0"):
        # Return recovery: Flipkart recouped sale amount — not a leakage
        status = ReconciliationStatus.RETURN_RECOVERY

    elif not fees:
        # No commission invoice entry for this order
        if marketplace_fee == Decimal("0"):
            # Settlement also shows no fees → genuinely no-fee order → MATCHED
            status = ReconciliationStatus.MATCHED
        else:
            # Settlement deducted fees but no invoice to verify against
            status = ReconciliationStatus.MISSING_FEE_RECORD

    elif expected_settlement is None:
        status = ReconciliationStatus.MISSING_FEE_RECORD

    else:
        diff = _d(settlement_amount) - expected_settlement
        if abs(diff) <= _MATCH_TOLERANCE:
            status = ReconciliationStatus.MATCHED
        elif diff < -_MATCH_TOLERANCE:
            # Settlement paid LESS than expected → Flipkart deducted more fees than invoiced
            status = ReconciliationStatus.SHORT_PAID
        else:
            # Settlement paid MORE than expected → Flipkart deducted fewer fees than invoiced
            # (fee waiver, rebate, or fully-discounted order where fee wasn't charged)
            status = ReconciliationStatus.OVER_PAID

    difference = (
        _d(settlement_amount) - expected_settlement
        if settlement_amount is not None and expected_settlement is not None
        else None
    )

    now = datetime.now(timezone.utc)
    row = dict(
        order_item_id=order_item_id,
        order_id=(order.order_id if order else None) or (settlement.order_id if settlement else None),
        neft_id=settlement.neft_id if settlement else None,
        neft_type=settlement.neft_type if settlement else None,
        sku=(order.sku if order else None) or (settlement.sku if settlement else None),
        fsn=(order.fsn if order else None) or (settlement.fsn if settlement else None),
        product_title=order.product_title if order else None,
        order_date=order.order_date if order else None,
        delivery_date=order.delivery_date if order else None,
        settlement_date=settlement.settlement_date if settlement else None,
        # Settlement components
        sale_amount=sale_amount,
        total_offer_amount=total_offer_amount,
        my_share=my_share,
        marketplace_fee=marketplace_fee,
        tcs=tcs,
        tds=tds,
        gst_on_mp_fees=gst_on_mp_fees,
        refund=refund,
        # Invoice components
        invoice_fee_total=invoice_fee_total,
        invoice_gst_total=invoice_gst_total,
        commission_fee=commission_fee,
        shipping_fee=shipping_fee,
        other_fee=other_fee,
        # Reconciliation result
        settlement_amount=settlement_amount,
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
