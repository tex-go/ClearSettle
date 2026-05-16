import React from 'react'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import useUIStore from '../store/uiStore'
import { INR } from '../utils/format'

function GST() {
  var { data, loading } = useApi('/gst/')
  var addToast = useUIStore(function(s) { return s.addToast })

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary

  return (
    <div className="page page-anim">
      {/* Stats */}
      <div className="stats-row cols-4">
        {[
          { label: 'TCS Deducted (1%)', val: INR(s.total_tcs), stripe: 'am' },
          { label: 'TDS Deducted (2%)', val: INR(s.total_tds), stripe: 'am' },
          { label: 'Unreconciled', val: s.unreconciled + ' platforms', stripe: 'rd' },
          { label: 'GSTR-2A Claimable', val: INR(s.claimable), stripe: 'tl' },
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

      {/* Warning */}
      {s.unreconciled > 0 && (
        <div className="ab warn">
          <span>⚠️</span>
          <div className="ab-body">
            <div className="ab-title">{s.unreconciled} platforms pending reconciliation</div>
            <div className="ab-sub">Meesho and Nykaa TCS does not match Form 26AS — CA review required</div>
          </div>
          <div className="ab-act">
            <button className="btn btn-s btn-sm" onClick={function() { addToast('Generating GSTR report...', 'info') }}>
              Export GSTR
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="tw" style={{ marginBottom: 20 }}>
        <table>
          <thead>
            <tr>
              {['Platform', 'Taxable Value', 'TCS (1%)', 'TDS (2%)', 'GST by Platform', 'Invoices', 'Reconciled', ''].map(function(h) {
                return <th key={h}>{h}</th>
              })}
            </tr>
          </thead>
          <tbody>
            {data.items.map(function(g) {
              return (
                <tr key={g.plat}>
                  <td>{g.icon} <strong>{g.plat}</strong></td>
                  <td>{INR(g.taxable)}</td>
                  <td style={{ color: '#E9930D', fontWeight: 600 }}>{INR(g.tcs)}</td>
                  <td style={{ color: '#E9930D', fontWeight: 600 }}>{INR(g.tds)}</td>
                  <td>{INR(g.gstByP)}</td>
                  <td>{g.inv}</td>
                  <td>
                    <StatusChip status={g.ok ? 'ok' : 'pending'} />
                  </td>
                  <td>
                    <button
                      className="btn btn-g btn-sm"
                      onClick={function() { addToast('Downloading GSTR for ' + g.plat, 'info') }}
                    >
                      GSTR
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 10 }}>
        {[
          { label: '📋 CA Report Pack', toast: 'Generating CA report pack...' },
          { label: '📄 TCS/TDS Statement', toast: 'Generating TCS/TDS statement...' },
          { label: '💰 ITC Claim Summary', toast: 'Generating ITC claim summary...' },
        ].map(function(b) {
          return (
            <button
              key={b.label}
              className="btn btn-s"
              onClick={function() { addToast(b.toast, 'info') }}
            >
              {b.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default GST
