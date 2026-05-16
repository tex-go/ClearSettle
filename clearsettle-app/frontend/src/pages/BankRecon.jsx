import React, { useState } from 'react'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import { Modal } from '../components/ui/Modal'
import useUIStore from '../store/uiStore'
import { INR } from '../utils/format'
import api from '../utils/api'

var statusBg = {
  matched: 'rgba(13,176,122,.06)',
  partial: 'rgba(233,147,13,.06)',
  unmatched: 'rgba(232,52,74,.06)',
}
var statusBorder = {
  matched: 'rgba(13,176,122,.2)',
  partial: 'rgba(233,147,13,.2)',
  unmatched: 'rgba(232,52,74,.2)',
}
var matchIcon = { matched: '✅', partial: '⚠️', unmatched: '❌' }

function BankRecon() {
  var { data, loading } = useApi('/bank/')
  var addToast = useUIStore(function(s) { return s.addToast })
  var [selected, setSelected] = useState(null)

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary

  function handleAutoMatch() {
    api.post('/bank/auto-match').then(function(res) {
      addToast('Auto-match complete', 'success', res.data.matched + ' matched, ' + res.data.unmatched + ' still unmatched')
    })
  }

  return (
    <div className="page page-anim">
      {/* Alert */}
      <div className="ab err">
        <span>❌</span>
        <div className="ab-body">
          <div className="ab-title">{s.unmatched_count} bank credits unmatched</div>
          <div className="ab-sub">{INR(s.unmatched_amount)} in unexplained credits need manual investigation</div>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-row cols-4">
        {[
          { label: 'Total Credits', val: INR(s.total_amount), stripe: 'tl' },
          { label: 'Matched', val: s.matched_count, stripe: 'gn' },
          { label: 'Partial Match', val: s.partial_count, stripe: 'am' },
          { label: 'Unmatched', val: s.unmatched_count, stripe: 'rd' },
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

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <button className="btn btn-s" onClick={function() { addToast('Upload feature coming soon', 'info') }}>
          ⬆ Upload Statement
        </button>
        <button className="btn btn-p" onClick={handleAutoMatch}>
          🔄 Auto-Match All
        </button>
      </div>

      {/* Transaction cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {data.items.map(function(b) {
          return (
            <div
              key={b.id}
              onClick={function() { setSelected(b) }}
              style={{
                background: statusBg[b.ms],
                border: '1px solid ' + statusBorder[b.ms],
                borderRadius: 12, padding: '14px 18px',
                cursor: 'pointer', transition: 'box-shadow .15s',
                display: 'grid', gridTemplateColumns: '1fr auto 1fr auto',
                alignItems: 'center', gap: 20,
              }}
            >
              {/* Left: bank side */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#8FA5BD', marginBottom: 4 }}>BANK CREDIT</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: '#0D1F35' }}>{INR(b.amt)}</div>
                <div style={{ fontSize: 12, color: '#4B6080', marginTop: 2 }}>{b.desc}</div>
                <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 3 }}>
                  {b.date} · <span className="mono">{b.ref}</span>
                </div>
              </div>

              {/* Match icon */}
              <div style={{ fontSize: 22, textAlign: 'center' }}>
                {matchIcon[b.ms]}
              </div>

              {/* Right: settlement side */}
              <div>
                {b.sid ? (
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#8FA5BD', marginBottom: 4 }}>SETTLEMENT</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#0D1F35' }}>{INR(b.amt - b.va)}</div>
                    <div className="mono" style={{ fontSize: 12, color: '#0ABFCA', marginTop: 2 }}>{b.sid}</div>
                    {b.va > 0 && (
                      <div style={{ fontSize: 12, color: '#E9930D', marginTop: 3 }}>
                        Variance: {INR(b.va)}
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#8FA5BD', marginBottom: 4 }}>SETTLEMENT</div>
                    <div style={{ fontSize: 14, color: '#E8344A', fontWeight: 600 }}>No match found</div>
                    <div style={{ fontSize: 12, color: '#8FA5BD' }}>Requires investigation</div>
                  </div>
                )}
              </div>

              {/* Status chip */}
              <div>
                <StatusChip status={b.ms} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Detail modal */}
      {selected && (
        <Modal
          open={!!selected}
          title={'Bank Entry ' + selected.id}
          sub={selected.date + ' · ' + selected.desc}
          onClose={function() { setSelected(null) }}
          footer={<button className="btn btn-s" onClick={function() { setSelected(null) }}>Close</button>}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
            {[
              { k: 'Amount', v: INR(selected.amt) },
              { k: 'Date', v: selected.date },
              { k: 'Reference', v: selected.ref },
              { k: 'Settlement ID', v: selected.sid || '—' },
              { k: 'Match Status', v: selected.ms },
              { k: 'Variance', v: selected.va > 0 ? INR(selected.va) : '—' },
            ].map(function(i) {
              return (
                <div key={i.k} style={{ background: '#F1F5F9', borderRadius: 10, padding: '10px 14px' }}>
                  <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 4 }}>{i.k}</div>
                  <div style={{ fontWeight: 700, fontFamily: ['Reference', 'Settlement ID'].includes(i.k) ? 'JetBrains Mono, monospace' : 'inherit', fontSize: 12 }}>{i.v}</div>
                </div>
              )
            })}
          </div>
          {!selected.sid && (
            <div className="ab err" style={{ marginBottom: 0 }}>
              <span>🔍</span>
              <div className="ab-body">
                <div className="ab-title">Unmatched Credit</div>
                <div className="ab-sub">Contact the platform finance team with this bank reference to trace the payment</div>
              </div>
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}

export default BankRecon
