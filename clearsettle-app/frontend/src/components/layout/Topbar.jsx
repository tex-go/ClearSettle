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
var typeIcons = {
  error: '🚨', warn: '⚠️', info: 'ℹ️', success: '✅',
}

function Topbar({ onMenuClick }) {
  var location = useLocation()
  var meta = ROUTE_META[location.pathname] || { title: 'ClearSettle', sub: '' }
  var addToast = useUIStore(function(s) { return s.addToast })
  var [alertsOpen, setAlertsOpen] = useState(false)
  var { data: notifData, loading: notifLoading } = useApi('/dashboard/notifications')
  var notifications = (notifData && notifData.items) || []
  var unreadCount = notifications.length

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
      <div className="topbar-left">
        <button
          className="mob-show btn btn-g btn-sm"
          onClick={onMenuClick}
          style={{ display: 'none', padding: '6px 10px', fontSize: 18, lineHeight: 1, flexShrink: 0 }}
        >☰</button>
        <div className="topbar-title-wrap">
          <div className="topbar-title">{meta.title}</div>
          <div className="topbar-sub">{meta.sub}</div>
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
          {unreadCount > 0 && (
            <span style={{
              position: 'absolute', top: 3, right: 3,
              minWidth: 16, height: 16,
              background: '#E8344A', color: '#fff',
              borderRadius: 99, border: '2px solid #fff',
              fontSize: 9, fontWeight: 800,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              lineHeight: 1,
            }}>
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
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
        title={'Notifications' + (unreadCount > 0 ? ' (' + unreadCount + ')' : '')}
        sub="Live alerts from your reconciliation data"
        onClose={function() { setAlertsOpen(false) }}
        size="sm"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {notifLoading && (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#8FA5BD', fontSize: 13 }}>
              Loading alerts...
            </div>
          )}
          {!notifLoading && notifications.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <div style={{ fontSize: 36, marginBottom: 10 }}>✅</div>
              <div style={{ fontWeight: 700, fontSize: 14, color: '#0D1F35', marginBottom: 4 }}>
                All Clear
              </div>
              <div style={{ fontSize: 12, color: '#8FA5BD', lineHeight: 1.5 }}>
                No open alerts. Upload a Flipkart P&L report to start detecting anomalies.
              </div>
            </div>
          )}
          {!notifLoading && notifications.map(function(n) {
            var color = typeColors[n.type] || '#0ABFCA'
            var icon  = typeIcons[n.type]  || 'ℹ️'
            return (
              <div key={n.id} style={{
                padding: '11px 14px', borderRadius: 10,
                border: '1px solid #E2EBF3',
                borderLeft: '3px solid ' + color,
                background: n.type === 'error' ? 'rgba(232,52,74,.03)'
                          : n.type === 'warn'  ? 'rgba(233,147,13,.03)'
                          : n.type === 'success' ? 'rgba(13,176,122,.03)'
                          : '#fff',
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>{icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: 13, color: '#0D1F35', lineHeight: 1.3 }}>
                      {n.title}
                    </div>
                    <div style={{ fontSize: 12, color: '#4B6080', marginTop: 3, lineHeight: 1.4 }}>
                      {n.sub}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 6 }}>
                      <span style={{ fontSize: 11, color: '#8FA5BD' }}>{n.time}</span>
                      {n.action && (
                        <span style={{ fontSize: 11, fontWeight: 700, color: color, cursor: 'pointer' }}>
                          {n.action} →
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </Modal>
    </div>
  )
}

export default Topbar
