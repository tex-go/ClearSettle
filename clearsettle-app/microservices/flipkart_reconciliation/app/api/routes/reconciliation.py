from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.orders import _to_response
from app.engine.reconciler import get_all_order_item_ids, reconcile_batch, reconcile_order_item
from app.models.business import OrderFinancials, ReconciliationStatus
from app.models.etl import OrdersEtl
from app.reports.excel_exporter import generate_april_report
from app.schemas.reconciliation import OrderFinancialsResponse, ReconciliationSummary

router = APIRouter()


@router.get("/order-item/{order_item_id}", response_model=OrderFinancialsResponse)
async def reconcile_item(
    order_item_id: str,
    session: AsyncSession = Depends(get_session),
):
    record = await reconcile_order_item(session, order_item_id)
    return _to_response(record)


@router.get("/date-range", response_model=list[OrderFinancialsResponse])
async def get_reconciled_date_range(
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(OrderFinancials).where(
            OrderFinancials.order_date >= start,
            OrderFinancials.order_date <= end,
        )
    )).scalars().all()
    return [_to_response(r) for r in rows]


@router.post("/batch", response_model=list[OrderFinancialsResponse])
async def reconcile_batch_endpoint(
    order_item_ids: list[str],
    session: AsyncSession = Depends(get_session),
):
    if not order_item_ids:
        raise HTTPException(400, "Provide at least one order_item_id")
    results = await reconcile_batch(session, order_item_ids)
    return [_to_response(r) for r in results]


@router.get("/results", response_model=list[OrderFinancialsResponse])
async def get_results(
    status: str | None = Query(None, description="Filter by reconciliation_status"),
    session: AsyncSession = Depends(get_session),
):
    """Return all reconciliation records as JSON (used by the UI table)."""
    stmt = select(OrderFinancials).order_by(OrderFinancials.reconciliation_status)
    if status:
        stmt = stmt.where(OrderFinancials.reconciliation_status == status)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_response(r) for r in rows]


@router.get("/export")
async def export_reconciliation_report(
    period: str = Query("April 2026", description="Period label for the report header"),
    filter_to_orders: bool = Query(True, description="When true, only include order_item_ids present in orders_etl"),
    session: AsyncSession = Depends(get_session),
):
    """Download a formatted Excel reconciliation report."""
    stmt = select(OrderFinancials)
    if filter_to_orders:
        order_ids_result = await session.execute(
            select(OrdersEtl.order_item_id).where(OrdersEtl.is_valid.is_(True)).distinct()
        )
        april_ids = {r[0] for r in order_ids_result.all()}
        if not april_ids:
            raise HTTPException(404, "No orders found — upload orders file first")
        stmt = stmt.where(OrderFinancials.order_item_id.in_(april_ids))

    rows = (await session.execute(stmt.order_by(OrderFinancials.reconciliation_status))).scalars().all()
    if not rows:
        raise HTTPException(404, "No reconciliation data — run /reconciliation/run-all first")

    row_dicts = [
        {c.key: getattr(r, c.key) for c in r.__table__.columns}
        for r in rows
    ]
    xlsx_bytes = generate_april_report(row_dicts, period_label=period)

    filename = f"flipkart_reconciliation_{period.replace(' ', '_')}.xlsx"
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/run-all", response_model=ReconciliationSummary)
async def run_full_reconciliation(session: AsyncSession = Depends(get_session)):
    order_item_ids = await get_all_order_item_ids(session)
    if not order_item_ids:
        raise HTTPException(404, "No order items found — upload reports first via /ingest")

    results = await reconcile_batch(session, order_item_ids)

    total_leakage = sum(
        abs(r.difference)
        for r in results
        if r.difference and r.reconciliation_status == ReconciliationStatus.SHORT_PAID.value
    )

    return ReconciliationSummary(
        total_items=len(results),
        matched=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.MATCHED.value),
        short_paid=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.SHORT_PAID.value),
        over_paid=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.OVER_PAID.value),
        missing_settlement=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.MISSING_SETTLEMENT.value),
        missing_order=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.MISSING_ORDER.value),
        missing_fee_record=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.MISSING_FEE_RECORD.value),
        total_leakage=total_leakage or Decimal("0"),
    )
