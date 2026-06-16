"""
flipkart_queries.py — All read queries against the flipkart_recon database.

SOURCE TABLES
─────────────
order_financials   970 rows   reconciled output (unique per order_item_id)
orders_etl         3105 rows  5 duplicate batches × 621; deduplicated via DISTINCT ON
fees_etl           3295 rows  5 duplicate batches × 659; deduplicated via DISTINCT ON
settlements_etl    3408 rows  5 April×529 + 1 May×763;  deduplicated via DISTINCT ON

DEDUPLICATION STRATEGY
──────────────────────
All ETL tables have duplicate batches from multiple uploads.
We use DISTINCT ON (order_item_id [, fee_name]) ORDER BY id ASC to pick the
first-ingested row per order, giving a clean deduplicated view.

DATA TRACEABILITY
─────────────────
Dashboard → Total GMV        : SELECT SUM(sale_amount)        FROM order_financials
Dashboard → Total Fees       : SELECT SUM(invoice_fee_total + invoice_gst_total) FROM order_financials
Dashboard → Settlement Amount: SELECT SUM(settlement_amount)  FROM order_financials
Dashboard → Matched Orders   : SELECT COUNT(*) FILTER status='MATCHED' FROM order_financials
Settlements → per NEFT ID    : settlements_etl grouped by neft_id (DISTINCT ON order_item_id)
Commission → fee_name        : fees_etl DISTINCT ON (order_item_id, fee_name)
GST → tcs/tds/gst            : settlements_etl DISTINCT ON order_item_id, summed
Returns → RETURNED orders    : orders_etl DISTINCT ON order_item_id WHERE status='RETURNED'

SOURCE FILES (uploaded by user)
────────────────────────────────
order_financials  ← reconciler output from all three files below
orders_etl        ← FulfilmentReports_Orders.xlsx
fees_etl          ← Invoices_CommissionInvoiceTransactionDetails.xlsx
settlements_etl   ← PaymentReports_SettledTransactions.xlsx
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _f(v) -> float:
    """Safe Decimal / None → float."""
    return float(v or 0)


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

_DASHBOARD_SQL = text("""
    SELECT
        COUNT(*)                                                          AS total_records,
        COALESCE(SUM(sale_amount), 0)                                    AS total_gmv,
        COALESCE(SUM(
            COALESCE(invoice_fee_total, 0) + COALESCE(invoice_gst_total, 0)
        ), 0)                                                             AS total_fees,
        COALESCE(SUM(expected_settlement), 0)                            AS total_expected,
        COALESCE(SUM(settlement_amount), 0)                              AS total_actual,
        COALESCE(SUM(difference), 0)                                     AS total_difference,
        COUNT(*) FILTER (WHERE reconciliation_status = 'MATCHED')        AS matched,
        COUNT(*) FILTER (WHERE reconciliation_status = 'SHORT_PAID')     AS short_paid,
        COUNT(*) FILTER (WHERE reconciliation_status = 'OVER_PAID')      AS over_paid,
        COUNT(*) FILTER (WHERE reconciliation_status = 'MISSING_SETTLEMENT') AS missing_settlement,
        COUNT(*) FILTER (WHERE reconciliation_status = 'RETURN_RECOVERY') AS return_recovery,
        COUNT(*) FILTER (WHERE reconciliation_status = 'MISSING_FEE_RECORD') AS missing_fee_record,
        COUNT(*) FILTER (WHERE reconciliation_status = 'MISSING_ORDER')  AS missing_order,
        COALESCE(SUM(expected_settlement)
            FILTER (WHERE reconciliation_status = 'MISSING_SETTLEMENT'), 0) AS pending_amount
    FROM order_financials
""")

_TREND_SQL = text("""
    SELECT
        TO_CHAR(DATE_TRUNC('month', order_date), 'YYYY-MM-DD') AS period,
        COALESCE(SUM(sale_amount), 0)                          AS gross,
        COALESCE(SUM(settlement_amount), 0)                    AS net
    FROM order_financials
    WHERE order_date IS NOT NULL
    GROUP BY DATE_TRUNC('month', order_date)
    ORDER BY DATE_TRUNC('month', order_date)
""")


async def get_dashboard_summary(db: AsyncSession) -> dict:
    """
    SQL source: order_financials
    Returns all KPIs for the Dashboard page.
    """
    row = (await db.execute(_DASHBOARD_SQL)).mappings().one()
    trend_rows = (await db.execute(_TREND_SQL)).mappings().all()

    total        = int(row["total_records"])
    matched      = int(row["matched"])
    short_paid   = int(row["short_paid"])
    over_paid    = int(row["over_paid"])
    miss_settle  = int(row["missing_settlement"])
    return_rec   = int(row["return_recovery"])
    miss_fee     = int(row["missing_fee_record"])
    miss_order   = int(row["missing_order"])

    closed_count = matched + over_paid + return_rec
    open_count   = miss_settle
    processing   = miss_fee + miss_order

    gmv          = _f(row["total_gmv"])
    fees         = _f(row["total_fees"])   # already negative
    actual       = _f(row["total_actual"])
    pending_amt  = _f(row["pending_amount"])
    variance     = _f(row["total_difference"])

    unresolved   = miss_settle + miss_order + short_paid

    trend = [
        {"date": r["period"], "gross": _f(r["gross"]), "net": _f(r["net"])}
        for r in trend_rows
    ]

    return {
        "settlements": {
            "total":            total,
            "closed_count":     closed_count,
            "open_count":       open_count,
            "processing_count": processing,
            "total_gross":      gmv,
            "total_fees":       fees,
            "total_net_paid":   actual,
            "pending_amount":   pending_amt,
            "total_orders":     total,
        },
        "payouts": {
            "transferred": actual,
            "pending":     pending_amt,
            "failed":      0.0,
        },
        "reconciliation": {
            "clean":                   matched,
            "warning":                 over_paid,
            "critical":                short_paid,
            "error":                   miss_fee + miss_order,
            "total_runs":              total,
            "unresolved_discrepancies": unresolved,
            "total_variance":          variance,
        },
        "revenue_trend":  trend,
        "platform_share": [
            {"platform": "flipkart", "label": "Flipkart", "share_pct": 100.0}
        ],
    }


# ── SETTLEMENTS ───────────────────────────────────────────────────────────────

_SETTLEMENTS_SQL = text("""
    WITH deduped AS (
        SELECT DISTINCT ON (order_item_id)
            neft_id,
            neft_type,
            settlement_date,
            order_item_id,
            order_id,
            sku,
            sale_amount,
            COALESCE(marketplace_fee, 0)        AS marketplace_fee,
            COALESCE(tcs, 0)                    AS tcs,
            COALESCE(tds, 0)                    AS tds,
            COALESCE(gst_on_mp_fees, 0)         AS gst_on_mp_fees,
            COALESCE(refund, 0)                 AS refund,
            COALESCE(offer_adjustments, 0)      AS offer_adjustments,
            COALESCE(protection_fund, 0)        AS protection_fund,
            settlement_amount
        FROM settlements_etl
        WHERE is_valid = true
        ORDER BY order_item_id, id ASC
    )
    SELECT
        COALESCE(neft_id, 'NEFT-' || MIN(order_item_id))  AS settlement_id,
        TO_CHAR(MIN(settlement_date), 'Mon YYYY')          AS period,
        MIN(settlement_date)                               AS settlement_date,
        COALESCE(SUM(sale_amount), 0)                      AS base,
        ABS(COALESCE(SUM(marketplace_fee), 0))             AS comm,
        ABS(COALESCE(SUM(tcs), 0))                        AS tcs,
        ABS(COALESCE(SUM(tds), 0))                        AS tds,
        ABS(COALESCE(SUM(refund), 0))                     AS ret,
        0                                                  AS pen,
        COALESCE(SUM(settlement_amount), 0)                AS net,
        COUNT(*)                                           AS orders,
        COUNT(*)                                           AS inv
    FROM deduped
    WHERE neft_id IS NOT NULL
    GROUP BY neft_id
    ORDER BY MIN(settlement_date) DESC
""")

_SETTLEMENTS_SUMMARY_SQL = text("""
    WITH deduped AS (
        SELECT DISTINCT ON (order_item_id)
            settlement_amount,
            reconciliation_status
        FROM order_financials
        ORDER BY order_item_id, id ASC
    )
    SELECT
        COALESCE(SUM(CASE WHEN reconciliation_status IN ('MATCHED','OVER_PAID','RETURN_RECOVERY')
                     THEN settlement_amount ELSE 0 END), 0)           AS total_net,
        COALESCE(SUM(CASE WHEN reconciliation_status = 'MISSING_SETTLEMENT'
                     THEN expected_settlement ELSE 0 END), 0)         AS pending_net,
        0                                                              AS total_penalties
    FROM order_financials
""")


async def get_settlements(db: AsyncSession) -> dict:
    """
    SQL source: settlements_etl (DISTINCT ON order_item_id), grouped by neft_id.
    Summary from: order_financials.
    """
    rows = (await db.execute(_SETTLEMENTS_SQL)).mappings().all()

    # Summary from order_financials
    s_row = (await db.execute(text("""
        SELECT
            COALESCE(SUM(settlement_amount)
                FILTER (WHERE reconciliation_status IN
                    ('MATCHED','OVER_PAID','RETURN_RECOVERY')), 0)     AS total_net,
            COALESCE(SUM(expected_settlement)
                FILTER (WHERE reconciliation_status = 'MISSING_SETTLEMENT'), 0) AS pending_net
        FROM order_financials
    """))).mappings().one()

    items = []
    for r in rows:
        net = _f(r["net"])
        items.append({
            "id":        r["settlement_id"],
            "plat":      "Flipkart",
            "icon":      "🛍️",
            "period":    r["period"],
            "base":      _f(r["base"]),
            "comm":      _f(r["comm"]),
            "logi":      0.0,
            "ret":       _f(r["ret"]),
            "tcs":       _f(r["tcs"]),
            "pen":       0.0,
            "net":       net,
            "status":    "paid" if net > 0 else "pending",
            "orders":    int(r["orders"]),
            "inv":       int(r["inv"]),
            "paid_date": str(r["settlement_date"]) if r["settlement_date"] else None,
        })

    total_net  = _f(s_row["total_net"])
    pending    = _f(s_row["pending_net"])

    return {
        "items": items,
        "summary": {
            "total_net":       total_net,
            "pending_net":     pending,
            "total_penalties": 0.0,
        },
    }


# ── COMMISSION ────────────────────────────────────────────────────────────────

_COMMISSION_SQL = text("""
    WITH deduped_fees AS (
        SELECT DISTINCT ON (order_item_id, fee_name)
            order_item_id,
            fee_name,
            COALESCE(fee_amount, 0)       AS fee_amount,
            COALESCE(fee_waiver_amount, 0) AS fee_waiver_amount,
            COALESCE(tax_amount, 0)        AS tax_amount
        FROM fees_etl
        WHERE is_valid = true
        ORDER BY order_item_id, fee_name, id ASC
    ),
    order_sale AS (
        SELECT DISTINCT ON (order_item_id)
            order_item_id,
            sku,
            product_title,
            sale_amount
        FROM order_financials
        ORDER BY order_item_id, id ASC
    ),
    joined AS (
        SELECT
            f.fee_name,
            o.sku,
            o.product_title,
            o.sale_amount,
            f.fee_amount,
            f.fee_waiver_amount,
            f.tax_amount
        FROM deduped_fees f
        LEFT JOIN order_sale o USING (order_item_id)
    )
    SELECT
        fee_name,
        COALESCE(sku, 'UNKNOWN')           AS sku,
        COALESCE(product_title, 'Product') AS product_title,
        COUNT(*)                           AS orders,
        SUM(ABS(sale_amount))              AS total_sale,
        SUM(ABS(fee_amount))               AS total_fee,
        SUM(ABS(tax_amount))               AS total_tax
    FROM joined
    GROUP BY fee_name, sku, product_title
    ORDER BY SUM(ABS(fee_amount)) DESC NULLS LAST
    LIMIT 100
""")

_FLIPKART_COMMISSION_RATE = 12.0   # published Flipkart referral rate


async def get_commission_data(db: AsyncSession) -> dict:
    """
    SQL source: fees_etl (DISTINCT ON order_item_id, fee_name) joined with orders_etl.
    Computes effective commission rate vs published 12% Flipkart rate.
    """
    rows = (await db.execute(_COMMISSION_SQL)).mappings().all()

    items = []
    total_overcharge = 0.0
    flagged_count    = 0
    affected_orders  = 0

    for r in rows:
        total_fee  = _f(r["total_fee"])
        total_sale = _f(r["total_sale"])
        orders     = int(r["orders"])
        fee_name   = r["fee_name"] or "Fee"

        chg_rate = round(total_fee / total_sale * 100, 2) if total_sale > 0 else 0.0
        pub_rate = _FLIPKART_COMMISSION_RATE
        overcharge = max(0.0, round(total_fee - (total_sale * pub_rate / 100), 2))
        flag = chg_rate > pub_rate and total_sale > 0

        if flag:
            total_overcharge += overcharge
            flagged_count    += 1
            affected_orders  += orders

        items.append({
            "plat":         "Flipkart",
            "icon":         "🛍️",
            "sku":          r["sku"],
            "prod":         r["product_title"],
            "cat":          fee_name,
            "pub":          pub_rate,
            "chg":          chg_rate,
            "orders":       orders,
            "expected_fee": round(total_sale * pub_rate / 100, 2),
            "charged_fee":  total_fee,
            "overcharge":   overcharge,
            "flag":         flag,
        })

    return {
        "items": items,
        "summary": {
            "total_overcharge": round(total_overcharge, 2),
            "flagged_count":    flagged_count,
            "affected_orders":  affected_orders,
        },
    }


# ── RETURNS ───────────────────────────────────────────────────────────────────

_RETURNS_SQL = text("""
    SELECT DISTINCT ON (order_item_id)
        order_item_id,
        order_id,
        sku,
        product_title,
        order_date,
        order_item_status,
        delivery_date
    FROM orders_etl
    WHERE is_valid = true
      AND order_item_status IN ('RETURNED', 'RETURN_REQUESTED')
    ORDER BY order_item_id, id ASC
""")

_RETURNS_REFUND_SQL = text("""
    SELECT DISTINCT ON (order_item_id)
        order_item_id,
        COALESCE(ABS(refund), 0) AS refund_amount
    FROM settlements_etl
    WHERE is_valid = true
    ORDER BY order_item_id, id ASC
""")


async def get_returns_data(db: AsyncSession) -> dict:
    """
    SQL source: orders_etl (DISTINCT ON order_item_id WHERE status=RETURNED)
    joined with settlements_etl for refund amounts.
    """
    ret_rows = (await db.execute(_RETURNS_SQL)).mappings().all()
    ref_rows = (await db.execute(_RETURNS_REFUND_SQL)).mappings().all()

    refund_map = {r["order_item_id"]: _f(r["refund_amount"]) for r in ref_rows}

    items = []
    total_deducted = 0.0
    by_reason: dict[str, int] = {"RETURNED": 0, "RETURN_REQUESTED": 0}

    for idx, r in enumerate(ret_rows, start=1):
        oid    = r["order_item_id"]
        status = r["order_item_status"] or "RETURNED"
        amount = refund_map.get(oid, 0.0)
        total_deducted += amount
        by_reason[status] = by_reason.get(status, 0) + 1

        items.append({
            "id":           f"RET-{idx:04d}",
            "tx_id":        oid,
            "plat":         "Flipkart",
            "platform_raw": "flipkart",
            "icon":         "🛍️",
            "oid":          r["order_id"] or "",
            "sku":          r["sku"] or "",
            "prod":         r["product_title"] or r["sku"] or "Product",
            "reason":       "Return",
            "qty":          1,
            "base":         amount,
            "ship":         0.0,
            "total":        amount,
            "date":         str(r["delivery_date"] or r["order_date"] or ""),
            "status":       "processed",
        })

    return {
        "items": items,
        "summary": {
            "total_count":    len(items),
            "total_deducted": round(total_deducted, 2),
            "disputed_count": 0,
            "by_reason":      by_reason,
        },
    }


# ── GST ───────────────────────────────────────────────────────────────────────

_GST_SQL = text("""
    WITH deduped AS (
        SELECT DISTINCT ON (order_item_id)
            sale_amount,
            COALESCE(tcs, 0)          AS tcs,
            COALESCE(tds, 0)          AS tds,
            COALESCE(gst_on_mp_fees, 0) AS gst_on_mp_fees,
            settlement_amount
        FROM settlements_etl
        WHERE is_valid = true
        ORDER BY order_item_id, id ASC
    )
    SELECT
        COALESCE(SUM(sale_amount), 0)       AS taxable,
        ABS(COALESCE(SUM(tcs), 0))          AS tcs,
        ABS(COALESCE(SUM(tds), 0))          AS tds,
        ABS(COALESCE(SUM(gst_on_mp_fees),0)) AS gst_by_platform,
        COUNT(*)                             AS inv
    FROM deduped
""")

_GST_MONTHLY_SQL = text("""
    WITH deduped AS (
        SELECT DISTINCT ON (order_item_id)
            settlement_date,
            sale_amount,
            COALESCE(tcs, 0)          AS tcs,
            COALESCE(tds, 0)          AS tds,
            COALESCE(gst_on_mp_fees, 0) AS gst_on_mp_fees
        FROM settlements_etl
        WHERE is_valid = true
        ORDER BY order_item_id, id ASC
    )
    SELECT
        TO_CHAR(DATE_TRUNC('month', settlement_date), 'Mon YYYY') AS period,
        COALESCE(SUM(sale_amount), 0)        AS taxable,
        ABS(COALESCE(SUM(tcs), 0))           AS tcs,
        ABS(COALESCE(SUM(tds), 0))           AS tds,
        ABS(COALESCE(SUM(gst_on_mp_fees),0)) AS gst_by_platform,
        COUNT(*)                             AS inv
    FROM deduped
    WHERE settlement_date IS NOT NULL
    GROUP BY DATE_TRUNC('month', settlement_date)
    ORDER BY DATE_TRUNC('month', settlement_date)
""")


async def get_gst_data(db: AsyncSession) -> dict:
    """
    SQL source: settlements_etl (DISTINCT ON order_item_id).
    Returns TCS, TDS, GST on MP fees grouped by platform (Flipkart).
    """
    row   = (await db.execute(_GST_SQL)).mappings().one()
    m_rows = (await db.execute(_GST_MONTHLY_SQL)).mappings().all()

    tcs = _f(row["tcs"])
    tds = _f(row["tds"])
    gst = _f(row["gst_by_platform"])

    items = [{
        "plat":    "Flipkart",
        "icon":    "🛍️",
        "taxable": _f(row["taxable"]),
        "tcs":     tcs,
        "tds":     tds,
        "gstByP":  gst,
        "inv":     int(row["inv"]),
        "ok":      True,
    }]

    monthly = [
        {
            "period":  r["period"],
            "taxable": _f(r["taxable"]),
            "tcs":     _f(r["tcs"]),
            "tds":     _f(r["tds"]),
            "gst":     _f(r["gst_by_platform"]),
            "inv":     int(r["inv"]),
        }
        for r in m_rows
    ]

    return {
        "items":   items,
        "monthly": monthly,
        "summary": {
            "total_tcs":    tcs,
            "total_tds":    tds,
            "total_itc":    gst,
            "unreconciled": 0,
            "claimable":    round(tcs + tds + gst, 2),
        },
    }


# ── REVENUE TREND (standalone) ────────────────────────────────────────────────

async def get_revenue_trend(db: AsyncSession) -> list[dict]:
    """
    SQL source: order_financials grouped by order_date month.
    """
    rows = (await db.execute(_TREND_SQL)).mappings().all()
    return [
        {"date": r["period"], "gross": _f(r["gross"]), "net": _f(r["net"])}
        for r in rows
    ]
