import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.validator import parse_date, parse_decimal, parse_optional_decimal, parse_str
from app.models.etl import FeesEtl, OrdersEtl, SettlementsEtl
from app.models.raw import FeesRaw, OrdersRaw, SettlementsRaw


async def transform_orders(session: AsyncSession, batch_id: uuid.UUID) -> int:
    result = await session.execute(select(OrdersRaw).where(OrdersRaw.batch_id == batch_id))
    raws = result.scalars().all()
    rows = []
    for raw in raws:
        j = raw.raw_json
        raw_oi = parse_str(j.get("order_item_id"))
        # Flipkart orders prefix IDs with "OI:" — strip for cross-table join compatibility
        order_item_id = raw_oi.removeprefix("OI:") if raw_oi else None
        errors: dict = {}
        if not order_item_id:
            errors["order_item_id"] = "missing"
        qty_raw = j.get("quantity")
        quantity = int(qty_raw) if qty_raw and str(qty_raw).isdigit() else None
        rows.append(OrdersEtl(
            batch_id=batch_id,
            raw_id=raw.id,
            order_item_id=order_item_id or f"MISSING_ROW_{raw.row_number}",
            order_id=parse_str(j.get("order_id")),
            sku=parse_str(j.get("sku")),
            fsn=parse_str(j.get("fsn")),
            product_title=parse_str(j.get("product_title")),
            quantity=quantity,
            order_date=parse_date(j.get("order_date")),
            dispatch_date=parse_date(j.get("dispatch_date")),
            delivery_date=parse_date(j.get("delivery_date")),
            order_item_status=parse_str(j.get("order_item_status")),
            is_valid=not errors,
            validation_errors=errors or None,
        ))
    session.add_all(rows)
    await session.commit()
    return len(rows)


async def transform_fees(session: AsyncSession, batch_id: uuid.UUID) -> int:
    result = await session.execute(select(FeesRaw).where(FeesRaw.batch_id == batch_id))
    raws = result.scalars().all()
    rows = []
    for raw in raws:
        j = raw.raw_json
        order_item_id = parse_str(j.get("order_item_id"))
        errors: dict = {}
        if not order_item_id:
            errors["order_item_id"] = "missing"
        rows.append(FeesEtl(
            batch_id=batch_id,
            raw_id=raw.id,
            order_item_id=order_item_id or f"MISSING_ROW_{raw.row_number}",
            fee_name=parse_str(j.get("fee_name")),
            fee_amount=parse_decimal(j.get("fee_amount")),
            fee_waiver_amount=parse_decimal(j.get("fee_waiver_amount")),
            cgst=parse_decimal(j.get("cgst")),
            sgst=parse_decimal(j.get("sgst")),
            igst=parse_decimal(j.get("igst")),
            tax_amount=parse_decimal(j.get("tax_amount")),
            fee_date=parse_date(j.get("fee_date")),
            is_valid=not errors,
            validation_errors=errors or None,
        ))
    session.add_all(rows)
    await session.commit()
    return len(rows)


async def transform_settlements(session: AsyncSession, batch_id: uuid.UUID) -> int:
    result = await session.execute(select(SettlementsRaw).where(SettlementsRaw.batch_id == batch_id))
    raws = result.scalars().all()
    rows = []
    for raw in raws:
        j = raw.raw_json
        order_item_id = parse_str(j.get("order_item_id"))
        errors: dict = {}
        if not order_item_id:
            errors["order_item_id"] = "missing"
        rows.append(SettlementsEtl(
            batch_id=batch_id,
            raw_id=raw.id,
            neft_id=parse_str(j.get("neft_id")),
            neft_type=parse_str(j.get("neft_type")),
            settlement_date=parse_date(j.get("settlement_date")),
            settlement_amount=parse_optional_decimal(j.get("settlement_amount")),
            order_id=parse_str(j.get("order_id")),
            order_item_id=order_item_id or f"MISSING_ROW_{raw.row_number}",
            # V2 transaction summary components
            sale_amount=parse_optional_decimal(j.get("sale_amount")),
            total_offer_amount=parse_decimal(j.get("total_offer_amount")),
            my_share=parse_decimal(j.get("my_share")),
            customer_addons_amount=parse_decimal(j.get("customer_addons_amount")),
            marketplace_fee=parse_decimal(j.get("marketplace_fee")),
            offer_adjustments=parse_decimal(j.get("offer_adjustments")),
            protection_fund=parse_decimal(j.get("protection_fund")),
            refund=parse_decimal(j.get("refund")),
            # Tax components
            tcs=parse_decimal(j.get("tcs")),
            tds=parse_decimal(j.get("tds")),
            gst_on_mp_fees=parse_decimal(j.get("gst_on_mp_fees")),
            # MP fee sub-components
            fixed_fee=parse_decimal(j.get("fixed_fee")),
            collection_fee=parse_decimal(j.get("collection_fee")),
            reverse_shipping_fee=parse_decimal(j.get("reverse_shipping_fee")),
            # Item details
            sku=parse_str(j.get("sku")),
            fsn=parse_str(j.get("fsn")),
            is_valid=not errors,
            validation_errors=errors or None,
        ))
    session.add_all(rows)
    await session.commit()
    return len(rows)
