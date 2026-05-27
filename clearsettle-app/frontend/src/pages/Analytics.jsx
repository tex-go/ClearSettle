import React, { useState } from 'react'
import useApi from '../hooks/useApi'
import { Modal } from '../components/ui/Modal'
import { INR, PCT } from '../utils/format'

function Analytics() {
  var { data, loading } = useApi('/analytics/')
  var [selected, setSelected] = useState(null)

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary
  var sorted = [...data.items].sort(function(a, b) { return b.margin - a.margin })
  var maxRev = Math.max(...data.items.map(function(i) { return i.rev }))

  function barColor(margin) {
    if (margin < 0) return '#E8344A'
    if (margin < 20) return '#E9930D'
    return '#0DB07A'
  }

  return (
    <div className="page page-anim">
      {/* Stats */}
      <div className="stats-row cols-4">
        {[
          { label: 'Total Revenue', val: INR(s.total_revenue), stripe: 'tl' },
          { label: 'Net Profit', val: INR(s.total_net), stripe: 'gn' },
          { label: 'Avg Margin', val: PCT(s.avg_margin), stripe: 'tl' },
          { label: 'Loss-Making SKUs', val: s.loss_making, stripe: 'rd' },
        ].map(function(k) {
          return (
            <div key={k.label} className="stat-card">
              <div className={'sc-stripe ' + k.stripe} />
              <div className="sc-label" style={{ marginTop: 8 }}>{k.label}</div>
              <div className="sc-val" style={{ color: k.stripe === 'rd' && k.val > 0 ? '#E8344A' : undefined }}>
                {k.val}
              </div>
            </div>
          )
        })}
      </div>

      <div className="two-col">
        {/* Ranking */}
        <div className="card">
          <div className="card-hd">
            <div className="card-title">SKU Profitability Ranking</div>
          </div>
          <div className="card-bd" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {sorted.map(function(item, i) {
              var rankColors = ['#F59E0B', '#94A3B8', '#B45309', '#162B48']
              var rankColor = rankColors[Math.min(i, 3)]
              var barW = Math.abs(item.margin) / 45 * 100
              return (
                <div
                  key={item.sku}
                  onClick={function() { setSelected(item) }}
                  style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', padding: '6px 8px', borderRadius: 8, transition: 'background .15s' }}
                >
                  <div style={{
                    width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                    background: rankColor, color: '#fff',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, fontWeight: 700,
                  }}>
                    {i + 1}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {item.prod}
                    </div>
                    <div className="mono" style={{ fontSize: 10, color: '#8FA5BD' }}>{item.sku}</div>
                  </div>
                  <div style={{ width: 80 }}>
                    <div style={{ background: '#F1F5F9', borderRadius: 4, height: 6, overflow: 'hidden' }}>
                      <div style={{
                        width: barW + '%', height: '100%',
                        background: barColor(item.margin), borderRadius: 4,
                      }} />
                    </div>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: barColor(item.margin), width: 50, textAlign: 'right' }}>
                    {PCT(item.margin)}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Stacked bars */}
        <div className="card">
          <div className="card-hd">
            <div className="card-title">P&L by SKU</div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {[
                { color: '#94A3B8', label: 'COGS' },
                { color: '#FCD34D', label: 'Fees' },
                { color: '#FCA5A5', label: 'Returns' },
                { color: '#86EFAC', label: 'Net' },
              ].map(function(l) {
                return (
                  <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: l.color, flexShrink: 0 }} />
                    <span style={{ fontSize: 10, color: '#8FA5BD' }}>{l.label}</span>
                  </div>
                )
              })}
            </div>
          </div>
          <div className="card-bd" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {data.items.map(function(item) {
              var total = item.cogs + item.fees + item.retCost + Math.max(item.net, 0)
              function pct(n) { return total > 0 ? (n / total * 100) : 0 }
              return (
                <div
                  key={item.sku}
                  onClick={function() { setSelected(item) }}
                  style={{ cursor: 'pointer' }}
                >
                  <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>{item.prod}</div>
                  <div style={{ display: 'flex', borderRadius: 6, overflow: 'hidden', height: 14 }}>
                    <div style={{ width: pct(item.cogs) + '%', background: '#94A3B8' }} />
                    <div style={{ width: pct(item.fees) + '%', background: '#FCD34D' }} />
                    <div style={{ width: pct(item.retCost) + '%', background: '#FCA5A5' }} />
                    <div style={{ width: pct(Math.max(item.net, 0)) + '%', background: '#86EFAC' }} />
                  </div>
                  <div style={{ display: 'flex', gap: 10, marginTop: 4, flexWrap: 'wrap' }}>
                    {[
                      { label: 'COGS', val: INR(item.cogs) },
                      { label: 'Fees', val: INR(item.fees) },
                      { label: 'Returns', val: INR(item.retCost) },
                      { label: 'Net', val: INR(item.net), bold: true },
                    ].map(function(l) {
                      return (
                        <div key={l.label} style={{ fontSize: 10, color: '#8FA5BD', whiteSpace: 'nowrap' }}>
                          {l.label}: <span style={{ fontWeight: l.bold ? 700 : 400, color: l.bold ? barColor(item.margin) : undefined }}>{l.val}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {selected && (
        <Modal
          open={!!selected}
          title={selected.prod}
          sub={selected.sku + ' · Best on ' + selected.top}
          onClose={function() { setSelected(null) }}
          footer={<button className="btn btn-s" onClick={function() { setSelected(null) }}>Close</button>}
        >
          <div className="info-grid">
            {[
              { k: 'Revenue', v: INR(selected.rev) },
              { k: 'COGS', v: INR(selected.cogs) },
              { k: 'Platform Fees', v: INR(selected.fees) },
              { k: 'Return Cost', v: INR(selected.retCost) },
              { k: 'Ad Spend', v: INR(selected.ads) },
              { k: 'Net Profit', v: INR(selected.net) },
            ].map(function(m) {
              return (
                <div key={m.k} style={{ background: '#F1F5F9', borderRadius: 10, padding: '10px 14px' }}>
                  <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 4 }}>{m.k}</div>
                  <div style={{ fontWeight: 700, color: m.k === 'Net Profit' ? barColor(selected.margin) : '#0D1F35' }}>
                    {m.v}
                  </div>
                </div>
              )
            })}
          </div>

          {selected.margin < 0 && (
            <div className="ab err" style={{ marginBottom: 0 }}>
              <span>⚠️</span>
              <div className="ab-body">
                <div className="ab-title">Loss-making SKU</div>
                <div className="ab-sub">
                  High return rate ({PCT(selected.retCost / selected.rev * 100)}) is driving this SKU into losses. Review product description, size chart, and images.
                </div>
              </div>
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}

export default Analytics
