import React from 'react'
import useUIStore from '../../store/uiStore'

var borderColors = {
  info: '#0ABFCA',
  success: '#0DB07A',
  error: '#E8344A',
  warn: '#E9930D',
}

export function ToastContainer() {
  var { toasts, removeToast } = useUIStore()

  return (
    <div style={{
      position: 'fixed', top: 20, right: 20,
      zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 10,
      pointerEvents: 'none',
    }}>
      {toasts.map(function(t) {
        return (
          <div key={t.id} onClick={function() { removeToast(t.id) }} style={{
            background: '#0D1F35', color: '#fff',
            borderRadius: 12, padding: '12px 16px',
            borderLeft: '4px solid ' + (borderColors[t.type] || '#0ABFCA'),
            minWidth: 280, maxWidth: 380,
            boxShadow: '0 8px 32px rgba(0,0,0,.3)',
            pointerEvents: 'all', cursor: 'pointer',
            animation: 'slideDown .25s ease both',
          }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{t.msg}</div>
            {t.sub && <div style={{ fontSize: 12, opacity: .7, marginTop: 3 }}>{t.sub}</div>}
          </div>
        )
      })}
    </div>
  )
}
