import React from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import useApi from '../hooks/useApi'
import useUIStore from '../store/uiStore'
import { INRL, INR } from '../utils/format'

var PLATFORM_COLORS = {
  amazon:   '#FF9900',
  flipkart: '#2874F0',
  meesho:   '#9B1FE8',
  myntra:   '#FF3E6C',
  nykaa:    '#FC2779',
  ajio:     '#1F1F1F',
  snapdeal: '#E40000',
  jiomart:  '#0E7340',
}

var PLATFORM_ICONS = {
  amazon:   '🛒',
  flipkart: '🛍️',
  meesho:   '👗',
  myntra:   '👠',
  nykaa:    '💄',
  ajio:     '👔',
  snapdeal: '🏷️',
  jiomart:  '🛒',
}

function fmtDate(iso) {
  var d = new Date(iso)
  return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
}

function EmptyState({ text }) {
  return (
    <div style={{ textAlign: 'center', color: '#8FA5BD', fontSize: 13, padding: '52px 0' }}>
      {text}
    </div>
  )
}

function Dashboard() {
  var { data, loading } = useApi('/dashboard/summary')
  var navigate = useNavigate()
  var addToast = useUIStore(function(s) { return s.addToast })

  if (loading || !data) {
    return (
      <div className="loading-wrap page-anim">
        <div className="spinner" />
      </div>
    )
  }

  var s   = data.settlements    || {}
  var pay = data.payouts         || {}
  var r   = data.reconciliation  || {}

  var trend = (data.revenue_trend || []).map(function(t) {
    return { gross: t.gross, net: t.net, label: fmtDate(t.date) }
  })

  var share = (data.platform_share || []).map(function(ps) {
    return {
      platform: ps.platform,
      label:    ps.label,
      value:    ps.share_pct,
      color:    PLATFORM_COLORS[ps.platform] || '#8FA5BD',
    }
  })

  var reconHealth = r.total_runs > 0
    ? Math.round((r.clean || 0) / r.total_runs * 100)
    : 100

  return (
    <div className="page page-anim">

      {/* Discrepancy alert banner */}
      {(r.unresolved_discrepancies || 0) > 0 && (
        <div className="ab warn" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 18 }}>⚠️</span>
          <div className="ab-body">
            <div className="ab-title">
              {r.unresolved_discrepancies} unresolved discrepanc{r.unresolved_discrepancies === 1 ? 'y' : 'ies'} —{' '}
              {INR(r.total_variance || 0)} variance
            </div>
            <div className="ab-sub">Review reconciliation results to recover overcharges</div>
          </div>
          <div className="ab-act">
            <button className="btn btn-s btn-sm" onClick={function() { navigate('/disputes') }}>
              Review →
            </button>
          </div>
        </div>
      )}

      {/* Primary KPI cards */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        {[
          {
            label:  'Total GMV',
            val:    INRL(s.total_gross || 0),
            sub:    (s.total || 0) + ' settlements',
            stripe: 'tl',
          },
          {
            label:  'Total Paid Out',
            val:    INRL(s.total_net_paid || 0),
            sub:    (s.closed_count || 0) + ' closed',
            stripe: 'gn',
          },
          {
            label:  'Pending Payout',
            val:    INRL(s.pending_amount || 0),
            sub:    ((s.open_count || 0) + (s.processing_count || 0)) + ' in progress',
            stripe: 'am',
          },
          {
            label:  'Platform Fees',
            val:    INRL(Math.abs(s.total_fees || 0)),
            sub:    'Total deductions',
            stripe: 'rd',
          },
        ].map(function(k) {
          return (
            <div key={k.label} className="stat-card">
              <div className={'sc-stripe ' + k.stripe} />
              <div className="sc-label" style={{ marginTop: 8 }}>{k.label}</div>
              <div className="sc-val">{k.val}</div>
              <div className="sc-sub">{k.sub}</div>
            </div>
          )
        })}
      </div>

      {/* Secondary metric cards */}
      <div className="kpi-grid" style={{ marginBottom: 28 }}>
        {[
          {
            label: 'Total Orders',
            val:   (s.total_orders || 0).toLocaleString('en-IN'),
            red:   false,
          },
          {
            label: 'Payout Transferred',
            val:   INRL(pay.transferred || 0),
            red:   false,
          },
          {
            label: 'Recon Health',
            val:   reconHealth + '%',
            red:   reconHealth < 80,
          },
          {
            label: 'Unresolved Issues',
            val:   (r.unresolved_discrepancies || 0).toString(),
            red:   (r.unresolved_discrepancies || 0) > 0,
          },
        ].map(function(m) {
          return (
            <div key={m.label} className="card" style={{ padding: '16px 18px' }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8FA5BD', marginBottom: 6 }}>
                {m.label}
              </div>
              <div style={{ fontSize: 20, fontWeight: 800, color: m.red ? '#E8344A' : '#0D1F35' }}>
                {m.val}
              </div>
            </div>
          )
        })}
      </div>

      {/* Charts row */}
      <div className="two-col-wide">

        {/* Revenue trend bar chart */}
        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-title">Revenue Trend</div>
              <div className="card-sub">Gross vs net — last 30 days</div>
            </div>
          </div>
          <div className="card-bd">
            {trend.length === 0
              ? <EmptyState text="No settlement data in the last 30 days" />
              : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={trend} barSize={20} barGap={2}>
                    <XAxis
                      dataKey="label"
                      axisLine={false} tickLine={false}
                      tick={{ fontSize: 11, fill: '#8FA5BD' }}
                      interval="preserveStartEnd"
                    />
                    <YAxis hide />
                    <Tooltip
                      formatter={function(v, name) {
                        return [INRL(v), name === 'gross' ? 'Gross' : 'Net']
                      }}
                      contentStyle={{ borderRadius: 10, fontSize: 12 }}
                    />
                    <Bar dataKey="gross" radius={[4, 4, 0, 0]} fill="#E2EBF3" name="gross" />
                    <Bar dataKey="net"   radius={[4, 4, 0, 0]} fill="#0ABFCA" name="net" />
                  </BarChart>
                </ResponsiveContainer>
              )
            }
          </div>
        </div>

        {/* Platform share pie chart */}
        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-title">Platform Mix</div>
              <div className="card-sub">GMV share by marketplace</div>
            </div>
          </div>
          <div className="card-bd" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {share.length === 0
              ? <EmptyState text="No platform data yet — connect a marketplace" />
              : (
                <>
                  <ResponsiveContainer width="100%" height={140}>
                    <PieChart>
                      <Pie
                        data={share}
                        cx="50%" cy="50%"
                        innerRadius={40} outerRadius={65}
                        dataKey="value"
                      >
                        {share.map(function(entry, i) {
                          return <Cell key={i} fill={entry.color} />
                        })}
                      </Pie>
                      <Tooltip
                        formatter={function(v, n) { return [v + '%', n] }}
                        contentStyle={{ fontSize: 12 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {share.map(function(item) {
                      return (
                        <div key={item.platform} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 8, height: 8, borderRadius: 2, background: item.color, flexShrink: 0 }} />
                          <span style={{ fontSize: 12, flex: 1, color: '#4B6080' }}>
                            {PLATFORM_ICONS[item.platform] || '🏪'} {item.label}
                          </span>
                          <span style={{ fontSize: 12, fontWeight: 700 }}>{item.value}%</span>
                        </div>
                      )
                    })}
                  </div>
                </>
              )
            }
          </div>
        </div>
      </div>

      {/* Reconciliation summary */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-hd">
          <div>
            <div className="card-title">Reconciliation Overview</div>
            <div className="card-sub">{r.total_runs || 0} total runs · {INR(r.total_variance || 0)} variance flagged</div>
          </div>
          <button className="btn btn-g btn-sm" onClick={function() { navigate('/disputes') }}>
            View all →
          </button>
        </div>
        <div className="card-bd">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'Clean',    val: r.clean    || 0, color: '#0DB07A' },
              { label: 'Warning',  val: r.warning  || 0, color: '#E9930D' },
              { label: 'Critical', val: r.critical || 0, color: '#E8344A' },
              { label: 'Error',    val: r.error    || 0, color: '#8FA5BD' },
            ].map(function(item) {
              return (
                <div
                  key={item.label}
                  style={{
                    textAlign: 'center', padding: '16px 8px',
                    borderRadius: 10, background: '#F8FAFC',
                    border: '1px solid #E2EBF3',
                  }}
                >
                  <div style={{ fontSize: 24, fontWeight: 800, color: item.color }}>{item.val}</div>
                  <div style={{ fontSize: 11, color: '#8FA5BD', textTransform: 'uppercase', fontWeight: 700, marginTop: 4 }}>
                    {item.label}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

    </div>
  )
}

export default Dashboard
