import React, { useEffect } from 'react'

var sizeMap = { '': '700px', lg: '860px', sm: '460px' }

export function Modal({ open, title, sub, children, footer, onClose, size }) {
  var maxW = sizeMap[size || ''] || '700px'

  useEffect(function() {
    if (!open) return
    function handler(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return function() { document.removeEventListener('keydown', handler) }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="modal-overlay"
      onClick={function(e) { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="modal-wrap" style={{ maxWidth: maxW }}>
        <div className="modal-hd">
          <div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#0D1F35' }}>{title}</div>
            {sub && <div style={{ fontSize: 12, color: '#8FA5BD', marginTop: 3 }}>{sub}</div>}
          </div>
          <button onClick={onClose} className="modal-close">✕</button>
        </div>
        <div className="modal-bd">
          {children}
        </div>
        {footer && (
          <div className="modal-ft">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
