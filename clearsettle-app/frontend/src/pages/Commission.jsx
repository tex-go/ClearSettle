import React from 'react'
import useApi from '../hooks/useApi'
import useUIStore from '../store/uiStore'
import { INR } from '../utils/format'
import api from '../utils/api'

function Commission() {
  var { data, loading } = useApi('/commission/')
  var addToast = useUIStore(function(s) { return s.addToast })

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary

  function handleBulkDispute() {
    api.post('/commission/bulk-dispute').then(function(res) {
      addToast('Bulk dispute raised for ' + res.data.count + ' SKUs', 'success', 'Total: ' + INR(res.data.total))
    })
  }

  return (
    <div className="page page-anim">
      {/* Alert banner */}
      <div className="ab warn">
        <span>⚠️</span>
        <div className="ab-body">
          <div className="ab-title">{s.flagged_count} overcharges detected — {INR(s.total_overcharge)} recoverable</div>
          <div className="ab-sub">Amazon and Flipkart are charging above published category rates</div>
        </div>
        <div className="ab-act">
          <button className="btn btn-s btn-sm" onClick={handleBulkDispute}>
            Dispute All →
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-row cols-3">
        {[
          { label: 'Total Overcharge', val: INR(s.total_overcharge), stripe: 'rd' },
          { label: 'SKUs Affected', val: s.flagged_count, stripe: 'am' },
          { label: 'Orders Affected', val: s.affected_orders.toLocaleString('en-IN'), stripe: 'am' },
        ].map(function(k) {
          return (
            <div key={k.label} className="stat-card">
              <div className={'sc-stripe ' + k.stripe} />
              <div className="sc-label" style={{ marginTop: 8 }}>{k.label}</div>
              <div className="sc-val" style={{ color: k.stripe === 'rd' ? '#E8344A' : undefined }}>{k.val}</div>
            </div>
          )
        })}
      </div>

      {/* Table */}
      <div className="tw">
        <table>
          <thead>
            <tr>
              {['Platform', 'SKU', 'Product', 'Category', 'Published %', 'Charged %', 'Orders', 'Expected Fee', 'Charged Fee', 'Overcharge', ''].map(function(h) {
                return <th key={h}>{h}</th>
              })}
            </tr>
          </thead>
          <tbody>
            {data.items.map(function(c, i) {
              return (
                <tr key={i} style={{ background: c.flag ? 'rgba(232,52,74,.04)' : 'transparent' }}>
                  <td>{c.icon} {c.plat}</td>
                  <td><span className="mono" style={{ color: '#0ABFCA', fontSize: 12 }}>{c.sku}</span></td>
                  <td style={{ maxWidth: 180 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{c.prod}</div>
                  </td>
                  <td><span className="cs-chip cs-chip-bl">{c.cat}</span></td>
                  <td style={{ fontWeight: 600 }}>{c.pub}%</td>
                  <td>
                    <span style={{ fontWeight: 700, color: c.flag ? '#E8344A' : '#0D1F35' }}>
                      {c.chg}%
                    </span>
                    {c.flag && (
                      <span style={{ fontSize: 11, color: '#E8344A', marginLeft: 4 }}>
                        (+{(c.chg - c.pub).toFixed(1)}%)
                      </span>
                    )}
                  </td>
                  <td>{c.orders}</td>
                  <td>{INR(c.expFee)}</td>
                  <td style={{ color: c.flag ? '#E8344A' : undefined, fontWeight: c.flag ? 700 : 400 }}>
                    {INR(c.chgFee)}
                  </td>
                  <td>
                    {c.flag
                      ? <span style={{ color: '#E8344A', fontWeight: 700 }}>-{INR(c.over)}</span>
                      : <span style={{ color: '#0DB07A', fontWeight: 600 }}>✓ Correct</span>
                    }
                  </td>
                  <td>
                    {c.flag && (
                      <button
                        className="btn btn-d btn-sm"
                        onClick={function() { addToast('Dispute raised for ' + c.sku, 'warn', 'Overcharge: ' + INR(c.over)) }}
                      >
                        Dispute
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Commission
