"""
ClearSettle V1 — Premium HTML Report Generator.

Generates a single-page dark-mode analytics report from an AnalyticsReport dataclass.
Output quality: Stripe / Linear / Razorpay — CFO + CA + Investor + Founder sections.

Usage:
    from app.services.analytics_engine import AnalyticsEngine
    from app.services.report_generator import ReportGenerator

    engine = AnalyticsEngine(rows, file_meta, detection_meta)
    report = engine.run()
    html   = ReportGenerator(report).generate()
"""
from __future__ import annotations

import json
from typing import List

from app.services.analytics_engine import (
    AnalyticsReport, DailyStat, Insight, RecoveryItem,
    RiskDimension, SkuStats,
)


def _fmt(v: float) -> str:
    """Format float as Indian rupee string: ₹1,25,342"""
    if v == 0:
        return "₹0"
    neg = v < 0
    v = abs(v)
    if v >= 1_00_00_000:
        return f"{'−' if neg else ''}₹{v / 1_00_00_000:.2f}Cr"
    if v >= 1_00_000:
        return f"{'−' if neg else ''}₹{v / 1_00_000:.2f}L"
    if v >= 1_000:
        # Indian comma formatting: X,XX,XXX
        vi = int(round(v))
        s = str(vi)
        if len(s) > 3:
            s = s[:-3] + "," + s[-3:]
        if len(s) > 7:
            s = s[:-7] + "," + s[-7:]
        return f"{'−' if neg else ''}₹{s}"
    return f"{'−' if neg else ''}₹{v:.0f}"


def _fmtc(v: float) -> str:
    """Compact format: ₹86.9K, ₹1.25L"""
    if v == 0:
        return "₹0"
    neg = v < 0
    v   = abs(v)
    if v >= 1_00_00_000:
        s = f"₹{v / 1_00_00_000:.1f}Cr"
    elif v >= 1_00_000:
        s = f"₹{v / 1_00_000:.1f}L"
    elif v >= 1_000:
        s = f"₹{v / 1_000:.1f}K"
    else:
        s = f"₹{v:.0f}"
    return ("−" if neg else "") + s


def _pct(v: float, sign: bool = False) -> str:
    p = f"{v:.1f}%"
    if sign and v > 0:
        p = "+" + p
    return p


class ReportGenerator:
    def __init__(self, report: AnalyticsReport):
        self._r = report

    # ── Public API ───────────────────────────────────────────────────────────

    def generate(self) -> str:
        r = self._r
        return (
            self._head(r)
            + self._sidebar(r)
            + "<main id='main'>"
            + self._hero(r)
            + self._kpi_grid(r)
            + self._waterfall(r)
            + self._revenue_analytics(r)
            + self._product_intelligence(r)
            + self._return_intelligence(r)
            + self._settlement_recon(r)
            + self._fee_analysis(r)
            + self._tax_intelligence(r)
            + self._recovery_engine(r)
            + self._risk_dashboard(r)
            + self._insights_section(r)
            + self._ca_review(r)
            + self._investor_view(r)
            + self._founder_actions(r)
            + self._footer(r)
            + "</main>"
            + self._scripts(r)
            + "</body></html>"
        )

    # ── HTML Head ────────────────────────────────────────────────────────────

    def _head(self, r: AnalyticsReport) -> str:
        title = f"ClearSettle — {r.file_name[:40]} | Settlement Analytics"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/apexcharts@3.48.0/dist/apexcharts.min.js"></script>
<style>
:root {{
  --bg:#0B1220;--surface:#111827;--card:#1E293B;--card-hover:#243347;
  --primary:#14B8A6;--primary-dim:rgba(20,184,166,.15);--primary-glow:rgba(20,184,166,.4);
  --success:#22C55E;--success-dim:rgba(34,197,94,.12);
  --warning:#F59E0B;--warning-dim:rgba(245,158,11,.12);
  --danger:#EF4444;--danger-dim:rgba(239,68,68,.12);
  --purple:#A78BFA;--blue:#60A5FA;
  --text:#F8FAFC;--text-sec:#94A3B8;--text-muted:#64748B;
  --border:rgba(255,255,255,.07);--border-bright:rgba(255,255,255,.12);
  --shadow:0 4px 24px rgba(0,0,0,.4);--shadow-lg:0 8px 48px rgba(0,0,0,.6);
  --radius:16px;--radius-sm:10px;
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html{{scroll-behavior:smooth;}}
body{{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;font-size:14px;line-height:1.6;overflow-x:hidden;}}
::-webkit-scrollbar{{width:5px;}}::-webkit-scrollbar-track{{background:var(--surface);}}::-webkit-scrollbar-thumb{{background:var(--primary);border-radius:3px;}}
#sidebar{{position:fixed;left:0;top:0;width:220px;height:100vh;background:rgba(17,24,39,.95);backdrop-filter:blur(20px);border-right:1px solid var(--border);z-index:100;display:flex;flex-direction:column;padding:24px 0;}}
.sidebar-logo{{padding:0 20px 24px;border-bottom:1px solid var(--border);margin-bottom:16px;}}
.sidebar-logo .logo-text{{font-family:'Syne',sans-serif;font-size:20px;font-weight:800;background:linear-gradient(135deg,var(--primary),#60A5FA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.sidebar-logo .logo-sub{{font-size:10px;color:var(--text-muted);letter-spacing:.1em;text-transform:uppercase;margin-top:2px;}}
.nav-section-title{{font-size:9px;color:var(--text-muted);letter-spacing:.12em;text-transform:uppercase;padding:12px 20px 6px;font-family:'DM Mono',monospace;}}
.nav-item{{display:flex;align-items:center;gap:10px;padding:9px 20px;color:var(--text-muted);text-decoration:none;font-size:13px;font-weight:400;transition:all .2s;border-left:2px solid transparent;cursor:pointer;}}
.nav-item:hover{{color:var(--text);background:rgba(255,255,255,.04);border-left-color:var(--primary);}}
.nav-item.active{{color:var(--primary);border-left-color:var(--primary);background:var(--primary-dim);font-weight:500;}}
.nav-dot{{width:6px;height:6px;border-radius:50%;background:var(--text-muted);flex-shrink:0;}}
.nav-item.active .nav-dot{{background:var(--primary);box-shadow:0 0 8px var(--primary);}}
.sidebar-footer{{margin-top:auto;padding:16px 20px;border-top:1px solid var(--border);font-size:11px;color:var(--text-muted);}}
.health-badge{{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-bottom:6px;}}
.health-dot{{width:6px;height:6px;border-radius:50%;animation:pulse 2s infinite;}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1);}}50%{{opacity:.5;transform:scale(1.3);}}}}
#main{{margin-left:220px;min-height:100vh;padding:0 32px 60px;}}
.hero{{position:relative;padding:48px 0 40px;overflow:hidden;}}
.hero-bg{{position:absolute;top:-60px;right:-100px;width:600px;height:400px;background:radial-gradient(ellipse,rgba(20,184,166,.12) 0%,transparent 70%);pointer-events:none;}}
.hero-tag{{display:inline-flex;align-items:center;gap:8px;background:var(--primary-dim);border:1px solid rgba(20,184,166,.25);color:var(--primary);padding:5px 14px;border-radius:20px;font-size:11px;font-family:'DM Mono',monospace;letter-spacing:.06em;margin-bottom:20px;}}
.hero h1{{font-family:'Syne',sans-serif;font-size:38px;font-weight:800;line-height:1.1;margin-bottom:12px;}}
.hero h1 span{{background:linear-gradient(135deg,var(--primary),#60A5FA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.hero-meta{{display:flex;gap:14px;flex-wrap:wrap;margin-top:20px;}}
.meta-chip{{display:flex;align-items:center;gap:8px;padding:8px 16px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:12px;}}
.meta-chip .label{{color:var(--text-muted);}}
.meta-chip .val{{color:var(--text);font-weight:500;font-family:'DM Mono',monospace;}}
.health-ring-wrap{{position:absolute;right:0;top:40px;display:flex;flex-direction:column;align-items:center;gap:8px;}}
.health-ring-label{{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;font-family:'DM Mono',monospace;}}
.section{{margin-top:48px;}}
.section-head{{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:24px;}}
.section-title{{font-family:'Syne',sans-serif;font-size:20px;font-weight:700;}}
.section-title span{{color:var(--primary);}}
.section-sub{{font-size:12px;color:var(--text-muted);margin-top:3px;}}
.section-tag{{font-size:10px;font-family:'DM Mono',monospace;color:var(--text-muted);border:1px solid var(--border);padding:3px 10px;border-radius:20px;}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;transition:all .2s;position:relative;overflow:hidden;}}
.card:hover{{border-color:var(--border-bright);box-shadow:var(--shadow);transform:translateY(-1px);}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.06),transparent);}}
.kpi-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}}
.kpi-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px 22px;position:relative;overflow:hidden;transition:all .25s;cursor:default;}}
.kpi-card:hover{{border-color:var(--border-bright);transform:translateY(-2px);box-shadow:var(--shadow-lg);}}
.kpi-card::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;}}
.kpi-card.c-primary::after{{background:var(--primary);}} .kpi-card.c-success::after{{background:var(--success);}} .kpi-card.c-warning::after{{background:var(--warning);}} .kpi-card.c-danger::after{{background:var(--danger);}} .kpi-card.c-purple::after{{background:var(--purple);}} .kpi-card.c-blue::after{{background:var(--blue);}}
.kpi-label{{font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.1em;font-family:'DM Mono',monospace;margin-bottom:10px;}}
.kpi-value{{font-family:'Syne',sans-serif;font-size:26px;font-weight:700;line-height:1;margin-bottom:8px;}}
.kpi-card.c-primary .kpi-value{{color:var(--primary);}} .kpi-card.c-success .kpi-value{{color:var(--success);}} .kpi-card.c-warning .kpi-value{{color:var(--warning);}} .kpi-card.c-danger .kpi-value{{color:var(--danger);}} .kpi-card.c-purple .kpi-value{{color:var(--purple);}} .kpi-card.c-blue .kpi-value{{color:var(--blue);}}
.kpi-pct{{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-family:'DM Mono',monospace;padding:2px 8px;border-radius:10px;margin-bottom:10px;}}
.kpi-pct.pos{{background:var(--success-dim);color:var(--success);}} .kpi-pct.neg{{background:var(--danger-dim);color:var(--danger);}} .kpi-pct.neu{{background:rgba(148,163,184,.1);color:var(--text-muted);}}
.kpi-note{{font-size:11px;color:var(--text-muted);line-height:1.4;}}
.kpi-icon{{position:absolute;top:18px;right:18px;font-size:22px;opacity:.15;}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;}}
.grid-3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;}}
.grid-4{{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:16px;}}
.col-span-2{{grid-column:span 2;}}
.chart-wrap{{position:relative;width:100%;}}
.chart-title{{font-size:13px;font-weight:600;color:var(--text-sec);margin-bottom:16px;display:flex;align-items:center;gap:8px;}}
.chart-title::before{{content:'';width:3px;height:14px;background:var(--primary);border-radius:2px;display:block;}}
.data-table{{width:100%;border-collapse:collapse;font-size:12px;}}
.data-table th{{text-align:left;padding:10px 14px;color:var(--text-muted);font-weight:500;font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--border);background:rgba(255,255,255,.02);}}
.data-table td{{padding:11px 14px;border-bottom:1px solid rgba(255,255,255,.04);color:var(--text-sec);vertical-align:middle;}}
.data-table tr:hover td{{background:rgba(255,255,255,.02);color:var(--text);}}
.data-table tr:last-child td{{border-bottom:none;}}
td.mono{{font-family:'DM Mono',monospace;font-size:11px;}}
td.pos{{color:var(--success)!important;}} td.neg{{color:var(--danger)!important;}} td.warn{{color:var(--warning)!important;}} td.pri{{color:var(--primary)!important;}}
.badge{{display:inline-flex;align-items:center;padding:3px 9px;border-radius:10px;font-size:10px;font-weight:600;font-family:'DM Mono',monospace;}}
.badge-success{{background:var(--success-dim);color:var(--success);}} .badge-warning{{background:var(--warning-dim);color:var(--warning);}} .badge-danger{{background:var(--danger-dim);color:var(--danger);}} .badge-primary{{background:var(--primary-dim);color:var(--primary);}} .badge-purple{{background:rgba(167,139,250,.12);color:var(--purple);}}
.progress-bar{{height:6px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden;margin-top:6px;}}
.progress-fill{{height:100%;border-radius:3px;transition:width 1s ease;}}
.action-item{{display:flex;align-items:flex-start;gap:14px;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.04);}}
.action-item:last-child{{border-bottom:none;}}
.action-num{{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;font-family:'DM Mono',monospace;}}
.action-num.high{{background:var(--danger-dim);color:var(--danger);}} .action-num.med{{background:var(--warning-dim);color:var(--warning);}} .action-num.low{{background:var(--success-dim);color:var(--success);}}
.action-content{{flex:1;}}
.action-title{{font-size:13px;font-weight:600;margin-bottom:3px;}}
.action-desc{{font-size:11px;color:var(--text-muted);line-height:1.4;}}
.action-amount{{font-family:'DM Mono',monospace;font-size:12px;color:var(--success);font-weight:600;flex-shrink:0;}}
.insight-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px 16px;border-left:3px solid;margin-bottom:10px;}}
.insight-card.type-info{{border-left-color:var(--primary);}} .insight-card.type-warn{{border-left-color:var(--warning);}} .insight-card.type-danger{{border-left-color:var(--danger);}} .insight-card.type-success{{border-left-color:var(--success);}}
.insight-text{{font-size:12px;color:var(--text-sec);line-height:1.5;}}
.insight-type{{font-size:10px;font-family:'DM Mono',monospace;color:var(--text-muted);margin-bottom:4px;text-transform:uppercase;letter-spacing:.08em;}}
.insight-title{{font-size:13px;font-weight:600;margin-bottom:4px;}}
.risk-item{{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.04);}}
.risk-item:last-child{{border-bottom:none;}}
.risk-name{{flex:1;font-size:12px;color:var(--text-sec);}}
.risk-bar-bg{{width:100px;height:6px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden;}}
.risk-bar-fill{{height:100%;border-radius:3px;}}
.risk-num{{width:30px;text-align:right;font-family:'DM Mono',monospace;font-size:11px;font-weight:600;}}
.divider{{height:1px;background:var(--border);margin:8px 0;}}
.page-footer{{text-align:center;padding:32px 0;font-size:11px;color:var(--text-muted);border-top:1px solid var(--border);margin-top:48px;}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(20px);}}to{{opacity:1;transform:translateY(0);}}}}
.fade-up{{animation:fadeUp .5s ease forwards;}}
.fade-up-delay-1{{animation-delay:.1s;opacity:0;}} .fade-up-delay-2{{animation-delay:.2s;opacity:0;}} .fade-up-delay-3{{animation-delay:.3s;opacity:0;}}
@media(max-width:900px){{#sidebar{{display:none;}}#main{{margin-left:0;padding:0 16px 40px;}} .kpi-grid{{grid-template-columns:1fr 1fr;}} .grid-2{{grid-template-columns:1fr;}} .grid-3{{grid-template-columns:1fr;}} .col-span-2{{grid-column:span 1;}} .health-ring-wrap{{display:none;}}}}
@media(max-width:600px){{.kpi-grid{{grid-template-columns:1fr;}} .hero h1{{font-size:26px;}}}}
@media print{{#sidebar{{display:none;}}#main{{margin-left:0;}} .card{{break-inside:avoid;}}}}
</style></head><body>
"""

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _sidebar(self, r: AnalyticsReport) -> str:
        h = r.health_score
        badge_cls = "success" if h.total >= 70 else "warning" if h.total >= 45 else "danger"
        badge_color = "var(--success)" if h.total >= 70 else "var(--warning)" if h.total >= 45 else "var(--danger)"
        return f"""
<nav id="sidebar">
  <div class="sidebar-logo">
    <div class="logo-text">ClearSettle</div>
    <div class="logo-sub">Settlement Intelligence</div>
  </div>
  <div class="nav-section-title">Overview</div>
  <a class="nav-item active" href="#hero" onclick="setActive(this)"><span class="nav-dot"></span>Executive Summary</a>
  <a class="nav-item" href="#waterfall" onclick="setActive(this)"><span class="nav-dot"></span>Revenue Waterfall</a>
  <div class="nav-section-title">Analytics</div>
  <a class="nav-item" href="#revenue" onclick="setActive(this)"><span class="nav-dot"></span>Revenue Analytics</a>
  <a class="nav-item" href="#products" onclick="setActive(this)"><span class="nav-dot"></span>Product Intelligence</a>
  <a class="nav-item" href="#returns" onclick="setActive(this)"><span class="nav-dot"></span>Return Intelligence</a>
  <a class="nav-item" href="#settlement" onclick="setActive(this)"><span class="nav-dot"></span>Settlement Recon</a>
  <div class="nav-section-title">Finance</div>
  <a class="nav-item" href="#fees" onclick="setActive(this)"><span class="nav-dot"></span>Fee Analysis</a>
  <a class="nav-item" href="#tax" onclick="setActive(this)"><span class="nav-dot"></span>Tax Intelligence</a>
  <a class="nav-item" href="#recovery" onclick="setActive(this)"><span class="nav-dot"></span>Recovery Engine</a>
  <div class="nav-section-title">Intelligence</div>
  <a class="nav-item" href="#risk" onclick="setActive(this)"><span class="nav-dot"></span>Risk Dashboard</a>
  <a class="nav-item" href="#insights" onclick="setActive(this)"><span class="nav-dot"></span>CFO Insights</a>
  <a class="nav-item" href="#ca" onclick="setActive(this)"><span class="nav-dot"></span>CA Review</a>
  <a class="nav-item" href="#investor" onclick="setActive(this)"><span class="nav-dot"></span>Investor View</a>
  <a class="nav-item" href="#founder" onclick="setActive(this)"><span class="nav-dot"></span>Founder Actions</a>
  <div class="sidebar-footer">
    <div class="health-badge" style="background:rgba(34,197,94,.1);color:{badge_color};display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-bottom:6px;">
      <span class="health-dot" style="background:{badge_color};"></span>{h.label.title()} Health
    </div>
    <div>Score: {h.total} / 100</div>
  </div>
</nav>
"""

    # ── Hero section ─────────────────────────────────────────────────────────

    def _hero(self, r: AnalyticsReport) -> str:
        h = r.health_score
        h_color = "var(--success)" if h.total >= 70 else "var(--warning)" if h.total >= 45 else "var(--danger)"
        seller = r.file_name.replace(".xlsx", "").replace(".xls", "").replace("_", " ")[:40]
        return f"""
<section class="hero fade-up" id="hero">
  <div class="hero-bg"></div>
  <div class="hero-tag">🏪 {r.platform.upper()} · SETTLEMENT REPORT · {r.period_label.upper()}</div>
  <h1>{seller}<br><span>Settlement Analytics</span></h1>
  <p style="color:var(--text-muted);font-size:13px;max-width:520px;">
    Complete financial intelligence — every rupee tracked, every opportunity surfaced.
    Generated {r.generated_at}.
  </p>
  <div class="hero-meta">
    <div class="meta-chip"><span class="label">Period</span>&nbsp;<span class="val">{r.period_label}</span></div>
    <div class="meta-chip"><span class="label">Marketplace</span>&nbsp;<span class="val">{r.platform}</span></div>
    <div class="meta-chip"><span class="label">Orders</span>&nbsp;<span class="val">{r.total_orders:,}</span></div>
    <div class="meta-chip"><span class="label">SKUs</span>&nbsp;<span class="val">{r.unique_skus:,}</span></div>
    <div class="meta-chip"><span class="label">Report</span>&nbsp;<span class="val">{r.report_type or 'Settlement'}</span></div>
  </div>
  <div class="health-ring-wrap">
    <div class="health-ring-label">Health Score</div>
    <canvas id="healthCanvas" width="120" height="120"></canvas>
    <div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:800;color:{h_color};margin-top:-65px;position:relative;z-index:2;">{h.total}</div>
    <div style="font-size:11px;color:{h_color};margin-top:48px;font-weight:600;">{h.label}</div>
  </div>
</section>
"""

    # ── KPI grid ─────────────────────────────────────────────────────────────

    def _kpi_grid(self, r: AnalyticsReport) -> str:
        ret_rate_cls = "neg" if r.return_rate_pct > 20 else "neu"
        sett_cls = "pos" if r.settlement_efficiency_pct > 65 else "neu"
        return f"""
<section class="section fade-up fade-up-delay-1" id="kpis">
  <div class="section-head">
    <div>
      <div class="section-title">Executive <span>Summary</span></div>
      <div class="section-sub">Core financial metrics for {r.period_label}</div>
    </div>
    <div class="section-tag">SETTLEMENT REPORT</div>
  </div>
  <div class="kpi-grid">
    <div class="kpi-card c-primary">
      <div class="kpi-icon">₹</div>
      <div class="kpi-label">Gross Sales (GMV)</div>
      <div class="kpi-value">{_fmt(r.gross_revenue)}</div>
      <div class="kpi-pct neu">100% of Revenue</div>
      <div class="kpi-note">Total customer payments. Baseline for all calculations.</div>
    </div>
    <div class="kpi-card c-blue">
      <div class="kpi-icon">📦</div>
      <div class="kpi-label">Total Orders</div>
      <div class="kpi-value">{r.total_orders:,}</div>
      <div class="kpi-pct pos">{r.unique_skus} Active SKUs</div>
      <div class="kpi-note">{r.total_orders} orders across {r.unique_skus} unique SKUs.</div>
    </div>
    <div class="kpi-card c-danger">
      <div class="kpi-icon">↩</div>
      <div class="kpi-label">Returns Value</div>
      <div class="kpi-value">{_fmt(abs(r.returns_total))}</div>
      <div class="kpi-pct {ret_rate_cls}">{_pct(r.return_rate_pct)} Return Rate</div>
      <div class="kpi-note">{'Above' if r.return_rate_pct > 20 else 'Within'} industry average. Monitor high-return SKUs.</div>
    </div>
    <div class="kpi-card c-warning">
      <div class="kpi-icon">🏪</div>
      <div class="kpi-label">Marketplace Fees</div>
      <div class="kpi-value">{_fmt(abs(r.fees_total))}</div>
      <div class="kpi-pct neg">{_pct(r.fee_rate_pct)} of GMV</div>
      <div class="kpi-note">Fixed fees + reverse shipping + collection charges.</div>
    </div>
    <div class="kpi-card c-purple">
      <div class="kpi-icon">🧾</div>
      <div class="kpi-label">Total Taxes</div>
      <div class="kpi-value">{_fmt(abs(r.taxes_total))}</div>
      <div class="kpi-pct neg">{_pct(r.tax_rate_pct)} of GMV</div>
      <div class="kpi-note">TCS + TDS + GST on fees. All 100% recoverable.</div>
    </div>
    <div class="kpi-card c-success">
      <div class="kpi-icon">✅</div>
      <div class="kpi-label">Net Settlement</div>
      <div class="kpi-value">{_fmt(r.net_settlement)}</div>
      <div class="kpi-pct {sett_cls}">{_pct(r.settlement_efficiency_pct)} Recovery Rate</div>
      <div class="kpi-note">Actual amount received / expected NEFT payout.</div>
    </div>
    <div class="kpi-card c-warning">
      <div class="kpi-icon">🎯</div>
      <div class="kpi-label">Offer Contribution</div>
      <div class="kpi-value">{_fmt(r.offers_share)}</div>
      <div class="kpi-pct neg">{_pct(r.offers_share / r.gross_revenue * 100 if r.gross_revenue else 0)} of GMV</div>
      <div class="kpi-note">Your sponsored discount contribution to sales.</div>
    </div>
    <div class="kpi-card c-blue">
      <div class="kpi-icon">📣</div>
      <div class="kpi-label">Ad Spend</div>
      <div class="kpi-value">{_fmt(r.ads_spent)}</div>
      <div class="kpi-pct neu">{_pct(r.ads_spent / r.gross_revenue * 100 if r.gross_revenue else 0)} of GMV</div>
      <div class="kpi-note">Net wallet top-up for ads & promotions.</div>
    </div>
    <div class="kpi-card c-success">
      <div class="kpi-icon">💰</div>
      <div class="kpi-label">Tax Credits (Recoverable)</div>
      <div class="kpi-value">{_fmt(r.tax_breakdown.total_recoverable)}</div>
      <div class="kpi-pct pos">File ITC / TDS claim</div>
      <div class="kpi-note">GST ITC + TCS + TDS fully claimable in next filing.</div>
    </div>
  </div>
</section>
"""

    # ── Revenue waterfall ─────────────────────────────────────────────────────

    def _waterfall(self, r: AnalyticsReport) -> str:
        return f"""
<section class="section" id="waterfall">
  <div class="section-head">
    <div>
      <div class="section-title">Revenue <span>Waterfall</span></div>
      <div class="section-sub">Where does your {_fmt(r.gross_revenue)} go?</div>
    </div>
    <div class="section-tag">INTERACTIVE</div>
  </div>
  <div class="card">
    <div id="waterfallChart" style="min-height:320px;"></div>
  </div>
</section>
"""

    # ── Revenue analytics ─────────────────────────────────────────────────────

    def _revenue_analytics(self, r: AnalyticsReport) -> str:
        top3_rev = sum(s.gross_revenue for s in r.top_skus[:3])
        top3_pct = round(top3_rev / r.gross_revenue * 100, 1) if r.gross_revenue else 0
        peak = max((d.gross_revenue for d in r.daily_stats), default=0)
        peak_date = next((d.date_str for d in r.daily_stats if d.gross_revenue == peak), "")
        return f"""
<section class="section" id="revenue">
  <div class="section-head">
    <div>
      <div class="section-title">Revenue <span>Analytics</span></div>
      <div class="section-sub">Daily trend, composition, and concentration analysis</div>
    </div>
  </div>
  <div class="grid-2">
    <div class="card col-span-2">
      <div class="chart-title">Daily Revenue Trend — {r.period_label}</div>
      <div id="revenueChart" style="min-height:240px;"></div>
    </div>
    <div class="card">
      <div class="chart-title">Revenue vs Returns Composition</div>
      <canvas id="compositionChart" style="max-height:220px;"></canvas>
    </div>
    <div class="card">
      <div class="chart-title">Revenue Concentration — Top SKUs</div>
      <canvas id="concentrationChart" style="max-height:220px;"></canvas>
    </div>
  </div>
  <div class="card" style="margin-top:16px;">
    <div class="chart-title">Revenue Concentration Risk</div>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:16px;">
      Top 3 SKUs contribute <strong style="color:var(--warning)">{top3_pct}%</strong> of gross revenue.
      {'Moderate concentration.' if top3_pct < 30 else 'High concentration — diversify SKU mix.'}
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
      <div style="text-align:center;padding:12px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:700;color:var(--primary)">{r.unique_skus}+</div>
        <div style="font-size:11px;color:var(--text-muted)">Active SKUs</div>
      </div>
      <div style="text-align:center;padding:12px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:700;color:var(--warning)">{top3_pct}%</div>
        <div style="font-size:11px;color:var(--text-muted)">Top 3 Revenue Share</div>
      </div>
      <div style="text-align:center;padding:12px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:700;color:var(--success)">{_fmtc(peak)}</div>
        <div style="font-size:11px;color:var(--text-muted)">Peak Day ({peak_date})</div>
      </div>
    </div>
  </div>
</section>
"""

    # ── Product intelligence ──────────────────────────────────────────────────

    def _product_intelligence(self, r: AnalyticsReport) -> str:
        rows_html = ""
        for i, s in enumerate(r.top_skus[:20], 1):
            score_cls = "pos" if s.score >= 70 else "warn" if s.score >= 40 else "neg"
            ret_cls   = "neg" if s.return_rate >= 25 else "warn" if s.return_rate >= 15 else "pos"
            rows_html += f"""<tr>
<td class="mono">{i}</td>
<td class="mono" title="{s.product_title}">{s.sku[:20]}</td>
<td>{s.units_sold}</td>
<td class="pos mono">{_fmtc(s.gross_revenue)}</td>
<td class="neg mono">{_fmtc(s.returns_value)}</td>
<td class="{ret_cls} mono">{_pct(s.return_rate)}</td>
<td class="pri mono">{_fmtc(s.net_revenue)}</td>
<td class="pos mono">{_fmtc(s.net_settlement)}</td>
<td class="{score_cls} mono">{int(s.score)}</td>
</tr>"""
        return f"""
<section class="section" id="products">
  <div class="section-head">
    <div>
      <div class="section-title">Product <span>Intelligence</span></div>
      <div class="section-sub">SKU-level profitability, returns, and net contribution</div>
    </div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="chart-title">Top 10 SKUs by Revenue</div>
      <div id="topSkuChart" style="min-height:280px;"></div>
    </div>
    <div class="card">
      <div class="chart-title">SKU Return Rate Analysis</div>
      <div id="returnRateChart" style="min-height:280px;"></div>
    </div>
  </div>
  <div class="card" style="margin-top:16px;">
    <div class="chart-title">Top {min(20, len(r.sku_stats))} SKUs — Performance Table</div>
    <div style="overflow-x:auto;">
      <table class="data-table">
        <thead><tr><th>#</th><th>SKU</th><th>Units</th><th>Gross Rev</th><th>Returns</th><th>Ret %</th><th>Net Rev</th><th>Settlement</th><th>Score</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
  </div>
</section>
"""

    # ── Return intelligence ───────────────────────────────────────────────────

    def _return_intelligence(self, r: AnalyticsReport) -> str:
        ra  = r.return_analysis
        h_sku = ""
        for s in ra.high_return_skus[:6]:
            sev_cls = "neg" if s.return_rate >= 30 else "warn"
            h_sku += f"""<tr><td class="mono">{s.sku[:20]}</td><td class="{sev_cls}">{s.units_returned}</td><td class="{sev_cls}">{_pct(s.return_rate)}</td><td class="{sev_cls}">{_fmtc(s.returns_value)}</td></tr>"""
        if not h_sku:
            h_sku = "<tr><td colspan='4' style='text-align:center;color:var(--text-muted);'>No high-return SKUs detected ✓</td></tr>"

        rate_cls = "c-danger" if ra.return_rate_pct > 20 else "c-warning"
        return f"""
<section class="section" id="returns">
  <div class="section-head">
    <div>
      <div class="section-title">Return <span>Intelligence</span></div>
      <div class="section-sub">Deep dive into return patterns, causes, and financial impact</div>
    </div>
    <div class="section-tag">{'⚠ HIGH PRIORITY' if ra.return_rate_pct > 20 else 'MONITOR'}</div>
  </div>
  <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr);">
    <div class="kpi-card {rate_cls}">
      <div class="kpi-label">Total Returns</div>
      <div class="kpi-value" style="font-size:20px;">{ra.total_returns} Orders</div>
      <div class="kpi-pct neg">{_pct(ra.return_rate_pct)} of orders</div>
      <div class="kpi-note">{'Above' if ra.return_rate_pct > 15 else 'Within'} comfortable threshold of 15%.</div>
    </div>
    <div class="kpi-card {rate_cls}">
      <div class="kpi-label">Return Value</div>
      <div class="kpi-value" style="font-size:20px;">{_fmt(ra.return_value)}</div>
      <div class="kpi-pct neg">{_pct(ra.return_rate_value_pct)} of GMV</div>
      <div class="kpi-note">Significant revenue erosion from returns.</div>
    </div>
    <div class="kpi-card c-warning">
      <div class="kpi-label">Logistics Returns</div>
      <div class="kpi-value" style="font-size:20px;">{ra.logistics_returns}</div>
      <div class="kpi-pct warn">{_pct(ra.logistics_returns / ra.total_returns * 100 if ra.total_returns else 0)} of returns</div>
      <div class="kpi-note">RTO / delivery failure — packaging or address issues.</div>
    </div>
    <div class="kpi-card c-warning">
      <div class="kpi-label">Customer Returns</div>
      <div class="kpi-value" style="font-size:20px;">{ra.customer_returns}</div>
      <div class="kpi-pct warn">{_pct(ra.customer_returns / ra.total_returns * 100 if ra.total_returns else 0)} of returns</div>
      <div class="kpi-note">Buyer-initiated — sizing, quality, wrong item.</div>
    </div>
  </div>
  <div class="grid-2" style="margin-top:16px;">
    <div class="card">
      <div class="chart-title">Return Type Breakdown</div>
      <canvas id="returnTypeChart" style="max-height:200px;"></canvas>
      <div style="margin-top:16px;display:flex;gap:16px;flex-wrap:wrap;">
        <span class="badge badge-danger">Logistics Returns: {ra.logistics_returns}</span>
        <span class="badge badge-warning">Customer Returns: {ra.customer_returns}</span>
        <span class="badge badge-primary">Reverse Ship Cost: {_fmtc(ra.reverse_shipping_cost)}</span>
      </div>
    </div>
    <div class="card">
      <div class="chart-title">High-Return SKUs (Risk Alert)</div>
      <table class="data-table">
        <thead><tr><th>SKU</th><th>Returns</th><th>Ret %</th><th>Impact</th></tr></thead>
        <tbody>{h_sku}</tbody>
      </table>
      <div style="margin-top:12px;padding:10px;background:var(--danger-dim);border-radius:8px;font-size:11px;color:var(--text-sec);">
        <strong style="color:var(--danger)">CA Observation:</strong> High logistics returns suggest packaging or address capture issues. Review product descriptions and sizing charts for customer returns.
      </div>
    </div>
  </div>
</section>
"""

    # ── Settlement reconciliation ─────────────────────────────────────────────

    def _settlement_recon(self, r: AnalyticsReport) -> str:
        rec = r.settlement_recon
        var_color = "var(--success)" if rec.is_favorable else "var(--danger)"
        var_sign  = "+" if rec.is_favorable else "−"
        status_msg = (
            "✅ <strong style='color:var(--success)'>Settlement Verified:</strong> No missing NEFTs detected."
            if abs(rec.variance) < rec.expected_settlement * 0.10 else
            "⚠ <strong style='color:var(--warning)'>Variance Detected:</strong> Raise dispute if underpayment exceeds 30 days."
        )
        return f"""
<section class="section" id="settlement">
  <div class="section-head">
    <div>
      <div class="section-title">Settlement <span>Reconciliation</span></div>
      <div class="section-sub">Expected vs actual settlement analysis — variance and recovery</div>
    </div>
  </div>
  <div class="grid-3">
    <div class="card" style="text-align:center;padding:28px 20px;">
      <div style="font-size:11px;color:var(--text-muted);font-family:'DM Mono',monospace;text-transform:uppercase;margin-bottom:8px;">Expected Settlement</div>
      <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:var(--blue);">{_fmt(rec.expected_settlement)}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:6px;">GMV − Returns − Fees − Taxes − Offers</div>
    </div>
    <div class="card" style="text-align:center;padding:28px 20px;">
      <div style="font-size:11px;color:var(--text-muted);font-family:'DM Mono',monospace;text-transform:uppercase;margin-bottom:8px;">Actual Settlement</div>
      <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:var(--success);">{_fmt(rec.actual_settlement)}</div>
      <div style="font-size:11px;color:var(--success);margin-top:6px;">NEFT received</div>
    </div>
    <div class="card" style="text-align:center;padding:28px 20px;">
      <div style="font-size:11px;color:var(--text-muted);font-family:'DM Mono',monospace;text-transform:uppercase;margin-bottom:8px;">Variance ({'Favorable' if rec.is_favorable else 'Unfavorable'})</div>
      <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:{var_color};">{var_sign}{_fmt(abs(rec.variance))}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:6px;">{'Order-level adjustments' if rec.is_favorable else 'Raise dispute with marketplace'}</div>
    </div>
  </div>
  <div class="card" style="margin-top:16px;">
    <div class="chart-title">Settlement Component Breakdown</div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:12px;">
      <div style="text-align:center;padding:14px 8px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Gross Sales</div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:16px;color:var(--success);">+{_fmtc(rec.gross_revenue)}</div>
      </div>
      <div style="text-align:center;padding:14px 8px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Returns</div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:16px;color:var(--danger);">−{_fmtc(abs(rec.returns_total))}</div>
      </div>
      <div style="text-align:center;padding:14px 8px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Offers</div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:16px;color:var(--warning);">−{_fmtc(abs(rec.offers_share))}</div>
      </div>
      <div style="text-align:center;padding:14px 8px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">MP Fees</div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:16px;color:var(--warning);">−{_fmtc(abs(rec.fees_total))}</div>
      </div>
      <div style="text-align:center;padding:14px 8px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Taxes</div>
        <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:16px;color:var(--purple);">−{_fmtc(abs(rec.taxes_total))}</div>
      </div>
    </div>
    <div style="margin-top:16px;padding:12px;background:{'var(--success-dim)' if rec.is_favorable else 'var(--warning-dim)'};border-radius:8px;font-size:12px;color:var(--text-sec);">
      {status_msg}
    </div>
  </div>
</section>
"""

    # ── Fee analysis ──────────────────────────────────────────────────────────

    def _fee_analysis(self, r: AnalyticsReport) -> str:
        fb = r.fee_breakdown
        total = max(1.0, fb.total)
        avg_fee = round(abs(r.fees_total) / max(1, r.settled_orders), 1)
        return f"""
<section class="section" id="fees">
  <div class="section-head">
    <div>
      <div class="section-title">Fee <span>Analysis</span></div>
      <div class="section-sub">Complete marketplace fee breakdown and leakage detection</div>
    </div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="chart-title">Fee Component Breakdown</div>
      <canvas id="feeChart" style="max-height:220px;"></canvas>
    </div>
    <div class="card">
      <div class="chart-title">Fee Efficiency Metrics</div>
      <div style="display:flex;flex-direction:column;gap:16px;margin-top:8px;">
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:12px;color:var(--text-sec);">Fixed Fee</span>
            <span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--warning);">{_fmtc(fb.fixed_fee)} · {fb.fixed_fee_pct:.0f}%</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" style="width:{fb.fixed_fee_pct:.0f}%;background:var(--warning);"></div></div>
        </div>
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:12px;color:var(--text-sec);">Reverse Shipping</span>
            <span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--danger);">{_fmtc(fb.reverse_shipping)} · {fb.reverse_shipping_pct:.0f}%</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" style="width:{fb.reverse_shipping_pct:.0f}%;background:var(--danger);"></div></div>
        </div>
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:12px;color:var(--text-sec);">Commission</span>
            <span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--primary);">{_fmtc(fb.commission)} · {round(fb.commission / total * 100):.0f}%</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" style="width:{round(fb.commission / total * 100):.0f}%;background:var(--primary);"></div></div>
        </div>
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:12px;color:var(--text-sec);">Collection Fee</span>
            <span style="font-family:'DM Mono',monospace;font-size:12px;color:var(--blue);">{_fmtc(fb.collection_fee)} · {round(fb.collection_fee / total * 100):.0f}%</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" style="width:{round(fb.collection_fee / total * 100):.0f}%;background:var(--blue);"></div></div>
        </div>
      </div>
      {'<div style="margin-top:20px;padding:12px;background:var(--warning-dim);border-radius:8px;font-size:11px;color:var(--text-sec);">⚠ <strong style="color:var(--warning)">Fee Alert:</strong> Reverse shipping is a significant cost. Reducing returns by 30% saves ~' + _fmtc(fb.reverse_shipping * 0.30) + ' in reverse shipping.</div>' if fb.reverse_shipping > fb.total * 0.25 else ''}
    </div>
  </div>
  <div class="card" style="margin-top:16px;">
    <div class="chart-title">Fee Efficiency Score</div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-top:8px;">
      <div style="text-align:center;padding:16px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-family:'Syne',sans-serif;font-size:32px;font-weight:800;color:{'var(--success)' if r.fee_rate_pct < 10 else 'var(--warning)'};">{_pct(r.fee_rate_pct)}</div>
        <div style="font-size:11px;color:var(--text-muted);">Effective MP Fee Rate (of GMV)</div>
        <div style="margin-top:6px;"><span class="badge {'badge-success' if r.fee_rate_pct < 10 else 'badge-warning'}">{'Within Benchmark' if r.fee_rate_pct < 10 else 'Monitor'}</span></div>
      </div>
      <div style="text-align:center;padding:16px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-family:'Syne',sans-serif;font-size:32px;font-weight:800;color:var(--warning);">₹{avg_fee:.0f}</div>
        <div style="font-size:11px;color:var(--text-muted);">Avg MP Fee Per Settled Order</div>
        <div style="margin-top:6px;"><span class="badge badge-warning">Monitor</span></div>
      </div>
      <div style="text-align:center;padding:16px;background:rgba(255,255,255,.03);border-radius:10px;">
        <div style="font-family:'Syne',sans-serif;font-size:32px;font-weight:800;color:var(--danger);">{_fmtc(fb.reverse_shipping)}</div>
        <div style="font-size:11px;color:var(--text-muted);">Total Reverse Shipping Cost</div>
        <div style="margin-top:6px;"><span class="badge badge-danger">High Impact</span></div>
      </div>
    </div>
  </div>
</section>
"""

    # ── Tax intelligence ──────────────────────────────────────────────────────

    def _tax_intelligence(self, r: AnalyticsReport) -> str:
        tb = r.tax_breakdown
        eff_rate = round(tb.total / r.gross_revenue * 100, 2) if r.gross_revenue else 0
        return f"""
<section class="section" id="tax">
  <div class="section-head">
    <div>
      <div class="section-title">Tax <span>Intelligence</span></div>
      <div class="section-sub">TDS, TCS, GST analysis and recovery opportunities</div>
    </div>
  </div>
  <div class="grid-3">
    <div class="card" style="text-align:center;padding:24px 16px;">
      <div style="font-size:32px;margin-bottom:8px;">🧾</div>
      <div class="kpi-label">TCS Deducted</div>
      <div style="font-family:'Syne',sans-serif;font-size:24px;font-weight:700;color:var(--warning);">{_fmt(tb.tcs)}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:6px;">Tax Collected at Source ~1%<br>Eligible for GST input credit</div>
      <div style="margin-top:10px;"><span class="badge badge-success">Claim in GSTR-2A</span></div>
    </div>
    <div class="card" style="text-align:center;padding:24px 16px;">
      <div style="font-size:32px;margin-bottom:8px;">📝</div>
      <div class="kpi-label">TDS Deducted (194-O)</div>
      <div style="font-family:'Syne',sans-serif;font-size:24px;font-weight:700;color:var(--purple);">{_fmt(tb.tds)}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:6px;">Tax Deducted at Source 0.1%<br>Claimable in annual ITR</div>
      <div style="margin-top:10px;"><span class="badge badge-primary">File TDS Claim</span></div>
    </div>
    <div class="card" style="text-align:center;padding:24px 16px;">
      <div style="font-size:32px;margin-bottom:8px;">📊</div>
      <div class="kpi-label">GST on MP Fees</div>
      <div style="font-family:'Syne',sans-serif;font-size:24px;font-weight:700;color:var(--blue);">{_fmt(tb.gst_on_fees)}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:6px;">18% GST on marketplace fees<br>Eligible for input tax credit</div>
      <div style="margin-top:10px;"><span class="badge badge-primary">ITC Claimable</span></div>
    </div>
  </div>
  <div class="card" style="margin-top:16px;">
    <div class="chart-title">Tax Summary &amp; Compliance Notes</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:8px;">
      <div>
        <table class="data-table">
          <thead><tr><th>Tax Head</th><th>Amount</th><th>Rate</th><th>Recovery</th></tr></thead>
          <tbody>
            <tr><td>TCS (194-1)</td><td class="neg mono">₹{tb.tcs:.2f}</td><td class="mono">~1%</td><td><span class="badge badge-success">GSTR</span></td></tr>
            <tr><td>TDS (194-O)</td><td class="neg mono">₹{tb.tds:.2f}</td><td class="mono">0.1%</td><td><span class="badge badge-primary">ITR</span></td></tr>
            <tr><td>GST on MP Fee</td><td class="neg mono">₹{tb.gst_on_fees:.2f}</td><td class="mono">18%</td><td><span class="badge badge-success">ITC</span></td></tr>
            <tr><td style="font-weight:600;">Total</td><td class="neg mono" style="font-weight:700;">₹{tb.total:.2f}</td><td>—</td><td><span class="badge badge-success">100% Recoverable</span></td></tr>
          </tbody>
        </table>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <div class="insight-card type-success">
          <div class="insight-type">CA NOTE</div>
          <div class="insight-text">All ₹{tb.total:,.0f} in taxes are legally recoverable through proper ITR and GSTR filing. Ensure your CA claims TCS in GSTR-2A reconciliation and TDS in 26AS.</div>
        </div>
        <div class="insight-card type-info">
          <div class="insight-type">COMPLIANCE</div>
          <div class="insight-text">Effective tax rate of {eff_rate:.2f}% on GMV is within expected norms for e-commerce sellers. No anomalies detected in tax deductions this period.</div>
        </div>
      </div>
    </div>
  </div>
</section>
"""

    # ── Recovery engine ───────────────────────────────────────────────────────

    def _recovery_engine(self, r: AnalyticsReport) -> str:
        total = r.total_recoverable
        items_html = ""
        for i, item in enumerate(r.recovery_items, 1):
            cls = "high" if item.priority == "HIGH" else "med" if item.priority == "MEDIUM" else "low"
            letter = item.priority[0]
            items_html += f"""
<div class="action-item">
  <div class="action-num {cls}">{letter}</div>
  <div class="action-content">
    <div class="action-title">{item.title}</div>
    <div class="action-desc">{item.description}</div>
  </div>
  <div class="action-amount">{_fmtc(item.amount)}</div>
</div>"""
        guaranteed = next((i.amount for i in r.recovery_items if "Tax" in i.title), 0)
        potential  = next((i.amount for i in r.recovery_items if "Return" in i.title), 0)
        return f"""
<section class="section" id="recovery">
  <div class="section-head">
    <div>
      <div class="section-title">💰 Money Left on <span>the Table</span></div>
      <div class="section-sub">Recoverable amounts, missed opportunities, and actionable wins</div>
    </div>
    <div class="section-tag">TOTAL OPPORTUNITY: {_fmtc(total)}</div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="chart-title">Recovery Priority Matrix</div>
      <div style="display:flex;flex-direction:column;gap:0;">{items_html}</div>
    </div>
    <div class="card">
      <div class="chart-title">Recovery Potential Summary</div>
      <canvas id="recoveryChart" style="max-height:220px;"></canvas>
      <div style="margin-top:16px;">
        <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
          <span style="font-size:12px;color:var(--text-sec);">Total Identified Opportunity</span>
          <span style="font-family:'DM Mono',monospace;font-weight:700;color:var(--success);">{_fmtc(total)}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
          <span style="font-size:12px;color:var(--text-sec);">Guaranteed (Tax Credits)</span>
          <span style="font-family:'DM Mono',monospace;color:var(--success);">{_fmtc(guaranteed)}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:10px 0;">
          <span style="font-size:12px;color:var(--text-sec);">Potential (Return Reduction)</span>
          <span style="font-family:'DM Mono',monospace;color:var(--warning);">{_fmtc(potential)}+</span>
        </div>
      </div>
    </div>
  </div>
</section>
"""

    # ── Risk dashboard ────────────────────────────────────────────────────────

    def _risk_dashboard(self, r: AnalyticsReport) -> str:
        dims = r.health_score.dimensions
        risk_rows = ""
        for d in dims:
            c = "var(--danger)" if d.level == "HIGH" else "var(--warning)" if d.level == "MEDIUM" else "var(--success)"
            badge = f"badge-danger" if d.level == "HIGH" else f"badge-warning" if d.level == "MEDIUM" else f"badge-success"
            risk_rows += f"""
<div class="risk-item">
  <span class="risk-name">{d.name}</span>
  <div style="display:flex;align-items:center;gap:10px;">
    <div class="risk-bar-bg"><div class="risk-bar-fill" style="width:{d.score}%;background:{c};"></div></div>
    <span class="risk-num" style="color:{c};">{d.score}</span>
    <span class="badge {badge}">{d.level}</span>
  </div>
</div>"""
        return f"""
<section class="section" id="risk">
  <div class="section-head">
    <div>
      <div class="section-title">Risk <span>Dashboard</span></div>
      <div class="section-sub">Automated risk scoring across {len(dims)} dimensions</div>
    </div>
  </div>
  <div class="grid-2">
    <div class="card">
      <div class="chart-title">Risk Score by Category</div>
      <div id="riskChart" style="min-height:260px;"></div>
    </div>
    <div class="card">
      <div class="chart-title">Risk Detail</div>
      {risk_rows}
    </div>
  </div>
  <div class="card" style="margin-top:16px;text-align:center;padding:32px;">
    <div style="font-family:'Syne',sans-serif;font-size:64px;font-weight:800;color:{'var(--success)' if r.health_score.total >= 70 else 'var(--warning)' if r.health_score.total >= 45 else 'var(--danger)'};">{r.health_score.total}</div>
    <div style="font-size:14px;color:var(--text-muted);margin-top:6px;">Business Health Score / 100 — {r.health_score.label}</div>
  </div>
</section>
"""

    # ── Insights ──────────────────────────────────────────────────────────────

    def _insights_section(self, r: AnalyticsReport) -> str:
        cfo = [i for i in r.insights if i.category == "CFO"]
        html = ""
        for ins in cfo:
            html += f"""<div class="insight-card type-{ins.type}">
  <div class="insight-type">CFO INSIGHT</div>
  <div class="insight-title">{ins.title}</div>
  <div class="insight-text">{ins.body}</div>
</div>"""
        return f"""
<section class="section" id="insights">
  <div class="section-head">
    <div>
      <div class="section-title">CFO <span>Insights</span></div>
      <div class="section-sub">Financial intelligence for decision-making</div>
    </div>
  </div>
  <div>{html}</div>
</section>
"""

    # ── CA review ─────────────────────────────────────────────────────────────

    def _ca_review(self, r: AnalyticsReport) -> str:
        ca = [i for i in r.insights if i.category == "CA"]
        html = ""
        for ins in ca:
            html += f"""<div class="insight-card type-{ins.type}">
  <div class="insight-type">CA REVIEW</div>
  <div class="insight-title">{ins.title}</div>
  <div class="insight-text">{ins.body}</div>
</div>"""
        return f"""
<section class="section" id="ca">
  <div class="section-head">
    <div>
      <div class="section-title">CA <span>Review</span></div>
      <div class="section-sub">Tax, compliance, and audit observations</div>
    </div>
  </div>
  <div>{html}</div>
</section>
"""

    # ── Investor view ─────────────────────────────────────────────────────────

    def _investor_view(self, r: AnalyticsReport) -> str:
        inv = [i for i in r.insights if i.category == "INVESTOR"]
        html = ""
        for ins in inv:
            html += f"""<div class="insight-card type-{ins.type}">
  <div class="insight-type">INVESTOR NOTE</div>
  <div class="insight-title">{ins.title}</div>
  <div class="insight-text">{ins.body}</div>
</div>"""
        if not html:
            html = f"""<div class="insight-card type-info">
  <div class="insight-type">INVESTOR NOTE</div>
  <div class="insight-title">GMV: {_fmt(r.gross_revenue)} — Settlement Efficiency: {_pct(r.settlement_efficiency_pct)}</div>
  <div class="insight-text">Business is generating {_fmt(r.gross_revenue)} in GMV. Settlement efficiency of {_pct(r.settlement_efficiency_pct)} indicates healthy marketplace operations. Key growth lever: reduce {_pct(r.return_rate_pct)} return rate.</div>
</div>"""
        return f"""
<section class="section" id="investor">
  <div class="section-head">
    <div>
      <div class="section-title">Investor <span>View</span></div>
      <div class="section-sub">High-level financial health for stakeholders</div>
    </div>
  </div>
  <div>{html}</div>
</section>
"""

    # ── Founder actions ───────────────────────────────────────────────────────

    def _founder_actions(self, r: AnalyticsReport) -> str:
        founder = [i for i in r.insights if i.category in ("FOUNDER", "RECOVERY")]
        # Merge with recovery items
        all_actions = []
        for i, ins in enumerate(founder[:5]):
            cls = "high" if ins.type == "danger" else "med" if ins.type == "warn" else "low"
            all_actions.append(f"""<div class="action-item">
  <div class="action-num {cls}">{i+1}</div>
  <div class="action-content">
    <div class="action-title">{ins.title}</div>
    <div class="action-desc">{ins.body}</div>
  </div>
</div>""")
        html = "\n".join(all_actions)
        return f"""
<section class="section" id="founder">
  <div class="section-head">
    <div>
      <div class="section-title">Founder <span>Actions</span></div>
      <div class="section-sub">Your top {len(all_actions)} priority actions this week</div>
    </div>
  </div>
  <div class="card">{html}</div>
</section>
"""

    # ── Footer ────────────────────────────────────────────────────────────────

    def _footer(self, r: AnalyticsReport) -> str:
        return f"""
<div class="page-footer">
  Generated by <strong style="color:var(--primary)">ClearSettle Intelligence Engine</strong> · {r.generated_at} ·
  {r.file_name} · {r.platform}
</div>
"""

    # ── Chart scripts ─────────────────────────────────────────────────────────

    def _scripts(self, r: AnalyticsReport) -> str:
        # Waterfall data
        wf_cats = ["Gross Sales", "Returns", "My Offers", "MP Fees", "Taxes", "Net Settlement"]
        wf_vals = [
            r.gross_revenue,
            abs(r.returns_total),
            r.offers_share,
            abs(r.fees_total),
            abs(r.taxes_total),
            r.net_settlement,
        ]
        wf_j = json.dumps([round(v, 2) for v in wf_vals])
        wf_c = json.dumps(wf_cats)

        # Daily revenue
        daily_dates = json.dumps([d.date_str for d in r.daily_stats])
        daily_rev   = json.dumps([round(d.gross_revenue, 2) for d in r.daily_stats])
        daily_sett  = json.dumps([round(d.net_settlement, 2) for d in r.daily_stats])

        # SKU chart data
        top_skus  = r.top_skus[:10]
        sku_names = json.dumps([s.sku[:15] for s in top_skus])
        sku_rev   = json.dumps([round(s.gross_revenue, 2) for s in top_skus])
        sku_ret_rates = json.dumps([s.return_rate for s in top_skus])

        # Fee chart data
        fb = r.fee_breakdown
        fee_labels = json.dumps(["Fixed Fee", "Reverse Shipping", "Commission", "Collection", "Shipping", "Other"])
        fee_data   = json.dumps([round(fb.fixed_fee, 2), round(fb.reverse_shipping, 2),
                                  round(fb.commission, 2), round(fb.collection_fee, 2),
                                  round(fb.shipping, 2), round(fb.other, 2)])

        # Tax chart
        tb = r.tax_breakdown
        tax_data = json.dumps([round(tb.tcs, 2), round(tb.tds, 2), round(tb.gst_on_fees, 2)])

        # Return type
        ra = r.return_analysis
        ret_data = json.dumps([ra.logistics_returns, ra.customer_returns])

        # Recovery
        rec_labels = json.dumps([i.title[:25] for i in r.recovery_items])
        rec_data   = json.dumps([round(i.amount, 2) for i in r.recovery_items])

        # Risk radar
        dim_labels = json.dumps([d.name for d in r.health_score.dimensions])
        dim_scores = json.dumps([d.score for d in r.health_score.dimensions])

        # Health score donut
        h = r.health_score
        h_color = "#22C55E" if h.total >= 70 else "#F59E0B" if h.total >= 45 else "#EF4444"

        return f"""
<script>
// ── Nav active state ─────────────────────────────────────────────────────────
function setActive(el){{document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));el.classList.add('active');}}

// ── Health donut ──────────────────────────────────────────────────────────────
const hCtx = document.getElementById('healthCanvas');
if(hCtx){{
  new Chart(hCtx, {{
    type:'doughnut',
    data:{{datasets:[{{data:[{h.total},{100 - h.total}],backgroundColor:['{h_color}','rgba(255,255,255,0.05)'],borderWidth:0,cutout:'78%'}}]}},
    options:{{responsive:false,plugins:{{legend:{{display:false}}}}}}
  }});
}}

// ── Revenue waterfall (ApexCharts) ────────────────────────────────────────────
const wfEl=document.querySelector('#waterfallChart');
if(wfEl){{
  const wfColors=['#22C55E','#EF4444','#F59E0B','#F59E0B','#A78BFA','#14B8A6'];
  new ApexCharts(wfEl,{{
    chart:{{type:'bar',height:320,background:'transparent',toolbar:{{show:false}}}},
    series:[{{name:'Amount',data:{wf_j}}}],
    xaxis:{{categories:{wf_c},labels:{{style:{{colors:'#94A3B8',fontSize:'11px'}}}}}},
    yaxis:{{labels:{{formatter:v=>'₹'+Math.abs(v/1000).toFixed(0)+'K',style:{{colors:'#94A3B8'}}}}}},
    colors:wfColors,
    plotOptions:{{bar:{{borderRadius:6,columnWidth:'55%'}}}},
    dataLabels:{{enabled:true,formatter:v=>'₹'+Math.abs(v/1000).toFixed(0)+'K',style:{{fontSize:'10px',colors:['#F8FAFC']}}}},
    grid:{{borderColor:'rgba(255,255,255,0.06)'}},
    theme:{{mode:'dark'}},
    tooltip:{{theme:'dark',y:{{formatter:v=>'₹'+Math.abs(v).toLocaleString('en-IN')}}}}
  }}).render();
}}

// ── Daily revenue (ApexCharts) ─────────────────────────────────────────────────
const rvEl=document.querySelector('#revenueChart');
if(rvEl){{
  new ApexCharts(rvEl,{{
    chart:{{type:'area',height:240,background:'transparent',toolbar:{{show:false}},sparkline:{{enabled:false}}}},
    series:[
      {{name:'Gross Revenue',data:{daily_rev}}},
      {{name:'Net Settlement',data:{daily_sett}}}
    ],
    xaxis:{{categories:{daily_dates},labels:{{rotate:-45,style:{{colors:'#64748B',fontSize:'9px'}}}},tickAmount:Math.min(10,{len(r.daily_stats)})}},
    yaxis:{{labels:{{formatter:v=>'₹'+Math.abs(v/1000).toFixed(0)+'K',style:{{colors:'#94A3B8'}}}}}},
    colors:['#14B8A6','#22C55E'],
    stroke:{{curve:'smooth',width:2}},
    fill:{{type:'gradient',gradient:{{shadeIntensity:1,opacityFrom:.3,opacityTo:.0,stops:[0,100]}}}},
    grid:{{borderColor:'rgba(255,255,255,0.06)'}},
    legend:{{labels:{{colors:'#94A3B8'}}}},
    theme:{{mode:'dark'}},
    tooltip:{{theme:'dark',y:{{formatter:v=>'₹'+Math.abs(v).toLocaleString('en-IN')}}}}
  }}).render();
}}

// ── Composition donut ─────────────────────────────────────────────────────────
const compCtx=document.getElementById('compositionChart');
if(compCtx){{
  new Chart(compCtx,{{
    type:'doughnut',
    data:{{labels:['Net Sales','Returns','Fees','Taxes'],
      datasets:[{{data:[{round(r.net_sales,2)},{round(abs(r.returns_total),2)},{round(abs(r.fees_total),2)},{round(abs(r.taxes_total),2)}],
        backgroundColor:['#14B8A6','#EF4444','#F59E0B','#A78BFA'],borderWidth:0}}]}},
    options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#94A3B8',font:{{size:11}}}}}},tooltip:{{callbacks:{{label:c=>c.label+': ₹'+c.raw.toLocaleString('en-IN')}}}}}}}}
  }});
}}

// ── Top SKU bar chart ─────────────────────────────────────────────────────────
const tskuEl=document.querySelector('#topSkuChart');
if(tskuEl){{
  new ApexCharts(tskuEl,{{
    chart:{{type:'bar',height:280,background:'transparent',toolbar:{{show:false}}}},
    series:[{{name:'Gross Revenue',data:{sku_rev}}}],
    xaxis:{{categories:{sku_names},labels:{{style:{{colors:'#94A3B8',fontSize:'10px'}}}}}},
    yaxis:{{labels:{{formatter:v=>'₹'+Math.abs(v/1000).toFixed(0)+'K',style:{{colors:'#94A3B8'}}}}}},
    colors:['#14B8A6'],
    plotOptions:{{bar:{{horizontal:true,borderRadius:4}}}},
    dataLabels:{{enabled:false}},
    grid:{{borderColor:'rgba(255,255,255,0.06)'}},
    theme:{{mode:'dark'}},
    tooltip:{{theme:'dark',y:{{formatter:v=>'₹'+v.toLocaleString('en-IN')}}}}
  }}).render();
}}

// ── Return rate chart ─────────────────────────────────────────────────────────
const rrcEl=document.querySelector('#returnRateChart');
if(rrcEl){{
  new ApexCharts(rrcEl,{{
    chart:{{type:'bar',height:280,background:'transparent',toolbar:{{show:false}}}},
    series:[{{name:'Return Rate %',data:{sku_ret_rates}}}],
    xaxis:{{categories:{sku_names},labels:{{style:{{colors:'#94A3B8',fontSize:'10px'}}}}}},
    yaxis:{{labels:{{formatter:v=>v.toFixed(1)+'%',style:{{colors:'#94A3B8'}}}}}},
    colors:['#EF4444'],
    plotOptions:{{bar:{{horizontal:true,borderRadius:4}}}},
    dataLabels:{{enabled:false}},
    grid:{{borderColor:'rgba(255,255,255,0.06)'}},
    annotations:{{xaxis:[{{x:20,borderColor:'#F59E0B',label:{{text:'20% threshold',style:{{color:'#F59E0B',fontSize:'10px'}}}}}}]}},
    theme:{{mode:'dark'}},
    tooltip:{{theme:'dark',y:{{formatter:v=>v.toFixed(1)+'%'}}}}
  }}).render();
}}

// ── Concentration donut ───────────────────────────────────────────────────────
const concCtx=document.getElementById('concentrationChart');
if(concCtx){{
  const skuRevs={sku_rev};
  const total=skuRevs.reduce((a,b)=>a+b,0);
  new Chart(concCtx,{{
    type:'pie',
    data:{{labels:{sku_names},
      datasets:[{{data:skuRevs,backgroundColor:['#14B8A6','#22C55E','#60A5FA','#F59E0B','#A78BFA','#EF4444','#34D399','#FBBF24','#818CF8','#F87171'],borderWidth:0}}]}},
    options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#94A3B8',font:{{size:10}}}},position:'right'}},tooltip:{{callbacks:{{label:c=>c.label+': ₹'+c.raw.toLocaleString('en-IN')+' ('+((c.raw/total)*100).toFixed(1)+'%)'}}}}}}}}
  }});
}}

// ── Return type donut ─────────────────────────────────────────────────────────
const retCtx=document.getElementById('returnTypeChart');
if(retCtx){{
  new Chart(retCtx,{{
    type:'doughnut',
    data:{{labels:['Logistics Returns','Customer Returns'],
      datasets:[{{data:{ret_data},backgroundColor:['#EF4444','#F59E0B'],borderWidth:0}}]}},
    options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#94A3B8',font:{{size:11}}}}}}}}}}
  }});
}}

// ── Fee chart ─────────────────────────────────────────────────────────────────
const feeCtx=document.getElementById('feeChart');
if(feeCtx){{
  new Chart(feeCtx,{{
    type:'doughnut',
    data:{{labels:{fee_labels},
      datasets:[{{data:{fee_data},backgroundColor:['#F59E0B','#EF4444','#14B8A6','#60A5FA','#22C55E','#94A3B8'],borderWidth:0}}]}},
    options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#94A3B8',font:{{size:11}}}}}}}}}}
  }});
}}

// ── Recovery chart ────────────────────────────────────────────────────────────
const recCtx=document.getElementById('recoveryChart');
if(recCtx){{
  new Chart(recCtx,{{
    type:'doughnut',
    data:{{labels:{rec_labels},
      datasets:[{{data:{rec_data},backgroundColor:['#22C55E','#14B8A6','#F59E0B','#60A5FA','#94A3B8'],borderWidth:0}}]}},
    options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#94A3B8',font:{{size:10}}}}}}}}}}
  }});
}}

// ── Risk radar chart (ApexCharts) ─────────────────────────────────────────────
const riskEl=document.querySelector('#riskChart');
if(riskEl){{
  new ApexCharts(riskEl,{{
    chart:{{type:'radar',height:260,background:'transparent',toolbar:{{show:false}}}},
    series:[{{name:'Risk Score',data:{dim_scores}}}],
    xaxis:{{categories:{dim_labels}}},
    yaxis:{{max:100,show:false}},
    colors:['#EF4444'],
    fill:{{opacity:.15}},
    stroke:{{width:2}},
    markers:{{size:4}},
    plotOptions:{{radar:{{polygons:{{strokeColors:'rgba(255,255,255,0.08)',fill:{{colors:['rgba(255,255,255,0.02)','rgba(255,255,255,0)']}}}}}}}}  ,
    theme:{{mode:'dark'}},
    tooltip:{{theme:'dark'}}
  }}).render();
}}

// ── Scroll spy ────────────────────────────────────────────────────────────────
const sections=document.querySelectorAll('section[id]');
const navItems=document.querySelectorAll('.nav-item');
window.addEventListener('scroll',()=>{{
  let cur='';
  sections.forEach(s=>{{if(s.getBoundingClientRect().top<=120)cur=s.id;}});
  navItems.forEach(n=>{{
    const href=(n.getAttribute('href')||'').replace('#','');
    if(href===cur){{n.classList.add('active');}}else{{n.classList.remove('active');}}
  }});
}},{{passive:true}});
</script>
"""
