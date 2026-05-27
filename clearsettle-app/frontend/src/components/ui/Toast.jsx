import React from 'react'
import useUIStore from '../../store/uiStore'

var borderColors = {
  info:    '#0ABFCA',
  success: '#0DB07A',
  error:   '#E8344A',
  warn:    '#E9930D',
}

export function ToastContainer() {
  var { toasts, removeToast } = useUIStore()

  return (
    <div className="toast-container" role="log" aria-live="polite" aria-label="Notifications">
      {toasts.map(function(t) {
        return (
          <div
            key={t.id}
            className="toast-item"
            role="alert"
            onClick={function() { removeToast(t.id) }}
            style={{ borderLeft: '4px solid ' + (borderColors[t.type] || '#0ABFCA') }}
          >
            <div className="toast-msg">{t.msg}</div>
            {t.sub && <div className="toast-sub">{t.sub}</div>}
          </div>
        )
      })}
    </div>
  )
}
