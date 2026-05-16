import React from 'react'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import { INR } from '../utils/format'

var PLATFORM_RATES = [
  { name: 'Myntra', rate: 37.8 },
  { name: 'AJIO', rate: 21.3 },
  { name: 'Nykaa', rate: 19.9 },
  { name: 'Meesho', rate: 15.3 },
  { name: 'Amazon', rate: 10.9 },
  { name: 'Flipkart', rate: 10.3 },
]

function CSSBar({ label, count, max, color }) {
  var pct = max > 0 ? (count / max) * 100 : 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
      <div style={{ width: 120, fontSize: 12, color: '#4B6080', flexShrink: 0, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
        {label}
      </div>
      <div style={{ flex: 1, background: '#F1F5F9', borderRadius: 4, height: 8, overflow: 'hidden' }}>
        <div style={{ width: pct + '%', background: color || '#0ABFCA', height: '100%', borderRadius: 4, transition: 'width .4s' }} />
      </div>
      <div style={{ width: 24, fontSize: 12, fontWeight: 700, color: '#0D1F35', textAlign: 'right' }}>
        {count}
      </div>
    </div>
  )
}

function Returns() {
  var { data, loading } = useApi('/returns/')

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary
  var reasons = s.by_reason
  var maxReason = Math.max(...Object.values(reasons))

  return (
    <div className="page page-anim">
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        {/* Left: table */}
        <div>
          <div className="stats-row cols-3" style={{ marginBottom: 20 }}>
            {[
              { label: 'Total Returns', val: s.total_count, stripe: 'tl' },
              { label: 'Total Deducted', val: INR(s.total_deducted), stripe: 'rd' },
              { label: 'Disputed Returns', val: s.disputed_count, stripe: 'pu' },
            ].map(function(k) {
              return (
                <div key={k.label} className="stat-card">
                  <div className={'sc-stripe ' + k.stripe} />
                  <div className="sc-label" style={{ marginTop: 8 }}>{k.label}</div>
                  <div className="sc-val">{k.val}</div>
                </div>
              )
            })}
          </div>

          <div className="tw">
            <table>
              <thead>
                <tr>
                  {['Return ID', 'Platform', 'Product / SKU', 'Reason', 'Qty', 'Refund', 'Shipping', 'Total', 'Status'].map(function(h) {
                    return <th key={h}>{h}</th>
                  })}
                </tr>
              </thead>
              <tbody>
                {data.items.map(function(r) {
                  return (
                    <tr key={r.id}>
                      <td><span className="mono" style={{ color: '#0ABFCA', fontSize: 12 }}>{r.id}</span></td>
                      <td>{r.icon} {r.plat}</td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{r.prod}</div>
                        <div className="mono" style={{ fontSize: 11, color: '#8FA5BD' }}>{r.sku}</div>
                      </td>
                      <td>
                        <span className="cs-chip cs-chip-am" style={{ fontSize: 11 }}>{r.reason}</span>
                      </td>
                      <td>{r.qty}</td>
                      <td>{INR(r.base)}</td>
                      <td style={{ color: '#E8344A' }}>-{INR(r.ship)}</td>
                      <td style={{ fontWeight: 700, color: '#E8344A' }}>-{INR(r.total)}</td>
                      <td><StatusChip status={r.status} /></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* By Reason */}
          <div className="card">
            <div className="card-hd">
              <div className="card-title">By Reason</div>
            </div>
            <div className="card-bd">
              {Object.entries(reasons).sort(function(a, b) { return b[1] - a[1] }).map(function(entry) {
                return (
                  <CSSBar key={entry[0]} label={entry[0]} count={entry[1]} max={maxReason} color="#7B52E8" />
                )
              })}
            </div>
          </div>

          {/* Platform Return Rates */}
          <div className="card">
            <div className="card-hd">
              <div className="card-title">Platform Return Rates</div>
            </div>
            <div className="card-bd">
              {PLATFORM_RATES.map(function(p) {
                var color = p.rate > 25 ? '#E8344A' : p.rate > 15 ? '#E9930D' : '#0DB07A'
                var maxRate = 40
                return (
                  <div key={p.name} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600 }}>{p.name}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: color }}>{p.rate}%</span>
                    </div>
                    <div style={{ background: '#F1F5F9', borderRadius: 4, height: 8 }}>
                      <div style={{
                        width: (p.rate / maxRate * 100) + '%',
                        background: color, height: '100%', borderRadius: 4,
                      }} />
                    </div>
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

export default Returns
