import React, { useState } from 'react'
import { useLocation } from 'react-router-dom'
import useUIStore from '../../store/uiStore'
import useApi from '../../hooks/useApi'
import { Modal } from '../ui/Modal'

var ROUTE_META = {
  '/': { title: 'Dashboard', sub: 'Live overview of your eCommerce operations' },
  '/settlements': { title: 'Settlements', sub: 'Track and verify platform payouts' },
  '/bank': { title: 'Bank Reconciliation', sub: 'Match bank credits to settlement IDs' },
  '/disputes': { title: 'Disputes', sub: 'Manage overcharge and penalty disputes' },
  '/returns': { title: 'Returns', sub: 'Return deductions and reason analysis' },
  '/commission': { title: 'Commission Audit', sub: 'Published vs charged rate comparison' },
  '/gst': { title: 'GST / TCS', sub: 'TCS/TDS reconciliation and ITC claims' },
  '/inventory': { title: 'Inventory Sync', sub: 'Multi-platform stock levels' },
  '/cashflow': { title: 'Cash Flow Forecast', sub: '30-day settlement forecast calendar' },
  '/analytics': { title: 'Profitability', sub: 'SKU-level P&L analysis' },
  '/dispute-engine': { title: 'Dispute Rule Engine', sub: 'Automated overcharge detection rules' },
  '/recovery': { title: 'Recovery Tracker', sub: 'Filed disputes and recovery progress' },
  '/competitors': { title: 'Market Intelligence', sub: 'Competitor feature comparison' },
  '/platforms': { title: 'Platform Settings', sub: 'Manage marketplace connections' },
  '/reports': { title: 'Report Centre', sub: 'Generate and download all reports' },
}

var typeColors = {
  error: '#E8344A', warn: '#E9930D', info: '#0ABFCA', success: '#0DB07A',
}

function Topbar({ onMenuClick }) {
  var location = useLocation()
  var meta = ROUTE_META[location.pathname] || { title: 'ClearSettle', sub: '' }
  var addToast = useUIStore(function(s) { return s.addToast })
  var [alertsOpen, setAlertsOpen] = useState(false)
  var { data: notifData } = useApi('/dashboard/notifications')

  function handleSync() {
    addToast('Syncing all platforms...', 'info', 'Fetching latest data from Amazon, Flipkart, Meesho')
    setTimeout(function() {
      addToast('Sync complete', 'success', 'All 4 platforms updated')
    }, 2500)
  }

  return (
    <div style={{
      height: 60, background: '#fff',
      borderBottom: '1px solid #E2EBF3',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 16px 0 20px', flexShrink: 0,
      position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          className="mob-show btn btn-g btn-sm"
          onClick={onMenuClick}
          style={{ display: 'none', padding: '6px 10px', fontSize: 18, lineHeight: 1 }}
        >☰</button>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#0D1F35' }}>{meta.title}</div>
          <div style={{ fontSize: 11, color: '#8FA5BD' }}>{meta.sub}</div>
        </div>
      </div>

      <div className="topbar-actions">
        <button onClick={handleSync} className="btn btn-s btn-sm">
          🔄 <span className="btn-text">Sync All</span>
        </button>

        <button
          onClick={function() { setAlertsOpen(true) }}
          style={{
            position: 'relative', width: 36, height: 36,
            background: '#F1F5F9', border: '1px solid #E2EBF3',
            borderRadius: 9, cursor: 'pointer', fontSize: 16,
          }}
        >
          🔔
          <span style={{
            position: 'absolute', top: 4, right: 4,
            width: 8, height: 8, background: '#E8344A',
            borderRadius: '50%', border: '2px solid #fff',
          }} />
        </button>

        <button
          onClick={function() { addToast('Exporting data...', 'info') }}
          className="btn btn-p btn-sm"
        >
          ⬇ <span className="btn-text">Export</span>
        </button>
      </div>

      <Modal
        open={alertsOpen}
        title="Notifications"
        sub="Recent alerts and updates"
        onClose={function() { setAlertsOpen(false) }}
        size="sm"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {notifData && notifData.items.map(function(n) {
            return (
              <div key={n.id} style={{
                padding: '12px 14px', borderRadius: 10,
                border: '1px solid #E2EBF3',
                borderLeft: '3px solid ' + (typeColors[n.type] || '#0ABFCA'),
              }}>
                <div style={{ fontWeight: 700, fontSize: 13 }}>{n.title}</div>
                <div style={{ fontSize: 12, color: '#4B6080', marginTop: 3 }}>{n.sub}</div>
                <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 4 }}>{n.time}</div>
              </div>
            )
          })}
        </div>
      </Modal>
    </div>
  )
}

export default Topbar
