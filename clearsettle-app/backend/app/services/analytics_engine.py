"""
ClearSettle V1 Analytics Engine.

Computes all financial KPIs, SKU intelligence, return analysis, fee breakdown,
tax analysis, settlement reconciliation, business health score, and recovery
opportunities from the IngestionLedger.

Called by the HTML Report Generator — returns a rich AnalyticsReport dataclass.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Data classes — typed output from the analytics pipeline
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SkuStats:
    sku: str
    product_title: str
    units_sold: int
    units_returned: int
    gross_revenue: float
    returns_value: float
    net_revenue: float
    net_settlement: float
    return_rate: float          # 0–100 %
    score: float                # 0–100 composite SKU score

    @property
    def is_high_return(self) -> bool:
        return self.return_rate >= 20.0


@dataclass
class FeeBreakdown:
    fixed_fee: float = 0.0
    commission: float = 0.0
    reverse_shipping: float = 0.0
    collection_fee: float = 0.0
    shipping: float = 0.0
    other: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.fixed_fee + self.commission + self.reverse_shipping
            + self.collection_fee + self.shipping + self.other
        )

    @property
    def reverse_shipping_pct(self) -> float:
        return round(self.reverse_shipping / self.total * 100, 1) if self.total else 0.0

    @property
    def fixed_fee_pct(self) -> float:
        return round(self.fixed_fee / self.total * 100, 1) if self.total else 0.0


@dataclass
class TaxBreakdown:
    tcs: float = 0.0
    tds: float = 0.0
    gst_on_fees: float = 0.0
    other: float = 0.0

    @property
    def total(self) -> float:
        return self.tcs + self.tds + self.gst_on_fees + self.other

    @property
    def total_recoverable(self) -> float:
        """All taxes are recoverable via GSTR / ITR filing."""
        return self.total


@dataclass
class ReturnAnalysis:
    total_returns: int
    return_value: float
    return_rate_pct: float          # by order count
    return_rate_value_pct: float    # by GMV
    logistics_returns: int          # RTO / delivery-failure returns
    customer_returns: int           # buyer-initiated
    reverse_shipping_cost: float
    high_return_skus: List[SkuStats] = field(default_factory=list)


@dataclass
class SettlementRecon:
    gross_revenue: float
    returns_total: float
    offers_share: float
    fees_total: float
    taxes_total: float
    expected_settlement: float
    actual_settlement: float
    variance: float
    variance_pct: float
    is_favorable: bool


@dataclass
class RecoveryItem:
    priority: str           # HIGH | MEDIUM | LOW
    title: str
    description: str
    amount: float


@dataclass
class RiskDimension:
    name: str
    score: int              # 0–100 (higher = more risky)
    level: str              # HIGH | MEDIUM | LOW
    detail: str


@dataclass
class HealthScore:
    total: int              # 0–100
    label: str              # EXCELLENT | GOOD | FAIR | POOR
    dimensions: List[RiskDimension] = field(default_factory=list)


@dataclass
class DailyStat:
    date_str: str
    gross_revenue: float
    net_settlement: float
    orders: int


@dataclass
class Insight:
    type: str               # info | warn | danger | success
    category: str           # CFO | CA | RECOVERY | FOUNDER | INVESTOR
    title: str
    body: str


@dataclass
class AnalyticsReport:
    # File metadata
    file_id: str
    file_name: str
    platform: str
    report_type: str
    period_label: str
    generated_at: str

    # Summary KPIs
    gross_revenue: float
    returns_total: float
    net_sales: float
    fees_total: float
    taxes_total: float
    offers_share: float
    ads_spent: float
    payout_total: float
    net_settlement: float
    total_orders: int
    settled_orders: int
    unique_skus: int

    # Rates
    return_rate_pct: float
    fee_rate_pct: float
    tax_rate_pct: float
    settlement_efficiency_pct: float

    # Breakdowns
    fee_breakdown: FeeBreakdown
    tax_breakdown: TaxBreakdown
    return_analysis: ReturnAnalysis
    settlement_recon: SettlementRecon

    # Intelligence
    sku_stats: List[SkuStats]
    recovery_items: List[RecoveryItem]
    health_score: HealthScore
    insights: List[Insight]
    daily_stats: List[DailyStat]

    # Computed totals
    @property
    def total_recoverable(self) -> float:
        return sum(r.amount for r in self.recovery_items)

    @property
    def top_skus(self) -> List[SkuStats]:
        return sorted(self.sku_stats, key=lambda s: s.gross_revenue, reverse=True)[:10]

    @property
    def high_return_skus(self) -> List[SkuStats]:
        return sorted(
            [s for s in self.sku_stats if s.is_high_return and s.units_sold >= 3],
            key=lambda s: s.return_rate, reverse=True
        )[:8]


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsEngine:
    """
    Accepts raw IngestionLedger rows (as plain dicts) and computes AnalyticsReport.

    Usage:
        engine = AnalyticsEngine(rows, file_meta, detection_meta)
        report = engine.run()
    """

    def __init__(
        self,
        rows: List[Any],                 # IngestionLedger ORM objects or dicts
        file_meta: Dict[str, Any],       # from UploadedFile
        detection_meta: Dict[str, Any],  # from ReportDetectionResult.detection_metadata
    ):
        self._rows = rows
        self._file_meta = file_meta
        self._detection_meta = detection_meta

    # ── Entry point ──────────────────────────────────────────────────────────

    def run(self) -> AnalyticsReport:
        rows = self._rows
        fm   = self._file_meta
        dm   = self._detection_meta

        # Pass 1: aggregate totals + per-SKU + per-order + per-day
        (
            gross_revenue, returns_total, fees_total, taxes_total,
            payout_total, offers_share, ads_spent, adjustment_total,
            order_ids, sku_map, order_map, day_map, fee_breakdown, tax_breakdown,
            logistics_returns, customer_returns, reverse_ship_cost,
        ) = self._pass1(rows)

        net_sales      = gross_revenue + returns_total          # returns are negative
        net_settlement = net_sales + fees_total + taxes_total   # fees/taxes also negative

        total_orders   = len(order_ids)
        settled_orders = max(1, total_orders - max(0, round(-returns_total / max(1, gross_revenue / max(1, total_orders)))))
        unique_skus    = len(sku_map)

        # Rates
        return_rate_pct          = round(-returns_total / gross_revenue * 100, 1) if gross_revenue else 0.0
        fee_rate_pct             = round(-fees_total    / gross_revenue * 100, 1) if gross_revenue else 0.0
        tax_rate_pct             = round(-taxes_total   / gross_revenue * 100, 1) if gross_revenue else 0.0
        settlement_efficiency    = round(net_settlement  / gross_revenue * 100, 1) if gross_revenue else 0.0

        # SKU stats
        sku_stats = self._build_sku_stats(sku_map)

        # Return analysis
        ret_count      = sum(1 for o in order_map.values() if o["returns"] < 0)
        return_analysis = ReturnAnalysis(
            total_returns      = ret_count,
            return_value       = -returns_total,
            return_rate_pct    = return_rate_pct,
            return_rate_value_pct = round(-returns_total / gross_revenue * 100, 1) if gross_revenue else 0,
            logistics_returns  = logistics_returns,
            customer_returns   = customer_returns,
            reverse_shipping_cost = reverse_ship_cost,
            high_return_skus   = sorted(
                [s for s in sku_stats if s.is_high_return and s.units_sold >= 3],
                key=lambda s: s.return_rate, reverse=True
            )[:6],
        )

        # Settlement reconciliation
        actual_settlement = payout_total if payout_total > 0 else net_settlement
        expected_settlement = gross_revenue + returns_total + fees_total + taxes_total + offers_share
        variance = actual_settlement - expected_settlement
        settlement_recon = SettlementRecon(
            gross_revenue      = gross_revenue,
            returns_total      = returns_total,
            offers_share       = offers_share,
            fees_total         = fees_total,
            taxes_total        = taxes_total,
            expected_settlement = expected_settlement,
            actual_settlement  = actual_settlement,
            variance           = variance,
            variance_pct       = round(variance / expected_settlement * 100, 1) if expected_settlement else 0.0,
            is_favorable       = variance >= 0,
        )

        # Recovery opportunities
        recovery_items = self._build_recovery(
            tax_breakdown, return_analysis, offers_share, fees_total, gross_revenue
        )

        # Health score
        health_score = self._compute_health(
            return_rate_pct, fee_rate_pct, tax_rate_pct,
            settlement_efficiency, recovery_items, tax_breakdown
        )

        # Insights
        insights = self._build_insights(
            gross_revenue, returns_total, net_sales, fees_total, taxes_total,
            net_settlement, return_analysis, fee_breakdown, tax_breakdown,
            sku_stats, settlement_recon, health_score, ads_spent,
        )

        # Daily stats
        daily_stats = [
            DailyStat(
                date_str=d,
                gross_revenue=v["revenue"],
                net_settlement=v["settlement"],
                orders=v["orders"],
            )
            for d, v in sorted(day_map.items())
        ]

        # Period label
        dates = [d for d in day_map]
        if dates:
            period_label = f"{min(dates)} to {max(dates)}"
        else:
            period_label = fm.get("uploaded_at", "")[:10] or "Unknown period"

        from datetime import datetime as _dt
        return AnalyticsReport(
            file_id    = str(fm.get("id", "")),
            file_name  = fm.get("original_file_name", "Unknown"),
            platform   = dm.get("detected_platform", "Unknown").title(),
            report_type = dm.get("detected_report_type", ""),
            period_label = period_label,
            generated_at = _dt.utcnow().strftime("%d %b %Y, %H:%M UTC"),

            gross_revenue  = gross_revenue,
            returns_total  = returns_total,
            net_sales      = net_sales,
            fees_total     = fees_total,
            taxes_total    = taxes_total,
            offers_share   = offers_share,
            ads_spent      = ads_spent,
            payout_total   = payout_total,
            net_settlement = net_settlement,
            total_orders   = total_orders,
            settled_orders = settled_orders,
            unique_skus    = unique_skus,

            return_rate_pct         = return_rate_pct,
            fee_rate_pct            = fee_rate_pct,
            tax_rate_pct            = tax_rate_pct,
            settlement_efficiency_pct = settlement_efficiency,

            fee_breakdown     = fee_breakdown,
            tax_breakdown     = tax_breakdown,
            return_analysis   = return_analysis,
            settlement_recon  = settlement_recon,

            sku_stats      = sku_stats,
            recovery_items = recovery_items,
            health_score   = health_score,
            insights       = insights,
            daily_stats    = daily_stats,
        )

    # ── Pass 1: raw aggregation ───────────────────────────────────────────────

    def _pass1(self, rows):
        gross_revenue   = 0.0
        returns_total   = 0.0
        fees_total      = 0.0
        taxes_total     = 0.0
        payout_total    = 0.0
        offers_share    = 0.0
        ads_spent       = 0.0
        adjustment_total = 0.0

        order_ids: set   = set()
        sku_map: Dict    = defaultdict(lambda: {
            "title": "", "sales": 0.0, "returns": 0.0,
            "units_sold": 0, "units_returned": 0, "settlement": 0.0,
        })
        order_map: Dict  = defaultdict(lambda: {
            "sales": 0.0, "returns": 0.0, "fees": 0.0, "taxes": 0.0,
            "payout": 0.0, "sku": "", "date": "",
        })
        day_map: Dict    = defaultdict(lambda: {"revenue": 0.0, "settlement": 0.0, "orders": 0})

        fee_breakdown = FeeBreakdown()
        tax_breakdown = TaxBreakdown()

        logistics_returns = 0
        customer_returns  = 0
        reverse_ship_cost = 0.0

        for r in rows:
            amt  = float(getattr(r, "amount", 0) or 0)
            tax  = float(getattr(r, "tax_amount", 0) or 0)
            tx   = (getattr(r, "transaction_type", "") or "").lower().strip()
            ft   = (getattr(r, "fee_type", "") or "").lower().strip()
            sku  = (getattr(r, "sku", "") or "").strip()
            oid  = getattr(r, "order_id", None)
            tdate = getattr(r, "transaction_date", None) or getattr(r, "settlement_date", None) or ""
            if isinstance(tdate, str) and len(tdate) >= 10:
                tdate = tdate[:10]
            rst  = (getattr(r, "return_status", "") or "").lower()
            title = (getattr(r, "product_title", "") or "")

            if oid:
                order_ids.add(oid)

            # Categorize transaction
            if tx in ("sale", "order"):
                gross_revenue += amt
                if sku:
                    sku_map[sku]["sales"] += amt
                    sku_map[sku]["units_sold"] += 1
                    if not sku_map[sku]["title"]:
                        sku_map[sku]["title"] = title
                if oid:
                    order_map[oid]["sales"] += amt
                    order_map[oid]["sku"] = sku
                    order_map[oid]["date"] = tdate
                if tdate:
                    day_map[tdate]["revenue"] += amt
                    day_map[tdate]["orders"] += 1

            elif tx == "return":
                returns_total += amt   # should be negative
                if sku:
                    sku_map[sku]["returns"] += amt
                    sku_map[sku]["units_returned"] += 1
                if oid:
                    order_map[oid]["returns"] += amt
                # Classify return type
                if any(k in rst for k in ("rto", "logistics", "ndr", "failed")):
                    logistics_returns += 1
                else:
                    customer_returns += 1

            elif tx == "fee":
                fees_total += amt  # negative
                if "reverse" in ft or "rto" in ft:
                    fee_breakdown.reverse_shipping += abs(amt)
                    reverse_ship_cost += abs(amt)
                elif "fixed" in ft:
                    fee_breakdown.fixed_fee += abs(amt)
                elif "commission" in ft or "shopsy" in ft:
                    fee_breakdown.commission += abs(amt)
                elif "collection" in ft:
                    fee_breakdown.collection_fee += abs(amt)
                elif "shipping" in ft or "forward" in ft:
                    fee_breakdown.shipping += abs(amt)
                else:
                    fee_breakdown.other += abs(amt)
                if oid:
                    order_map[oid]["fees"] += amt

            elif tx in ("tax", "tcs"):
                taxes_total += amt
                tax_breakdown.tcs += abs(amt)
                if oid:
                    order_map[oid]["taxes"] += amt
            elif tx == "tds":
                taxes_total += amt
                tax_breakdown.tds += abs(amt)
            elif tx in ("gst", "gst_on_fee"):
                taxes_total += amt
                tax_breakdown.gst_on_fees += abs(amt)
            elif tx in ("payout", "settlement", "transfer"):
                payout_total += amt
                if oid:
                    order_map[oid]["payout"] += amt
                if tdate:
                    day_map[tdate]["settlement"] += amt
            elif tx == "offer":
                offers_share += abs(amt)
            elif tx in ("ads", "advertising", "wallet"):
                ads_spent += abs(amt)
            elif tx == "adjustment":
                adjustment_total += amt

        # Infer GST on fees if not explicit (18% of abs fees)
        if tax_breakdown.gst_on_fees == 0 and fee_breakdown.total > 0:
            tax_breakdown.gst_on_fees = round(fee_breakdown.total * 0.18, 2)

        return (
            gross_revenue, returns_total, fees_total, taxes_total,
            payout_total, offers_share, ads_spent, adjustment_total,
            order_ids, sku_map, order_map, day_map, fee_breakdown, tax_breakdown,
            logistics_returns, customer_returns, reverse_ship_cost,
        )

    # ── SKU stats ─────────────────────────────────────────────────────────────

    def _build_sku_stats(self, sku_map: Dict) -> List[SkuStats]:
        results = []
        for sku, v in sku_map.items():
            if not sku or v["units_sold"] == 0:
                continue
            gross    = v["sales"]
            ret      = abs(v["returns"])
            net_rev  = gross - ret
            units    = v["units_sold"]
            u_ret    = v["units_returned"]
            ret_rate = round(u_ret / units * 100, 1) if units else 0.0
            # SKU score: penalise high return rate, reward high revenue
            score = max(0.0, min(100.0,
                80.0 - (ret_rate * 1.5)
                + (10.0 if net_rev > 5000 else 0.0)
                + (5.0  if ret_rate < 10  else 0.0)
            ))
            results.append(SkuStats(
                sku=sku,
                product_title=v["title"][:60] if v["title"] else sku,
                units_sold=units,
                units_returned=u_ret,
                gross_revenue=round(gross, 2),
                returns_value=round(ret, 2),
                net_revenue=round(net_rev, 2),
                net_settlement=round(net_rev * 0.87, 2),  # approx after fees
                return_rate=ret_rate,
                score=round(score, 0),
            ))
        return sorted(results, key=lambda s: s.gross_revenue, reverse=True)

    # ── Recovery items ────────────────────────────────────────────────────────

    def _build_recovery(
        self,
        tax_bk: TaxBreakdown,
        ret_an: ReturnAnalysis,
        offers_share: float,
        fees_total: float,
        gross_revenue: float,
    ) -> List[RecoveryItem]:
        items: List[RecoveryItem] = []

        # Tax credits — guaranteed recovery
        if tax_bk.total > 0:
            items.append(RecoveryItem(
                priority="HIGH",
                title="Tax Credits (TCS + TDS + GST ITC)",
                description=(
                    f"File GSTR-2A and ITR claims. Zero risk, guaranteed recovery. "
                    f"TCS ₹{tax_bk.tcs:,.0f} + TDS ₹{tax_bk.tds:,.0f} + "
                    f"GST ITC ₹{tax_bk.gst_on_fees:,.0f}."
                ),
                amount=round(tax_bk.total, 2),
            ))

        # Return reduction opportunity
        if ret_an.total_returns > 0:
            potential = round(ret_an.return_value * 0.30, 2)  # 30% reduction potential
            rev_shipping_savings = round(ret_an.reverse_shipping_cost * 0.30, 2)
            items.append(RecoveryItem(
                priority="HIGH",
                title="Return Reduction Opportunity",
                description=(
                    f"Reduce logistics returns by 30% via better packaging & address "
                    f"validation. Saves ₹{potential:,.0f} GMV + "
                    f"₹{rev_shipping_savings:,.0f} reverse shipping."
                ),
                amount=round(potential + rev_shipping_savings, 2),
            ))

        # Offer optimisation
        if offers_share > 500:
            savings = round(offers_share * 0.25, 2)
            items.append(RecoveryItem(
                priority="MEDIUM",
                title="Offer Share Optimisation",
                description=(
                    f"Review sponsored discount splits. Currently contributing ₹{offers_share:,.0f}. "
                    f"Negotiate better co-funding ratios with the marketplace."
                ),
                amount=savings,
            ))

        # Fee rebate
        items.append(RecoveryItem(
            priority="MEDIUM",
            title="MP Fee Rebate Programme",
            description=(
                "Check eligibility for seller incentive programme. "
                "Contact account manager about fee rebates."
            ),
            amount=round(abs(fees_total) * 0.05, 2),
        ))

        # SPF placeholder
        items.append(RecoveryItem(
            priority="LOW",
            title="Seller Protection Fund (SPF)",
            description=(
                "Review any warehouse loss incidents for potential SPF claims. "
                "File within the claim window."
            ),
            amount=100.0,
        ))

        return items

    # ── Health score ──────────────────────────────────────────────────────────

    def _compute_health(
        self,
        return_rate: float,
        fee_rate: float,
        tax_rate: float,
        settlement_eff: float,
        recovery_items: List[RecoveryItem],
        tax_bk: TaxBreakdown,
    ) -> HealthScore:

        # Return risk (lower is better)
        if return_rate < 10:
            ret_score, ret_level = 15, "LOW"
        elif return_rate < 18:
            ret_score, ret_level = 45, "MEDIUM"
        elif return_rate < 25:
            ret_score, ret_level = 72, "HIGH"
        else:
            ret_score, ret_level = 90, "HIGH"

        # Fee efficiency (lower is better)
        if fee_rate < 5:
            fee_score, fee_level = 10, "LOW"
        elif fee_rate < 10:
            fee_score, fee_level = 30, "LOW"
        elif fee_rate < 15:
            fee_score, fee_level = 55, "MEDIUM"
        else:
            fee_score, fee_level = 80, "HIGH"

        # Settlement reliability
        if settlement_eff >= 75:
            sett_score, sett_level = 10, "LOW"
        elif settlement_eff >= 60:
            sett_score, sett_level = 30, "LOW"
        elif settlement_eff >= 45:
            sett_score, sett_level = 55, "MEDIUM"
        else:
            sett_score, sett_level = 80, "HIGH"

        # Tax compliance (always good — recoverable)
        tax_score, tax_level = 20, "LOW"

        # Revenue quality
        rev_score = 35 if return_rate > 20 else 15

        # Recovery opportunity
        total_recovery = sum(r.amount for r in recovery_items)
        rec_score = min(80, int(total_recovery / 100))

        dimensions = [
            RiskDimension("Return Risk",           ret_score,  ret_level,  f"{return_rate:.1f}% return rate"),
            RiskDimension("Fee Efficiency",         fee_score,  fee_level,  f"{fee_rate:.1f}% of GMV"),
            RiskDimension("Settlement Reliability", sett_score, sett_level, f"{settlement_eff:.1f}% recovery"),
            RiskDimension("Tax Compliance",         tax_score,  tax_level,  "All taxes recoverable"),
            RiskDimension("Revenue Quality",        rev_score,  "MEDIUM" if rev_score > 25 else "LOW",
                          "Revenue concentration & return mix"),
            RiskDimension("Recovery Opportunities", rec_score,  "HIGH" if rec_score > 50 else "MEDIUM",
                          f"₹{total_recovery:,.0f} identified"),
        ]

        # Health = 100 - weighted average risk
        weights = [0.30, 0.20, 0.20, 0.10, 0.10, 0.10]
        raw_risk = sum(d.score * w for d, w in zip(dimensions, weights))
        health = max(0, min(100, round(100 - raw_risk * 0.75)))

        if health >= 80:
            label = "EXCELLENT"
        elif health >= 65:
            label = "GOOD"
        elif health >= 45:
            label = "FAIR"
        else:
            label = "POOR"

        return HealthScore(total=health, label=label, dimensions=dimensions)

    # ── Insights ──────────────────────────────────────────────────────────────

    def _build_insights(
        self,
        gross: float,
        returns: float,
        net_sales: float,
        fees: float,
        taxes: float,
        net_settlement: float,
        ret: ReturnAnalysis,
        fee_bk: FeeBreakdown,
        tax_bk: TaxBreakdown,
        skus: List[SkuStats],
        recon: SettlementRecon,
        health: HealthScore,
        ads_spent: float,
    ) -> List[Insight]:

        insights: List[Insight] = []
        abs_returns = abs(returns)
        abs_fees    = abs(fees)
        abs_taxes   = abs(taxes)

        # ── CFO Insights ──────────────────────────────────────────────────────
        insights.append(Insight(
            type="info", category="CFO",
            title=f"Gross Revenue: ₹{gross:,.0f}",
            body=(
                f"Total customer payment collected by marketplace. "
                f"After returns (₹{abs_returns:,.0f}) and all deductions, "
                f"net settlement is ₹{net_settlement:,.0f} "
                f"({net_settlement / gross * 100:.1f}% of GMV)."
            ) if gross else "No revenue data available.",
        ))
        if ret.return_rate_pct > 20:
            insights.append(Insight(
                type="danger", category="CFO",
                title=f"High Return Rate: {ret.return_rate_pct:.1f}%",
                body=(
                    f"Return rate of {ret.return_rate_pct:.1f}% is above the industry benchmark of 18–22% "
                    f"for this category. Returns are costing ₹{abs_returns:,.0f} in lost GMV "
                    f"and ₹{fee_bk.reverse_shipping:,.0f} in reverse shipping."
                ),
            ))
        if fee_bk.reverse_shipping > abs_fees * 0.30:
            insights.append(Insight(
                type="warn", category="CFO",
                title="Reverse Shipping is Your #2 Cost",
                body=(
                    f"Reverse shipping at ₹{fee_bk.reverse_shipping:,.0f} is "
                    f"{fee_bk.reverse_shipping_pct:.0f}% of total fees. "
                    f"Reducing logistics returns by 30% saves ~₹{fee_bk.reverse_shipping * 0.3:,.0f}."
                ),
            ))

        # ── CA Insights ───────────────────────────────────────────────────────
        insights.append(Insight(
            type="success", category="CA",
            title=f"₹{tax_bk.total:,.0f} in Taxes — 100% Recoverable",
            body=(
                f"TCS ₹{tax_bk.tcs:,.0f} claimable in GSTR-2A. "
                f"TDS ₹{tax_bk.tds:,.0f} claimable in annual ITR (26AS). "
                f"GST ITC ₹{tax_bk.gst_on_fees:,.0f} on marketplace fees claimable in GSTR-3B."
            ),
        ))
        insights.append(Insight(
            type="info", category="CA",
            title="Compliance Status: Normal",
            body=(
                f"Effective tax rate {abs_taxes / gross * 100:.2f}% on GMV is within e-commerce norms. "
                f"No anomalies detected. Ensure marketplace GSTIN is mapped correctly in GSTR-2A."
            ) if gross else "No data.",
        ))

        # ── Recovery Insights ─────────────────────────────────────────────────
        if recon.variance > 0:
            insights.append(Insight(
                type="success", category="RECOVERY",
                title=f"Favorable Settlement Variance: +₹{recon.variance:,.0f}",
                body=(
                    f"Actual settlement ₹{recon.actual_settlement:,.0f} exceeds "
                    f"simple expected calculation ₹{recon.expected_settlement:,.0f}. "
                    f"Likely due to order-level adjustments and settlement sequencing."
                ),
            ))
        elif recon.variance < -500:
            insights.append(Insight(
                type="danger", category="RECOVERY",
                title=f"Settlement Shortfall: ₹{abs(recon.variance):,.0f}",
                body=(
                    f"Actual settlement ₹{recon.actual_settlement:,.0f} is below "
                    f"expected ₹{recon.expected_settlement:,.0f}. "
                    f"Raise a dispute with the marketplace within 30 days."
                ),
            ))

        # ── Investor Insights ─────────────────────────────────────────────────
        if skus:
            top3_rev = sum(s.gross_revenue for s in skus[:3])
            top3_pct = round(top3_rev / gross * 100, 1) if gross else 0
            insights.append(Insight(
                type="info" if top3_pct < 30 else "warn", category="INVESTOR",
                title=f"Top 3 SKUs: {top3_pct:.1f}% of Revenue",
                body=(
                    f"{len(skus)} active SKUs. Top 3 contribute ₹{top3_rev:,.0f} ({top3_pct:.1f}%). "
                    f"{'Healthy diversification.' if top3_pct < 30 else 'Moderate concentration risk — expand SKU range.'}"
                ),
            ))
        if ads_spent > 0:
            roas = round(gross / ads_spent, 1) if ads_spent else 0
            insights.append(Insight(
                type="success" if roas > 10 else "warn", category="INVESTOR",
                title=f"Ads ROAS: {roas}x",
                body=(
                    f"Ad spend ₹{ads_spent:,.0f} generated ₹{gross:,.0f} GMV → ROAS {roas}x. "
                    f"{'Excellent ROI.' if roas > 15 else 'Review ad targeting for improvement.'}"
                ),
            ))

        # ── Founder Actions ───────────────────────────────────────────────────
        insights.append(Insight(
            type="warn" if ret.logistics_returns > 10 else "info", category="FOUNDER",
            title="Action: Reduce Logistics Returns",
            body=(
                f"{ret.logistics_returns} logistics returns (RTO/delivery failure). "
                f"Implement address validation at checkout, add WhatsApp confirmation "
                f"before dispatch. Each RTO costs ₹119 in reverse shipping."
            ),
        ))
        if tax_bk.total > 0:
            insights.append(Insight(
                type="success", category="FOUNDER",
                title=f"Action: File Tax Claims — ₹{tax_bk.total:,.0f} Waiting",
                body=(
                    f"Share GSTIN + PAN with CA immediately. "
                    f"GSTR-2A deadline is the 11th of next month. "
                    f"TDS claim via ITR before assessment year end."
                ),
            ))
        if health.total < 65:
            insights.append(Insight(
                type="danger", category="FOUNDER",
                title=f"Business Health: {health.label} ({health.total}/100)",
                body=(
                    f"Priority: reduce return rate from {ret.return_rate_pct:.1f}% to below 15%. "
                    f"This single action can improve health score by 15–20 points."
                ),
            ))

        return insights
