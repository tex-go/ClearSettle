import React, { useState, useEffect, useCallback } from 'react'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import useAuthStore from '../store/authStore'
import _axiosApi from '../utils/api'

// Proxy through the shared axios client (which handles 401 refresh automatically).
// Token parameter is kept for backward-compat with child component calls but is ignored —
// axios interceptor injects the token from localStorage on every request.
function api(_token, path, opts) {
  var method = (opts && opts.method ? opts.method : 'GET').toLowerCase()
  var body = opts && opts.body ? JSON.parse(opts.body) : undefined
  if (method === 'get') return _axiosApi.get(path).then(function(r) { return r.data })
  return _axiosApi[method](path, body).then(function(r) { return r.data })
}

function fmt(n, compact) {
  if (n === null || n === undefined) return '—'
  if (compact) {
    if (Math.abs(n) >= 10000000) return '₹' + (n / 10000000).toFixed(1) + 'Cr'
    if (Math.abs(n) >= 100000)   return '₹' + (n / 100000).toFixed(1) + 'L'
    if (Math.abs(n) >= 1000)     return '₹' + (n / 1000).toFixed(1) + 'K'
  }
  return '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

var RISK_COLOR = { low: '#22C55E', medium: '#F59E0B', high: '#EF4444', critical: '#7F1D1D' }
var RISK_BG    = { low: 'rgba(34,197,94,.1)', medium: 'rgba(245,158,11,.1)', high: 'rgba(239,68,68,.1)', critical: 'rgba(127,29,29,.1)' }

var HORIZON_OPTIONS = [
  { value: '7d',  label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
  { value: '1y',  label: '1 Year' },
]

var INSIGHT_ICONS = { trend: '📈', warning: '⚠️', opportunity: '💡', anomaly: '🔍' }
var INSIGHT_COLORS = {
  info:     { bg: 'rgba(10,191,202,.08)', border: '#0ABFCA', color: '#0ABFCA' },
  warning:  { bg: 'rgba(245,158,11,.08)',  border: '#F59E0B', color: '#E9930D' },
  critical: { bg: 'rgba(239,68,68,.08)',   border: '#EF4444', color: '#EF4444' },
}

function KPICard({ title, value, sub, trend, loading }) {
  var trendColor = trend > 0 ? '#22C55E' : trend < 0 ? '#EF4444' : '#8FA5BD'
  return (
    <div style={{
      background: '#fff', border: '1px solid #E8EEF4', borderRadius: 12,
      padding: '16px 20px', minWidth: 0,
    }}>
      <div style={{ fontSize: 12, color: '#8FA5BD', fontWeight: 600, marginBottom: 6 }}>{title}</div>
      {loading
        ? <div style={{ height: 28, background: '#F1F5F9', borderRadius: 6, width: 120 }} />
        : <div style={{ fontSize: 22, fontWeight: 800, color: '#0D1F35' }}>{value}</div>
      }
      {sub && <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 4 }}>{sub}</div>}
      {trend !== undefined && !loading && (
        <div style={{ fontSize: 12, color: trendColor, fontWeight: 600, marginTop: 4 }}>
          {trend > 0 ? '▲' : trend < 0 ? '▼' : '—'} {Math.abs(trend).toFixed(1)}% vs last month
        </div>
      )}
    </div>
  )
}

function InsightCard({ insight }) {
  var s = INSIGHT_COLORS[insight.severity] || INSIGHT_COLORS.info
  return (
    <div style={{
      background: s.bg, border: '1px solid ' + s.border + '33',
      borderLeft: '3px solid ' + s.border,
      borderRadius: 10, padding: '12px 16px', marginBottom: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize: 16 }}>{INSIGHT_ICONS[insight.type] || '•'}</span>
        <span style={{ fontWeight: 700, color: s.color, fontSize: 13 }}>{insight.title}</span>
        <span style={{
          marginLeft: 'auto', fontSize: 10, fontWeight: 700,
          background: s.border + '22', color: s.border,
          borderRadius: 20, padding: '1px 8px',
        }}>{insight.severity.toUpperCase()}</span>
      </div>
      <div style={{ fontSize: 13, color: '#4B6080', lineHeight: 1.5 }}>{insight.description}</div>
      {insight.action && (
        <div style={{ fontSize: 12, color: s.color, marginTop: 8, fontWeight: 600 }}>
          → {insight.action}
        </div>
      )}
    </div>
  )
}

function ShortageWarning({ points }) {
  var high = points.filter(function(p) { return p.shortage_risk === 'high' || p.shortage_risk === 'critical' })
  if (!high.length) return null
  return (
    <div style={{
      background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.3)',
      borderRadius: 10, padding: '14px 18px', marginBottom: 20,
    }}>
      <div style={{ fontWeight: 700, color: '#EF4444', fontSize: 14, marginBottom: 8 }}>
        ⚠️ Cash Shortage Risk Detected
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {high.map(function(p) {
          return (
            <div key={p.date} style={{
              background: RISK_BG[p.shortage_risk],
              border: '1px solid ' + RISK_COLOR[p.shortage_risk] + '55',
              borderRadius: 8, padding: '4px 12px', fontSize: 12,
              color: RISK_COLOR[p.shortage_risk], fontWeight: 600,
            }}>
              {p.label}: {fmt(p.cumulative_balance, true)}
            </div>
          )
        })}
      </div>
    </div>
  )
}

var CustomTooltip = function({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null
  return (
    <div style={{
      background: '#0D1F35', border: '1px solid rgba(255,255,255,.1)',
      borderRadius: 10, padding: '12px 16px', minWidth: 180,
    }}>
      <div style={{ color: '#8FA5BD', fontSize: 11, marginBottom: 8 }}>{label}</div>
      {payload.map(function(e) {
        return (
          <div key={e.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
            <span style={{ color: e.color, fontSize: 12 }}>{e.name}</span>
            <span style={{ color: '#fff', fontSize: 12, fontWeight: 700 }}>{fmt(e.value, true)}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function CashFlowForecast({ noPadding }) {
  var { token } = useAuthStore()
  var [horizon, setHorizon] = useState('30d')
  var [tab, setTab] = useState('overview')   // overview | projection | insights

  var [summary, setSummary] = useState(null)
  var [projection, setProjection] = useState(null)
  var [insights, setInsights] = useState(null)
  var [snapshots, setSnapshots] = useState([])

  var [loadingSummary, setLoadingSummary] = useState(true)
  var [loadingProjection, setLoadingProjection] = useState(false)
  var [loadingInsights, setLoadingInsights] = useState(false)
  var [generating, setGenerating] = useState(false)
  var [error, setError] = useState(null)

  // Load summary on mount
  useEffect(function() {
    setLoadingSummary(true)
    api(token, '/forecast/summary')
      .then(function(d) { setSummary(d) })
      .catch(function(e) { setError(e.message) })
      .finally(function() { setLoadingSummary(false) })

    api(token, '/forecast/snapshots?period_type=monthly&limit=12')
      .then(function(d) { setSnapshots(d) })
      .catch(function() {})
  }, [token])

  // Load projection when horizon changes
  var loadProjection = useCallback(function() {
    setLoadingProjection(true)
    api(token, '/forecast/projections?horizon=' + horizon)
      .then(function(d) { setProjection(d) })
      .catch(function(e) { setError(e.message) })
      .finally(function() { setLoadingProjection(false) })
  }, [token, horizon])

  useEffect(function() { if (tab === 'projection') loadProjection() }, [tab, horizon, loadProjection])

  // Load insights lazily
  var loadInsights = useCallback(function() {
    if (insights) return
    setLoadingInsights(true)
    api(token, '/forecast/insights?horizon=' + horizon)
      .then(function(d) { setInsights(d) })
      .catch(function(e) { setError(e.message) })
      .finally(function() { setLoadingInsights(false) })
  }, [token, horizon, insights])

  useEffect(function() { if (tab === 'insights') loadInsights() }, [tab, loadInsights])

  function generateSnapshots() {
    setGenerating(true)
    api(token, '/forecast/generate', {
      method: 'POST',
      body: JSON.stringify({ period_type: 'monthly', regenerate: true }),
    })
      .then(function(d) {
        alert('Generated ' + d.snapshots_generated + ' snapshots')
        setSummary(null)
        setLoadingSummary(true)
        return api(token, '/forecast/summary')
      })
      .then(function(d) { setSummary(d) })
      .catch(function(e) { alert('Error: ' + e.message) })
      .finally(function() {
        setGenerating(false)
        setLoadingSummary(false)
      })
  }

  var trend = summary
    ? summary.current_month_inflow > 0 && summary.last_month_inflow > 0
      ? ((summary.current_month_inflow - summary.last_month_inflow) / summary.last_month_inflow) * 100
      : undefined
    : undefined

  // Chart data from snapshots (reversed = ascending)
  var snapshotChartData = snapshots.slice().reverse().map(function(s) {
    return {
      name: s.snapshot_date.substring(0, 7),
      Inflows: s.inflows,
      Outflows: s.outflows,
      Net: s.net_cash_flow,
    }
  })

  var projectionChartData = projection
    ? projection.points.map(function(p) {
        return {
          name:     p.label,
          Inflow:   p.projected_inflow,
          Outflow:  p.projected_outflow,
          Balance:  p.cumulative_balance,
          risk:     p.shortage_risk,
        }
      })
    : []

  return (
    <div style={noPadding ? {} : { padding: '24px 28px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: '#0D1F35', margin: 0 }}>Cash Flow Forecast</h1>
          <div style={{ fontSize: 13, color: '#8FA5BD', marginTop: 2 }}>AI-powered financial projections from your settlement data</div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button onClick={generateSnapshots} disabled={generating} style={{
            padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
            background: generating ? '#F1F5F9' : '#0ABFCA', color: generating ? '#8FA5BD' : '#fff',
            border: 'none',
          }}>
            {generating ? 'Generating…' : '⚡ Refresh Snapshots'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 10, padding: '12px 16px', marginBottom: 20, color: '#EF4444', fontSize: 13 }}>
          {error} — <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={function() { setError(null) }}>dismiss</span>
        </div>
      )}

      {/* KPI Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14, marginBottom: 28 }}>
        <KPICard title="Current Month Inflow"  value={fmt(summary?.current_month_inflow)}  loading={loadingSummary} trend={trend} />
        <KPICard title="Current Month Outflow" value={fmt(summary?.current_month_outflow)} loading={loadingSummary} />
        <KPICard title="Current Month Net"     value={fmt(summary?.current_month_net)}     loading={loadingSummary}
          sub={summary?.current_month_net >= 0 ? 'Positive cash flow' : 'Negative cash flow'} />
        <KPICard title="YTD Inflow"  value={fmt(summary?.ytd_inflow,  true)} loading={loadingSummary} />
        <KPICard title="YTD Net"     value={fmt(summary?.ytd_net,     true)} loading={loadingSummary}
          sub={'as of ' + (summary?.as_of || '—')} />
        <KPICard title="Avg Monthly Inflow" value={fmt(summary?.avg_monthly_inflow, true)} loading={loadingSummary}
          sub="6-month average" />
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '2px solid #E8EEF4', paddingBottom: 0 }}>
        {[['overview', '📊 Overview'], ['projection', '📈 Projection'], ['insights', '🤖 AI Insights']].map(function([k, l]) {
          var active = tab === k
          return (
            <button key={k} onClick={function() { setTab(k) }} style={{
              padding: '9px 18px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              background: 'transparent', color: active ? '#0ABFCA' : '#8FA5BD',
              borderBottom: active ? '2px solid #0ABFCA' : '2px solid transparent',
              marginBottom: -2,
            }}>{l}</button>
          )
        })}
      </div>

      {/* Overview tab — historical snapshot chart */}
      {tab === 'overview' && (
        <div>
          {snapshotChartData.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#8FA5BD' }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>📊</div>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>No snapshot data yet</div>
              <div style={{ fontSize: 13, marginBottom: 16 }}>Click "Refresh Snapshots" to generate aggregates from your settlement data.</div>
            </div>
          ) : (
            <>
              <div style={{ background: '#fff', border: '1px solid #E8EEF4', borderRadius: 14, padding: '20px 24px', marginBottom: 20 }}>
                <div style={{ fontWeight: 700, color: '#0D1F35', fontSize: 15, marginBottom: 16 }}>Monthly Cash Flow History</div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={snapshotChartData} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="name" tick={{ fill: '#8FA5BD', fontSize: 11 }} />
                    <YAxis tickFormatter={function(v) { return fmt(v, true) }} tick={{ fill: '#8FA5BD', fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="Inflows"  fill="#0ABFCA" radius={[4,4,0,0]} />
                    <Bar dataKey="Outflows" fill="#EF4444" radius={[4,4,0,0]} />
                    <Bar dataKey="Net"      fill="#6366F1" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Platform breakdown */}
              {summary?.platform_breakdown && Object.keys(summary.platform_breakdown).length > 0 && (
                <div style={{ background: '#fff', border: '1px solid #E8EEF4', borderRadius: 14, padding: '20px 24px' }}>
                  <div style={{ fontWeight: 700, color: '#0D1F35', fontSize: 15, marginBottom: 14 }}>Platform Breakdown (YTD)</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                    {Object.entries(summary.platform_breakdown).map(function([platform, amount]) {
                      return (
                        <div key={platform} style={{ background: '#F8FAFC', border: '1px solid #E8EEF4', borderRadius: 10, padding: '10px 16px', minWidth: 140 }}>
                          <div style={{ fontSize: 11, color: '#8FA5BD', fontWeight: 600, textTransform: 'uppercase' }}>{platform}</div>
                          <div style={{ fontSize: 18, fontWeight: 800, color: '#0D1F35', marginTop: 4 }}>{fmt(amount, true)}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Projection tab */}
      {tab === 'projection' && (
        <div>
          {/* Horizon selector */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            {HORIZON_OPTIONS.map(function(opt) {
              return (
                <button key={opt.value} onClick={function() { setHorizon(opt.value) }} style={{
                  padding: '7px 16px', borderRadius: 8, border: '1px solid #E8EEF4',
                  background: horizon === opt.value ? '#0ABFCA' : '#fff',
                  color: horizon === opt.value ? '#fff' : '#4B6080',
                  fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}>
                  {opt.label}
                </button>
              )
            })}
          </div>

          {loadingProjection ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#8FA5BD' }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>⏳</div>
              <div>Generating projection…</div>
            </div>
          ) : projection ? (
            <>
              {/* Shortage warnings */}
              <ShortageWarning points={projection.points} />

              {/* Balance projection chart */}
              <div style={{ background: '#fff', border: '1px solid #E8EEF4', borderRadius: 14, padding: '20px 24px', marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div style={{ fontWeight: 700, color: '#0D1F35', fontSize: 15 }}>
                    Projected Balance — {HORIZON_OPTIONS.find(function(o) { return o.value === horizon })?.label}
                  </div>
                  <div style={{ fontSize: 13, color: '#8FA5BD' }}>
                    Current: <strong style={{ color: '#0D1F35' }}>{fmt(projection.current_balance, true)}</strong>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={projectionChartData}>
                    <defs>
                      <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#0ABFCA" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#0ABFCA" stopOpacity={0.02} />
                      </linearGradient>
                      <linearGradient id="inflowGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#22C55E" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#22C55E" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="name" tick={{ fill: '#8FA5BD', fontSize: 10 }} />
                    <YAxis tickFormatter={function(v) { return fmt(v, true) }} tick={{ fill: '#8FA5BD', fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <ReferenceLine y={0} stroke="#EF4444" strokeDasharray="4 4" />
                    <Area type="monotone" dataKey="Balance" name="Cumulative Balance" stroke="#0ABFCA" fill="url(#balanceGrad)" strokeWidth={2} dot={false} />
                    <Area type="monotone" dataKey="Inflow"  name="Projected Inflow"  stroke="#22C55E" fill="url(#inflowGrad)"   strokeWidth={2} dot={false} />
                    <Area type="monotone" dataKey="Outflow" name="Projected Outflow" stroke="#EF4444" fill="none"               strokeWidth={1.5} strokeDasharray="4 2" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Summary row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
                <div style={{ background: '#fff', border: '1px solid #E8EEF4', borderRadius: 12, padding: '14px 18px' }}>
                  <div style={{ fontSize: 12, color: '#8FA5BD', fontWeight: 600, marginBottom: 6 }}>Total Projected Inflow</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#22C55E' }}>{fmt(projection.total_projected_inflow, true)}</div>
                </div>
                <div style={{ background: '#fff', border: '1px solid #E8EEF4', borderRadius: 12, padding: '14px 18px' }}>
                  <div style={{ fontSize: 12, color: '#8FA5BD', fontWeight: 600, marginBottom: 6 }}>Total Projected Outflow</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#EF4444' }}>{fmt(projection.total_projected_outflow, true)}</div>
                </div>
                <div style={{ background: '#fff', border: '1px solid #E8EEF4', borderRadius: 12, padding: '14px 18px' }}>
                  <div style={{ fontSize: 12, color: '#8FA5BD', fontWeight: 600, marginBottom: 6 }}>Net Projection</div>
                  <div style={{
                    fontSize: 20, fontWeight: 800,
                    color: projection.net_projection >= 0 ? '#22C55E' : '#EF4444',
                  }}>
                    {fmt(projection.net_projection, true)}
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Insights tab */}
      {tab === 'insights' && (
        <div>
          {loadingInsights ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#8FA5BD' }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>🤖</div>
              <div>Generating AI insights…</div>
            </div>
          ) : insights ? (
            <>
              <div style={{ fontSize: 12, color: '#8FA5BD', marginBottom: 16 }}>
                Generated by {insights.model_used} · {insights.generated_at?.substring(0, 10)}
                <button onClick={function() { setInsights(null); loadInsights() }} style={{
                  marginLeft: 12, fontSize: 11, color: '#0ABFCA', background: 'none', border: 'none', cursor: 'pointer',
                }}>↻ Refresh</button>
              </div>
              {insights.insights.map(function(ins, i) {
                return <InsightCard key={i} insight={ins} />
              })}
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#8FA5BD' }}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>🤖</div>
              <div style={{ marginBottom: 12 }}>Click to generate AI-powered insights</div>
              <button onClick={loadInsights} style={{
                padding: '10px 24px', background: '#0ABFCA', color: '#fff',
                border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: 'pointer',
              }}>Generate Insights</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
