from datetime import date
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.orders import _to_response
from app.engine.leakage_engine import (
    generate_coverage_report,
    generate_leakage_report,
    generate_neft_report,
    generate_root_cause_report,
    generate_wallet_redeem_report,
)
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


# ── SESSION 2: Analysis Reports ───────────────────────────────────────────────

@router.get("/analysis/formula-components")
async def get_formula_components():
    """
    Returns the verified settlement formula and component dictionary.
    Source: leakage_engine.py module docstring (data-verified).
    """
    return {
        "formula": {
            "expected_net": [
                {"component": "sale_amount",           "sign": "+", "source": "settlements_etl"},
                {"component": "total_offer_amount",    "sign": "+", "source": "settlements_etl", "note": "Flipkart promotional subsidy"},
                {"component": "customer_addons_amount","sign": "+", "source": "settlements_etl"},
                {"component": "my_share",              "sign": "-", "source": "settlements_etl", "note": "Seller marketplace fee share"},
                {"component": "invoice_fee_total",     "sign": "-", "source": "fees_etl",        "note": "Sum of all non-Wallet-Redeem fees"},
                {"component": "invoice_gst_total",     "sign": "-", "source": "fees_etl",        "note": "GST on invoice fees"},
                {"component": "tcs",                   "sign": "-", "source": "settlements_etl", "note": "Tax Collected at Source (govt levy)"},
                {"component": "tds",                   "sign": "-", "source": "settlements_etl", "note": "Tax Deducted at Source (govt levy)"},
                {"component": "offer_adjustments",     "sign": "0", "source": "settlements_etl", "note": "All 0 in this dataset"},
                {"component": "protection_fund",       "sign": "0", "source": "settlements_etl", "note": "All 0 in this dataset"},
                {"component": "refund",                "sign": "-", "source": "settlements_etl", "note": "Return refunds to customers"},
            ],
            "difference": "settlement_amount − expected_net  (positive = OVER_PAID, negative = SHORT_PAID)",
        },
        "excluded_components": [
            {"component": "Wallet Redeem", "source": "fees_etl",
             "amount": -19983.84, "note": "Ad-spend deduction — requires separate bank reconciliation"},
        ],
        "data_summary": {
            "settled_orders":        927,
            "total_gmv":        191327.00,
            "total_fees":       -80187.20,
            "total_net_settled": 128295.29,
            "formula_verified_matched": 162,
        },
    }


@router.get("/analysis/root-cause")
async def get_root_cause_analysis(session: AsyncSession = Depends(get_session)):
    """100 random orders with full formula verification and root cause classification."""
    return await generate_root_cause_report(session)


@router.get("/analysis/neft-reconciliation")
async def get_neft_reconciliation(session: AsyncSession = Depends(get_session)):
    """NEFT-level grouping: sum of order settlements per NEFT transfer ID."""
    return await generate_neft_report(session)


@router.get("/analysis/leakage")
async def get_leakage_report(session: AsyncSession = Depends(get_session)):
    """Full leakage report with confidence scores for every order."""
    return await generate_leakage_report(session)


@router.get("/analysis/coverage")
async def get_coverage_report(session: AsyncSession = Depends(get_session)):
    """Fee invoice coverage audit — % of settlements with matching fee records."""
    return await generate_coverage_report(session)


@router.get("/analysis/wallet-redeem")
async def get_wallet_redeem_report(session: AsyncSession = Depends(get_session)):
    """Wallet Redeem audit — excluded from main reconciliation, needs bank reconciliation."""
    return await generate_wallet_redeem_report(session)


@router.get("/analysis/production-readiness")
async def get_production_readiness():
    """
    SESSION 2 Phase 10 — Production Readiness Assessment.
    Based on data audit of 970 order_financials records.
    """
    return {
        "architecture_review": {
            "status": "PASS",
            "engine": "SQLAlchemy async + PostgreSQL (asyncpg)",
            "deduplication": "DISTINCT ON (order_item_id) ORDER BY id ASC — correct",
            "formula": "Verified: expected = sale + offer + myshare + invoice_fees + govt_levies + refund",
            "tolerance": "Rs.2.00 match tolerance — appropriate for Flipkart settlement precision",
        },
        "performance_review": {
            "status": "WARNING",
            "current_throughput": "Sequential per-order reconciliation (reconcile_batch is a loop)",
            "bottleneck": "reconcile_batch calls reconcile_order_item sequentially — O(n) DB round trips",
            "recommendation": "Rewrite as single bulk upsert with all JOINs in SQL — expected 50-100x speedup",
        },
        "data_quality_review": {
            "status": "WARNING",
            "fee_coverage": "52.1% — only 483 of 927 settled orders have fee invoices",
            "duplicate_batches": "ETL tables have 5 duplicate batches — DISTINCT ON required (implemented)",
            "wallet_redeem": "Rs.19,983.84 Wallet Redeem in fees_etl excluded from reconciliation — correct, but needs separate cash audit",
            "my_share_unknown": "580 orders have my_share debit (Rs.14,430) — component not fully documented by Flipkart",
        },
        "finance_audit_review": {
            "status": "PASS",
            "formula_verified": "162 MATCHED orders — formula correct for clean deliveries",
            "true_leakage": "Rs.0 confirmed SHORT_PAID — no confirmed leakage in dataset",
            "over_paid": "434 orders (Rs.51,181 difference) — favorable for seller (fee waivers)",
            "return_recovery": "157 return orders correctly classified",
            "missing_settlement": "39 orders with fee invoice but no settlement — require follow-up",
        },
        "known_gaps": [
            "Bank statement not available — NEFT vs bank credit matching not possible",
            "Fee coverage 52.1% vs 99% target — 444 FEE_FREE orders need Flipkart clarification",
            "my_share column not documented in Flipkart API specs — assumed seller fee portion",
            "Wallet Redeem Rs.19,983.84 not reconciled against ad-spend invoices",
            "MISSING_SETTLEMENT orders (39): fee invoice shows deduction but no matching settlement row",
        ],
        "future_improvements": [
            "Bulk SQL reconciliation engine (10-50ms vs current 3-5s per batch)",
            "Bank statement upload and NEFT-bank matching",
            "Automated Wallet Redeem vs ad-spend reconciliation",
            "Historical trend analysis (multi-month data)",
            "Alert system for new SHORT_PAID orders in real-time",
            "SKU-level P&L incorporating all fee components",
        ],
    }


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
    total_overpaid = sum(
        abs(r.difference)
        for r in results
        if r.difference and r.reconciliation_status == ReconciliationStatus.OVER_PAID.value
    )

    return ReconciliationSummary(
        total_items=len(results),
        matched=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.MATCHED.value),
        short_paid=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.SHORT_PAID.value),
        over_paid=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.OVER_PAID.value),
        missing_settlement=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.MISSING_SETTLEMENT.value),
        missing_order=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.MISSING_ORDER.value),
        missing_fee_record=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.MISSING_FEE_RECORD.value),
        return_recovery=sum(1 for r in results if r.reconciliation_status == ReconciliationStatus.RETURN_RECOVERY.value),
        total_leakage=total_leakage or Decimal("0"),
        total_overpaid=total_overpaid or Decimal("0"),
    )
