"""
Payment Reconciliation Workbench — backend router.

Provides all APIs for the Payment Reconciliation Investigation Screen.
Every value is sourced from uploaded Flipkart reports stored in flipkart_recon DB.

Tables:
  settlements_etl   — PaymentReports_SettledTransactions upload (deduplicated by order_item_id)
  orders_etl        — Orders report upload
  fees_etl          — Commission / Invoice report upload
  order_financials  — Reconciled canonical record (output of reconcile engine)

No mock data. No hardcoded values. All numbers traceable to source rows.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db.flipkart_db import fk_session

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# KPI Cards — top-level summary
# ─────────────────────────────────────────────────────────────────────────────

_KPI_SQL = text("""
    WITH deduped AS (
        SELECT DISTINCT ON (order_item_id)
            neft_id, settlement_amount, order_item_id
        FROM settlements_etl
        WHERE is_valid = TRUE
          AND neft_id IS NOT NULL AND neft_id <> ''
        ORDER BY order_item_id, id ASC
    )
    SELECT
        COUNT(DISTINCT neft_id)                                  AS total_payments,
        COUNT(DISTINCT order_item_id)                            AS total_orders,
        COALESCE(SUM(settlement_amount), 0)                      AS total_settlement,
        (SELECT COUNT(*) FROM order_financials
         WHERE reconciliation_status = 'MATCHED')                AS matched_orders,
        (SELECT COUNT(*) FROM order_financials
         WHERE reconciliation_status = 'SHORT_PAID')             AS potential_leakage_count,
        (SELECT COALESCE(SUM(ABS(difference)), 0) FROM order_financials
         WHERE reconciliation_status = 'SHORT_PAID')             AS potential_leakage_amount,
        (SELECT COUNT(*) FROM order_financials
         WHERE reconciliation_status = 'MISSING_SETTLEMENT')     AS missing_settlements
    FROM deduped
""")


@router.get("/kpis")
async def get_kpis() -> dict[str, Any]:
    """
    KPI cards for the Payment Reconciliation page header.
    Source: settlements_etl (deduplicated) + order_financials (reconciliation counts).
    """
    async with fk_session() as db:
        row = (await db.execute(_KPI_SQL)).mappings().one()
    return {
        "total_payments":           int(row["total_payments"] or 0),
        "total_orders":             int(row["total_orders"] or 0),
        "total_settlement":         float(row["total_settlement"] or 0),
        "matched_orders":           int(row["matched_orders"] or 0),
        "potential_leakage_count":  int(row["potential_leakage_count"] or 0),
        "potential_leakage_amount": float(row["potential_leakage_amount"] or 0),
        "missing_settlements":      int(row["missing_settlements"] or 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Payment List
# ─────────────────────────────────────────────────────────────────────────────

_PAYMENTS_SQL = text("""
    WITH deduped AS (
        SELECT DISTINCT ON (order_item_id)
            neft_id,
            settlement_date,
            order_item_id,
            settlement_amount
        FROM settlements_etl
        WHERE is_valid = TRUE
          AND neft_id IS NOT NULL AND neft_id <> ''
        ORDER BY order_item_id, id ASC
    )
    SELECT
        d.neft_id                               AS payment_id,
        MAX(d.settlement_date)                  AS settlement_date,
        COUNT(DISTINCT d.order_item_id)         AS order_count,
        COALESCE(SUM(d.settlement_amount), 0)   AS total_settlement_amount,
        -- reconciliation summary for this NEFT batch
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'MATCHED')             AS matched,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'SHORT_PAID')          AS short_paid,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'OVER_PAID')           AS over_paid,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'MISSING_SETTLEMENT')  AS missing_settlement,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'RETURN_RECOVERY')     AS return_recovery
    FROM deduped d
    LEFT JOIN order_financials of ON of.order_item_id = d.order_item_id
    GROUP BY d.neft_id
    ORDER BY MAX(d.settlement_date) DESC, d.neft_id
""")

_PAYMENTS_SEARCH_SQL = text("""
    WITH deduped AS (
        SELECT DISTINCT ON (order_item_id)
            neft_id,
            settlement_date,
            order_item_id,
            settlement_amount
        FROM settlements_etl
        WHERE is_valid = TRUE
          AND neft_id IS NOT NULL AND neft_id <> ''
          AND neft_id ILIKE :q
        ORDER BY order_item_id, id ASC
    )
    SELECT
        d.neft_id                               AS payment_id,
        MAX(d.settlement_date)                  AS settlement_date,
        COUNT(DISTINCT d.order_item_id)         AS order_count,
        COALESCE(SUM(d.settlement_amount), 0)   AS total_settlement_amount,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'MATCHED')             AS matched,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'SHORT_PAID')          AS short_paid,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'OVER_PAID')           AS over_paid,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'MISSING_SETTLEMENT')  AS missing_settlement,
        COUNT(of.reconciliation_status) FILTER (WHERE of.reconciliation_status = 'RETURN_RECOVERY')     AS return_recovery
    FROM deduped d
    LEFT JOIN order_financials of ON of.order_item_id = d.order_item_id
    GROUP BY d.neft_id
    ORDER BY MAX(d.settlement_date) DESC, d.neft_id
""")


def _payment_row(r) -> dict[str, Any]:
    matched     = int(r["matched"] or 0)
    short_paid  = int(r["short_paid"] or 0)
    over_paid   = int(r["over_paid"] or 0)
    missing     = int(r["missing_settlement"] or 0)
    returns     = int(r["return_recovery"] or 0)
    order_count = int(r["order_count"] or 0)

    if short_paid > 0:
        status = "SHORT_PAID"
    elif missing > 0:
        status = "MISSING_SETTLEMENT"
    elif matched == order_count and order_count > 0:
        status = "MATCHED"
    elif over_paid > 0:
        status = "OVER_PAID"
    else:
        status = "PARTIAL"

    return {
        "payment_id":              r["payment_id"],
        "settlement_date":         str(r["settlement_date"]) if r["settlement_date"] else None,
        "order_count":             order_count,
        "total_settlement_amount": float(r["total_settlement_amount"] or 0),
        "status":                  status,
        "reconciliation_summary": {
            "matched":            matched,
            "short_paid":         short_paid,
            "over_paid":          over_paid,
            "missing_settlement": missing,
            "return_recovery":    returns,
        },
    }


@router.get("/payments")
async def list_payments(
    search: str | None = Query(None, description="Filter by payment ID (partial match)"),
    date_from: str | None = Query(None, description="Filter settlement_date >= YYYY-MM-DD"),
    date_to:   str | None = Query(None, description="Filter settlement_date <= YYYY-MM-DD"),
) -> list[dict[str, Any]]:
    """
    Phase 2: Payment List API.
    Lists all NEFT payments from settlements_etl, deduplicated and grouped.
    Source: settlements_etl → DISTINCT ON order_item_id → GROUP BY neft_id.
    """
    async with fk_session() as db:
        if search:
            rows = (await db.execute(_PAYMENTS_SEARCH_SQL, {"q": f"%{search}%"})).mappings().all()
        else:
            rows = (await db.execute(_PAYMENTS_SQL)).mappings().all()

    result = [_payment_row(r) for r in rows]

    if date_from:
        result = [p for p in result if p["settlement_date"] and p["settlement_date"] >= date_from]
    if date_to:
        result = [p for p in result if p["settlement_date"] and p["settlement_date"] <= date_to]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 + 4 — Payment Detail with Order Grid
# ─────────────────────────────────────────────────────────────────────────────

_PAYMENT_HEADER_SQL = text("""
    WITH deduped AS (
        SELECT DISTINCT ON (order_item_id)
            neft_id, settlement_date, order_item_id, settlement_amount
        FROM settlements_etl
        WHERE is_valid = TRUE AND neft_id = :payment_id
        ORDER BY order_item_id, id ASC
    )
    SELECT
        neft_id                               AS payment_id,
        MAX(settlement_date)                  AS settlement_date,
        COUNT(DISTINCT order_item_id)         AS total_orders,
        COALESCE(SUM(settlement_amount), 0)   AS total_settlement
    FROM deduped
    GROUP BY neft_id
""")

_PAYMENT_ORDERS_SQL = text("""
    WITH deduped_s AS (
        SELECT DISTINCT ON (order_item_id)
            order_item_id, order_id, sku, sale_amount, settlement_amount
        FROM settlements_etl
        WHERE is_valid = TRUE AND neft_id = :payment_id
        ORDER BY order_item_id, id ASC
    ),
    deduped_o AS (
        SELECT DISTINCT ON (order_item_id)
            order_item_id, product_title
        FROM orders_etl
        WHERE is_valid = TRUE
        ORDER BY order_item_id, id ASC
    )
    SELECT
        s.order_item_id,
        s.order_id,
        s.sku,
        COALESCE(of.product_title, o.product_title)   AS product_title,
        s.sale_amount                                   AS selling_price,
        of.expected_settlement,
        s.settlement_amount                             AS actual_settlement,
        of.difference,
        of.reconciliation_status                        AS status
    FROM deduped_s s
    LEFT JOIN order_financials of ON of.order_item_id = s.order_item_id
    LEFT JOIN deduped_o o          ON o.order_item_id  = s.order_item_id
    ORDER BY s.order_item_id
""")


@router.get("/payment/{payment_id:path}")
async def get_payment_detail(payment_id: str) -> dict[str, Any]:
    """
    Phase 3 + 4: Payment Detail API.
    Returns header summary and full order grid for one NEFT payment.
    Sources: settlements_etl + order_financials + orders_etl.
    """
    async with fk_session() as db:
        header = (await db.execute(_PAYMENT_HEADER_SQL, {"payment_id": payment_id})).mappings().one_or_none()
        if not header or header["payment_id"] is None:
            raise HTTPException(404, f"Payment '{payment_id}' not found in settlements_etl")
        order_rows = (await db.execute(_PAYMENT_ORDERS_SQL, {"payment_id": payment_id})).mappings().all()

    orders = [
        {
            "order_item_id":    r["order_item_id"],
            "order_id":         r["order_id"],
            "sku":              r["sku"],
            "product_title":    r["product_title"],
            "selling_price":    float(r["selling_price"] or 0),
            "expected_settlement": float(r["expected_settlement"]) if r["expected_settlement"] is not None else None,
            "actual_settlement": float(r["actual_settlement"] or 0),
            "difference":       float(r["difference"]) if r["difference"] is not None else None,
            "status":           r["status"],
        }
        for r in order_rows
    ]

    return {
        "payment_id":       header["payment_id"],
        "settlement_date":  str(header["settlement_date"]) if header["settlement_date"] else None,
        "total_orders":     int(header["total_orders"] or 0),
        "total_settlement": float(header["total_settlement"] or 0),
        "orders":           orders,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Order Timeline
# ─────────────────────────────────────────────────────────────────────────────

_TIMELINE_SQL = text("""
    WITH ords AS (
        SELECT DISTINCT ON (order_item_id)
            order_item_id, order_date, dispatch_date, delivery_date, order_item_status
        FROM orders_etl
        WHERE order_item_id = :oid AND is_valid = TRUE
        ORDER BY order_item_id, id ASC
    ),
    setts AS (
        SELECT DISTINCT ON (order_item_id)
            order_item_id, settlement_date, neft_id
        FROM settlements_etl
        WHERE order_item_id = :oid AND is_valid = TRUE
        ORDER BY order_item_id, id ASC
    ),
    fins AS (
        SELECT order_date, delivery_date, settlement_date, neft_id
        FROM order_financials
        WHERE order_item_id = :oid
        LIMIT 1
    )
    SELECT
        COALESCE(o.order_date,      f.order_date)      AS order_date,
        o.dispatch_date,
        COALESCE(o.delivery_date,   f.delivery_date)   AS delivery_date,
        o.order_item_status,
        COALESCE(s.settlement_date, f.settlement_date) AS settlement_date,
        COALESCE(s.neft_id,         f.neft_id)         AS neft_id
    FROM ords o
    FULL JOIN setts s ON TRUE
    FULL JOIN fins  f ON TRUE
""")


@router.get("/order/{order_item_id}/timeline")
async def get_order_timeline(order_item_id: str) -> dict[str, Any]:
    """
    Phase 5: Order Timeline API.
    Builds chronological event list from all available timestamps.
    Sources: orders_etl (order/dispatch/delivery) + settlements_etl (settlement) + order_financials (fallback).
    """
    async with fk_session() as db:
        row = (await db.execute(_TIMELINE_SQL, {"oid": order_item_id})).mappings().one_or_none()

    if not row:
        raise HTTPException(404, f"Order item '{order_item_id}' not found")

    events: list[dict] = []

    if row["order_date"]:
        events.append({
            "event": "ORDER_CREATED",
            "timestamp": str(row["order_date"]),
            "source": "orders_etl.order_date",
        })
    if row["dispatch_date"]:
        events.append({
            "event": "DISPATCHED",
            "timestamp": str(row["dispatch_date"]),
            "source": "orders_etl.dispatch_date",
        })
    if row["delivery_date"]:
        events.append({
            "event": "DELIVERED",
            "timestamp": str(row["delivery_date"]),
            "source": "orders_etl.delivery_date",
        })
    if row["settlement_date"]:
        events.append({
            "event": "SETTLED",
            "timestamp": str(row["settlement_date"]),
            "source": "settlements_etl.settlement_date",
            "payment_id": row["neft_id"],
        })

    status = row["order_item_status"]
    if status:
        s_upper = status.upper()
        if s_upper in (
            "RETURNED", "CANCELLED", "RETURN_REQUESTED",
            "RETURN_COMPLETED", "REFUNDED", "RETURN_INITIATED",
        ):
            events.append({
                "event": s_upper,
                "timestamp": None,
                "source": "orders_etl.order_item_status",
            })

    events.sort(key=lambda e: e["timestamp"] or "9999")

    return {
        "order_item_id":  order_item_id,
        "current_status": status,
        "payment_id":     row["neft_id"],
        "events":         events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Order Financial Breakdown
# ─────────────────────────────────────────────────────────────────────────────

_FINANCIALS_SQL = text("""
    SELECT
        of.sale_amount, of.total_offer_amount, of.my_share,
        of.marketplace_fee, of.tcs, of.tds, of.gst_on_mp_fees, of.refund,
        of.invoice_fee_total, of.invoice_gst_total,
        of.commission_fee, of.shipping_fee, of.other_fee,
        of.settlement_amount, of.expected_settlement, of.difference,
        of.reconciliation_status, of.order_date, of.settlement_date,
        of.neft_id, of.product_title, of.sku
    FROM order_financials of
    WHERE of.order_item_id = :oid
""")

_FEE_LINES_SQL = text("""
    SELECT DISTINCT ON (fee_name)
        fee_name, fee_amount, fee_waiver_amount,
        cgst, sgst, igst, tax_amount, fee_date
    FROM fees_etl
    WHERE order_item_id = :oid AND is_valid = TRUE
    ORDER BY fee_name, id ASC
""")


@router.get("/order/{order_item_id}/financials")
async def get_order_financials(order_item_id: str) -> dict[str, Any]:
    """
    Phase 6: Order Financial Breakdown API.
    Full formula components, invoice lines, and reconciliation result.
    Sources: order_financials (reconciled totals) + fees_etl (invoice line items).
    """
    async with fk_session() as db:
        of_row   = (await db.execute(_FINANCIALS_SQL, {"oid": order_item_id})).mappings().one_or_none()
        fee_rows = (await db.execute(_FEE_LINES_SQL,  {"oid": order_item_id})).mappings().all()

    if not of_row:
        raise HTTPException(404, f"Order item '{order_item_id}' not found in reconciled data")

    def _f(v) -> float | None:
        return float(v) if v is not None else None

    return {
        "order_item_id":   order_item_id,
        "sku":             of_row["sku"],
        "product_title":   of_row["product_title"],
        "order_date":      str(of_row["order_date"])      if of_row["order_date"]      else None,
        "settlement_date": str(of_row["settlement_date"]) if of_row["settlement_date"] else None,
        "payment_id":      of_row["neft_id"],
        "status":          of_row["reconciliation_status"],

        # Raw components from settlements_etl (via reconciler)
        "formula_components": {
            "sale_amount":        _f(of_row["sale_amount"]),
            "total_offer_amount": _f(of_row["total_offer_amount"]),
            "my_share":           _f(of_row["my_share"]),
            "marketplace_fee":    _f(of_row["marketplace_fee"]),
            "tcs":                _f(of_row["tcs"]),
            "tds":                _f(of_row["tds"]),
            "gst_on_mp_fees":     _f(of_row["gst_on_mp_fees"]),
            "refund":             _f(of_row["refund"]),
        },

        # Invoice cross-check from fees_etl
        "invoice_breakdown": {
            "invoice_fee_total": _f(of_row["invoice_fee_total"]),
            "invoice_gst_total": _f(of_row["invoice_gst_total"]),
            "commission_fee":    _f(of_row["commission_fee"]),
            "shipping_fee":      _f(of_row["shipping_fee"]),
            "other_fee":         _f(of_row["other_fee"]),
            "fee_lines": [
                {
                    "fee_name":    r["fee_name"],
                    "fee_amount":  _f(r["fee_amount"]),
                    "fee_waiver":  _f(r["fee_waiver_amount"]),
                    "cgst":        _f(r["cgst"]),
                    "sgst":        _f(r["sgst"]),
                    "igst":        _f(r["igst"]),
                    "tax_amount":  _f(r["tax_amount"]),
                    "fee_date":    str(r["fee_date"]) if r["fee_date"] else None,
                }
                for r in fee_rows
            ],
        },

        # Reconciliation result
        "reconciliation": {
            "selling_price":       _f(of_row["sale_amount"]),
            "actual_settlement":   _f(of_row["settlement_amount"]),
            "expected_settlement": _f(of_row["expected_settlement"]),
            "difference":          _f(of_row["difference"]),
            "status":              of_row["reconciliation_status"],
            "formula": (
                "expected = sale_amount + total_offer_amount + my_share "
                "+ invoice_fee_total + invoice_gst_total + tcs + tds + refund"
            ),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Debug / Source Data
# ─────────────────────────────────────────────────────────────────────────────

_DBG_ORDERS_SQL = text("""
    SELECT id, batch_id::text, raw_id, order_item_id, order_id, sku, product_title,
           quantity,
           order_date::text, dispatch_date::text, delivery_date::text,
           order_item_status, is_valid, created_at::text
    FROM orders_etl
    WHERE order_item_id = :oid
    ORDER BY id ASC
""")

_DBG_FEES_SQL = text("""
    SELECT id, batch_id::text, raw_id, order_item_id, fee_name,
           fee_amount::float8, fee_waiver_amount::float8,
           cgst::float8, sgst::float8, igst::float8, tax_amount::float8,
           fee_date::text, is_valid, created_at::text
    FROM fees_etl
    WHERE order_item_id = :oid
    ORDER BY id ASC
""")

_DBG_SETTLEMENTS_SQL = text("""
    SELECT id, batch_id::text, raw_id, neft_id, neft_type,
           settlement_date::text, settlement_amount::float8,
           order_id, order_item_id,
           sale_amount::float8, total_offer_amount::float8, my_share::float8,
           customer_addons_amount::float8, marketplace_fee::float8,
           offer_adjustments::float8, protection_fund::float8, refund::float8,
           tcs::float8, tds::float8, gst_on_mp_fees::float8,
           fixed_fee::float8, collection_fee::float8, reverse_shipping_fee::float8,
           sku, fsn, is_valid, created_at::text
    FROM settlements_etl
    WHERE order_item_id = :oid
    ORDER BY id ASC
""")

_DBG_FINANCIALS_SQL = text("""
    SELECT id, order_item_id, order_id, neft_id, neft_type, sku, fsn, product_title,
           order_date::text, delivery_date::text, settlement_date::text,
           sale_amount::float8, total_offer_amount::float8, my_share::float8,
           marketplace_fee::float8, tcs::float8, tds::float8,
           gst_on_mp_fees::float8, refund::float8,
           invoice_fee_total::float8, invoice_gst_total::float8,
           commission_fee::float8, shipping_fee::float8, other_fee::float8,
           settlement_amount::float8, expected_settlement::float8, difference::float8,
           reconciliation_status, last_reconciled_at::text, created_at::text
    FROM order_financials
    WHERE order_item_id = :oid
""")


@router.get("/order/{order_item_id}/debug")
async def get_order_debug(order_item_id: str) -> dict[str, Any]:
    """
    Phase 7: Source Data / Debug Mode.
    Exposes every raw ETL row for this order_item_id across all tables.
    Use batch_id + raw_id to trace any value back to the uploaded source file row.
    Sources: orders_etl + fees_etl + settlements_etl + order_financials (ALL batches, not deduplicated).
    """
    async with fk_session() as db:
        o_rows  = (await db.execute(_DBG_ORDERS_SQL,      {"oid": order_item_id})).mappings().all()
        f_rows  = (await db.execute(_DBG_FEES_SQL,        {"oid": order_item_id})).mappings().all()
        s_rows  = (await db.execute(_DBG_SETTLEMENTS_SQL, {"oid": order_item_id})).mappings().all()
        fin_row = (await db.execute(_DBG_FINANCIALS_SQL,  {"oid": order_item_id})).mappings().one_or_none()

    if not o_rows and not f_rows and not s_rows and not fin_row:
        raise HTTPException(404, f"Order item '{order_item_id}' not found in any ETL table")

    def _m(row) -> dict:
        return {k: v for k, v in row.items()}

    return {
        "order_item_id": order_item_id,
        "traceability": {
            "orders_etl_rows":      len(o_rows),
            "fees_etl_rows":        len(f_rows),
            "settlements_etl_rows": len(s_rows),
            "has_financials":       fin_row is not None,
            "deduplication_note":   (
                "Multiple rows per order_item_id are expected (5 batches uploaded). "
                "The canonical record uses the row with the lowest id in each table."
            ),
        },
        "sources": {
            "orders_etl":       [_m(r) for r in o_rows],
            "fees_etl":         [_m(r) for r in f_rows],
            "settlements_etl":  [_m(r) for r in s_rows],
            "order_financials": _m(fin_row) if fin_row else None,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Global Search
# ─────────────────────────────────────────────────────────────────────────────

_SEARCH_SQL = text("""
    WITH results AS (
        -- Match on order_item_id, order_id, sku, product_title
        SELECT
            of.order_item_id,
            of.order_id,
            of.sku,
            of.product_title,
            of.sale_amount::float8          AS selling_price,
            of.settlement_amount::float8    AS settlement_amount,
            of.reconciliation_status        AS status,
            of.difference::float8,
            of.neft_id                      AS payment_id,
            of.settlement_date::text
        FROM order_financials of
        WHERE
            of.order_item_id ILIKE :q
            OR of.order_id    ILIKE :q
            OR of.sku         ILIKE :q
            OR of.product_title ILIKE :q
        LIMIT :lim
    )
    SELECT * FROM results
    ORDER BY order_item_id
""")


@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, description="Search term: payment ID, order ID, order item ID, SKU, or product"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """
    Global search across order_financials + NEFT payment match.
    Source: order_financials (all reconciled records).
    """
    async with fk_session() as db:
        order_rows = (await db.execute(_SEARCH_SQL, {"q": f"%{q}%", "lim": limit})).mappings().all()

        # Also search payments (NEFT IDs)
        payment_rows = (await db.execute(
            text("""
                SELECT DISTINCT neft_id AS payment_id, MAX(settlement_date)::text AS settlement_date,
                       COUNT(DISTINCT order_item_id) AS order_count
                FROM settlements_etl
                WHERE is_valid = TRUE AND neft_id ILIKE :q
                GROUP BY neft_id
                ORDER BY neft_id
                LIMIT :lim
            """),
            {"q": f"%{q}%", "lim": 20},
        )).mappings().all()

    return {
        "query": q,
        "payments": [
            {
                "payment_id":    r["payment_id"],
                "settlement_date": r["settlement_date"],
                "order_count":   int(r["order_count"]),
            }
            for r in payment_rows
        ],
        "orders": [
            {
                "order_item_id":    r["order_item_id"],
                "order_id":         r["order_id"],
                "sku":              r["sku"],
                "product_title":    r["product_title"],
                "selling_price":    r["selling_price"],
                "settlement_amount": r["settlement_amount"],
                "status":           r["status"],
                "difference":       r["difference"],
                "payment_id":       r["payment_id"],
                "settlement_date":  r["settlement_date"],
            }
            for r in order_rows
        ],
        "total_orders_found": len(order_rows),
        "total_payments_found": len(payment_rows),
    }
