import React from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import useUIStore from '../store/uiStore'
import { INRL, INR } from '../utils/format'

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

  var alertIcons = { warn: '⚠️', error: '🔴', info: 'ℹ️', ok: '✅' }
  var alertClasses = { warn: 'warn', error: 'err', info: 'inf', ok: 'ok' }

  return (
    <div className="page page-anim">
      {/* Alert banners */}
      {data.alerts.map(function(a, i) {
        return (
          <div key={i} className={'ab ' + alertClasses[a.type]}>
            <span style={{ fontSize: 18 }}>{alertIcons[a.type]}</span>
            <div className="ab-body">
              <div className="ab-title">{a.title}</div>
              <div className="ab-sub">{a.sub}</div>
            </div>
            <div className="ab-act">
              <button
                className="btn btn-s btn-sm"
                onClick={function() { navigate(i === 0 ? '/commission' : '/bank') }}
              >
                {a.action}
              </button>
            </div>
          </div>
        )
      })}

      {/* KPI grid */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total GMV', val: INRL(data.total_gmv), sub: 'All platforms', stripe: 'tl' },
          { label: 'Settlements Received', val: INRL(data.total_net), sub: 'This month', stripe: 'gn' },
          { label: 'Pending Payout', val: INRL(data.pending_net), sub: 'Awaiting credit', stripe: 'am' },
          { label: 'Return Deductions', val: INR(data.total_returns), sub: data.total_returns + ' returns', stripe: 'rd' },
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

      {/* Mini stats */}
      <div className="kpi-grid" style={{ marginBottom: 28 }}>
        {[
          { label: 'Total Orders', val: data.total_orders.toLocaleString('en-IN') },
          { label: 'Connected Platforms', val: data.connected_platforms + '/' + data.total_platforms },
          { label: 'Commission Overcharges', val: INR(data.commission_overcharges), red: true },
          { label: 'Bank Mismatches', val: data.bank_mismatches + ' credits', red: true },
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

      {/* Platform overview */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div className="card-title">Platform Overview</div>
          <div className="card-sub">Live status from connected marketplaces</div>
        </div>
        <button className="btn btn-g btn-sm" onClick={function() { navigate('/platforms') }}>
          Manage →
        </button>
      </div>

      <div className="four-col">
        {data.platforms.map(function(p) {
          return (
            <div
              key={p.id}
              className="card"
              style={{ padding: 16, cursor: 'pointer' }}
              onClick={function() { addToast(p.name + ' — ' + INRL(p.gmv) + ' GMV', 'info', p.orders + ' orders this month') }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <span style={{ fontSize: 24 }}>{p.icon}</span>
                <StatusChip status={p.status} />
              </div>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 2 }}>{p.name}</div>
              <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 10 }}>Phase {p.phase}</div>
              {p.status !== 'disconnected' ? (
                <div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#0D1F35' }}>
                    {INRL(p.gmv)}
                  </div>
                  <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 10 }}>GMV this month</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                    {[
                      { k: 'Orders', v: p.orders.toLocaleString('en-IN') },
                      { k: 'Returns %', v: p.rr + '%' },
                      { k: 'Commission', v: p.comm + '%' },
                      { k: 'Last Sync', v: p.sync },
                    ].map(function(s) {
                      return (
                        <div key={s.k}>
                          <div style={{ fontSize: 10, color: '#8FA5BD' }}>{s.k}</div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#0D1F35' }}>{s.v}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: 12, color: '#8FA5BD' }}>
                  Not connected.{' '}
                  <span
                    onClick={function(e) { e.stopPropagation(); navigate('/platforms') }}
                    style={{ color: '#0ABFCA', cursor: 'pointer' }}
                  >
                    Connect →
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Charts */}
      <div className="two-col-wide">
        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-title">Settlement Trend</div>
              <div className="card-sub">Monthly net settlements (₹)</div>
            </div>
          </div>
          <div className="card-bd">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data.settlement_trend} barSize={32}>
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#8FA5BD' }} />
                <YAxis hide />
                <Tooltip
                  formatter={function(v) { return [INRL(v), 'Settlements'] }}
                  contentStyle={{ borderRadius: 10, fontSize: 12 }}
                />
                <Bar dataKey="amount" radius={[6, 6, 0, 0]}>
                  {data.settlement_trend.map(function(entry, i) {
                    return (
                      <Cell
                        key={i}
                        fill={entry.month === 'Apr' ? '#0ABFCA' : '#E2EBF3'}
                      />
                    )
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-title">Platform Mix</div>
              <div className="card-sub">GMV share by platform</div>
            </div>
          </div>
          <div className="card-bd" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <ResponsiveContainer width="100%" height={140}>
              <PieChart>
                <Pie
                  data={data.platform_share}
                  cx="50%" cy="50%"
                  innerRadius={40} outerRadius={65}
                  dataKey="value"
                >
                  {data.platform_share.map(function(entry, i) {
                    return <Cell key={i} fill={entry.color} />
                  })}
                </Pie>
                <Tooltip formatter={function(v, n) { return [v + '%', n] }} contentStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {data.platform_share.map(function(s) {
                return (
                  <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                    <span style={{ fontSize: 12, flex: 1, color: '#4B6080' }}>{s.name}</span>
                    <span style={{ fontSize: 12, fontWeight: 700 }}>{s.value}%</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
