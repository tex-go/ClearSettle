"""Pydantic schemas for Cash Flow Forecast API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Snapshot (stored aggregate) ───────────────────────────────────────────────

class SnapshotOut(BaseModel):
    id:               str
    company_id:       str
    snapshot_date:    str
    period_type:      str
    opening_balance:  float
    inflows:          float
    outflows:         float
    net_cash_flow:    float
    closing_balance:  float
    settlements_count: int
    fees_total:       float
    currency:         str
    platform_breakdown_json: Optional[dict]
    ai_shortage_risk: Optional[str]
    ai_insights_json: Optional[dict]
    ai_generated_at:  Optional[str]
    created_at:       str
    updated_at:       str


# ── Projection (computed, not stored) ────────────────────────────────────────

class ProjectionPoint(BaseModel):
    """One time-bucket in a forecast projection."""
    date:             str
    label:            str            # "Mon 19 May", "Week 3", "Q2 2026"
    projected_inflow: float
    projected_outflow: float
    net:              float
    cumulative_balance: float
    confidence:       float          # 0.0 – 1.0
    shortage_risk:    str            # low / medium / high / critical


class ProjectionResponse(BaseModel):
    horizon:    str                  # 7d / 30d / 90d / 1y
    period_type: str                 # daily / weekly / monthly
    current_balance: float
    currency:   str
    points:     list[ProjectionPoint]
    total_projected_inflow: float
    total_projected_outflow: float
    net_projection: float
    generated_at: str


# ── Summary KPIs ──────────────────────────────────────────────────────────────

class ForecastSummary(BaseModel):
    current_month_inflow:  float
    current_month_outflow: float
    current_month_net:     float
    last_month_inflow:     float
    last_month_outflow:    float
    last_month_net:        float
    ytd_inflow:            float
    ytd_outflow:           float
    ytd_net:               float
    avg_monthly_inflow:    float
    avg_monthly_outflow:   float
    platform_breakdown:    dict[str, float]
    currency:              str
    as_of:                 str


# ── AI Insights ───────────────────────────────────────────────────────────────

class InsightItem(BaseModel):
    type:        str   # trend / warning / opportunity / anomaly
    severity:    str   # info / warning / critical
    title:       str
    description: str
    action:      Optional[str] = None


class InsightsResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    insights:     list[InsightItem]
    generated_at: str
    model_used:   str


# ── Generate snapshot request ─────────────────────────────────────────────────

class GenerateSnapshotRequest(BaseModel):
    period_type: str  = Field(default="monthly", description="daily/weekly/monthly/quarterly")
    start_date:  Optional[date] = None
    end_date:    Optional[date] = None
    regenerate:  bool = Field(default=False, description="Overwrite existing snapshots")
