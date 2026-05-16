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
      onClick={function(e) { if (e.target === e.currentTarget) onClose() }}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(13,31,53,.45)',
        backdropFilter: 'blur(6px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 20,
      }}
    >
      <div style={{
        background: '#fff', borderRadius: 18,
        maxWidth: maxW, width: '100%',
        maxHeight: '90vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 24px 80px rgba(13,31,53,.25)',
        animation: 'fadeUp .25s ease both',
      }}>
        <div style={{
          display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
          padding: '20px 24px 16px', borderBottom: '1px solid #E2EBF3',
        }}>
          <div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#0D1F35' }}>{title}</div>
            {sub && <div style={{ fontSize: 12, color: '#8FA5BD', marginTop: 3 }}>{sub}</div>}
          </div>
          <button onClick={onClose} style={{
            background: '#F1F5F9', border: 'none', borderRadius: 8,
            width: 32, height: 32, cursor: 'pointer',
            fontSize: 16, color: '#4B6080', flexShrink: 0,
          }}>✕</button>
        </div>
        <div style={{ overflow: 'auto', padding: '20px 24px', flex: 1 }}>
          {children}
        </div>
        {footer && (
          <div style={{
            padding: '16px 24px', borderTop: '1px solid #E2EBF3',
            display: 'flex', gap: 10, justifyContent: 'flex-end',
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
