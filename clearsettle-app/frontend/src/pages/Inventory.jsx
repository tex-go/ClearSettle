import React from 'react'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import useUIStore from '../store/uiStore'
import api from '../utils/api'

function StockCell({ val }) {
  if (val === 0) return <span style={{ color: '#8FA5BD' }}>—</span>
  var color = val < 20 ? '#E8344A' : '#0D1F35'
  return <span style={{ color: color, fontWeight: val < 20 ? 700 : 400 }}>{val}</span>
}

function Inventory() {
  var { data, loading } = useApi('/inventory/')
  var addToast = useUIStore(function(s) { return s.addToast })

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary
  var critical = data.items.filter(function(i) { return i.st === 'critical' })
  var low = data.items.filter(function(i) { return i.st === 'low' })

  function handleSync() {
    api.post('/inventory/sync').then(function() {
      addToast('Inventory sync initiated', 'success', 'Fetching stock from all 5 platforms')
    })
  }

  return (
    <div className="page page-anim">
      {/* Alerts */}
      {critical.length > 0 && (
        <div className="ab err">
          <span>🔴</span>
          <div className="ab-body">
            <div className="ab-title">Critical stock — {critical.length} SKU(s) need immediate reorder</div>
            <div className="ab-sub">{critical.map(function(c) { return c.sku }).join(', ')}</div>
          </div>
        </div>
      )}
      {low.length > 0 && (
        <div className="ab warn">
          <span>⚠️</span>
          <div className="ab-body">
            <div className="ab-title">Low stock — {low.length} SKU(s) below reorder level</div>
            <div className="ab-sub">{low.map(function(l) { return l.sku }).join(', ')}</div>
          </div>
        </div>
      )}

      {/* Header + actions */}
      <div className="page-hd">
        <div>
          <div className="page-title">Inventory</div>
          <div className="page-sub">Stock levels across all connected platforms</div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-s btn-sm" onClick={function() { addToast('Exporting inventory...', 'info') }}>
            ⬇ Export
          </button>
          <button className="btn btn-p btn-sm" onClick={handleSync}>
            🔄 Sync All
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="tw">
        <table>
          <thead>
            <tr>
              {['SKU', 'Product', 'Amazon', 'Flipkart', 'Meesho', 'Myntra', 'Nykaa', 'Total', 'Reorder At', 'Status'].map(function(h) {
                return <th key={h}>{h}</th>
              })}
            </tr>
          </thead>
          <tbody>
            {data.items.map(function(item) {
              return (
                <tr key={item.sku}>
                  <td>
                    <span className="mono" style={{ color: '#0ABFCA', fontSize: 12 }}>{item.sku}</span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{item.prod}</td>
                  <td><StockCell val={item.amazon} /></td>
                  <td><StockCell val={item.flipkart} /></td>
                  <td><StockCell val={item.meesho} /></td>
                  <td><StockCell val={item.myntra} /></td>
                  <td><StockCell val={item.nykaa} /></td>
                  <td style={{ fontWeight: 700 }}>{item.total}</td>
                  <td style={{ color: '#8FA5BD' }}>{item.reorder}</td>
                  <td><StatusChip status={item.st} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Bottom buttons */}
      <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
        <button className="btn btn-s" onClick={function() { addToast('Reorder alerts sent to 4 SKUs', 'warn') }}>
          📧 Send Reorder Alert
        </button>
        <button className="btn btn-s" onClick={handleSync}>
          🔄 Force Sync
        </button>
      </div>
    </div>
  )
}

export default Inventory
