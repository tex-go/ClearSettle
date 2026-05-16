import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import { Modal } from '../components/ui/Modal'
import useUIStore from '../store/uiStore'
import { INR, INRL } from '../utils/format'

function Settlements() {
  var { data, loading } = useApi('/settlements/')
  var addToast = useUIStore(function(s) { return s.addToast })
  var navigate = useNavigate()
  var [statusFilter, setStatusFilter] = useState('all')
  var [search, setSearch] = useState('')
  var [selected, setSelected] = useState(null)

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var items = data.items.filter(function(s) {
    if (statusFilter !== 'all' && s.status !== statusFilter) return false
    if (search && !s.id.toLowerCase().includes(search.toLowerCase()) && !s.plat.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  var paidCount = data.items.filter(function(s) { return s.status === 'paid' }).length
  var pendingCount = data.items.filter(function(s) { return s.status === 'pending' }).length

  return (
    <div className="page page-anim">
      {/* Stats */}
      <div className="stats-row cols-3">
        <div className="stat-card">
          <div className="sc-stripe tl" />
          <div className="sc-label" style={{ marginTop: 8 }}>Total Settled</div>
          <div className="sc-val">{INRL(data.summary.total_net)}</div>
          <div className="sc-sub">{paidCount} settlements paid</div>
        </div>
        <div className="stat-card">
          <div className="sc-stripe am" />
          <div className="sc-label" style={{ marginTop: 8 }}>Pending Payout</div>
          <div className="sc-val">{INRL(data.summary.pending_net)}</div>
          <div className="sc-sub">{pendingCount} settlements pending</div>
        </div>
        <div className="stat-card">
          <div className="sc-stripe rd" />
          <div className="sc-label" style={{ marginTop: 8 }}>Penalty Deductions</div>
          <div className="sc-val" style={{ color: '#E8344A' }}>{INR(data.summary.total_penalties)}</div>
          <div className="sc-sub">May be raisable as disputes</div>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-row">
        <div className="filter-pills" style={{ marginBottom: 0 }}>
          {[
            { key: 'all', label: 'All (' + data.items.length + ')' },
            { key: 'paid', label: 'Paid (' + paidCount + ')' },
            { key: 'pending', label: 'Pending (' + pendingCount + ')' },
          ].map(function(f) {
            return (
              <button
                key={f.key}
                className={'pill' + (statusFilter === f.key ? ' active' : '')}
                onClick={function() { setStatusFilter(f.key) }}
              >
                {f.label}
              </button>
            )
          })}
        </div>
        <div className="filter-search">
          <input
            placeholder="Search settlements..."
            value={search}
            onChange={function(e) { setSearch(e.target.value) }}
          />
          <button className="btn btn-s btn-sm" onClick={function() { addToast('Exporting settlements CSV...', 'info') }}>
            ⬇ Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="tw">
        <table>
          <thead>
            <tr>
              {['Settlement ID', 'Platform', 'Period', 'Base Value', 'Deductions', 'Net Settled', 'Penalty', 'Status', ''].map(function(h) {
                return <th key={h}>{h}</th>
              })}
            </tr>
          </thead>
          <tbody>
            {items.map(function(s) {
              var deductions = s.comm + s.logi + s.ret + s.tcs + s.pen
              return (
                <tr key={s.id}>
                  <td><span className="mono" style={{ color: '#0ABFCA', fontSize: 12 }}>{s.id}</span></td>
                  <td>
                    <span style={{ marginRight: 6 }}>{s.icon}</span>
                    <strong>{s.plat}</strong>
                  </td>
                  <td style={{ color: '#4B6080' }}>{s.period}</td>
                  <td>{INR(s.base)}</td>
                  <td style={{ color: '#E8344A' }}>-{INR(deductions)}</td>
                  <td style={{ fontWeight: 700 }}>{INR(s.net)}</td>
                  <td>
                    {s.pen > 0
                      ? <span style={{ color: '#E9930D', fontWeight: 600 }}>-{INR(s.pen)}</span>
                      : <span style={{ color: '#0DB07A' }}>—</span>
                    }
                  </td>
                  <td><StatusChip status={s.status} /></td>
                  <td>
                    <button
                      className="btn btn-g btn-sm"
                      onClick={function() { setSelected(s) }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Detail Modal */}
      {selected && (
        <Modal
          open={!!selected}
          title={'Settlement ' + selected.id}
          sub={selected.plat + ' · ' + selected.period}
          onClose={function() { setSelected(null) }}
          footer={
            <>
              <button className="btn btn-s" onClick={function() { setSelected(null) }}>Close</button>
              <button className="btn btn-g" onClick={function() { setSelected(null); navigate('/disputes') }}>
                Raise Dispute →
              </button>
              <button className="btn btn-p" onClick={function() { addToast('Downloading PDF...', 'info') }}>
                ⬇ Download PDF
              </button>
            </>
          }
        >
          {/* Info grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 20 }}>
            {[
              { k: 'Orders', v: selected.orders },
              { k: 'Invoices', v: selected.inv },
              { k: 'Period', v: selected.period },
              { k: 'Paid On', v: selected.paid_date || 'Pending' },
              { k: 'Status', v: selected.status },
              { k: 'Penalty', v: selected.pen > 0 ? INR(selected.pen) : '—' },
            ].map(function(i) {
              return (
                <div key={i.k} style={{ background: '#F1F5F9', borderRadius: 10, padding: '10px 14px' }}>
                  <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 4 }}>{i.k}</div>
                  <div style={{ fontWeight: 700 }}>{i.v}</div>
                </div>
              )
            })}
          </div>

          {/* Breakdown table */}
          <div className="card-title" style={{ marginBottom: 12 }}>Invoice Breakdown</div>
          <div style={{ background: '#F1F5F9', borderRadius: 12, overflow: 'hidden' }}>
            {[
              { label: 'Base Settlement Value', val: INR(selected.base), color: '#0D1F35', bold: false },
              { label: '− Commission (' + selected.plat + ')', val: '-' + INR(selected.comm), color: '#E8344A', bold: false },
              { label: '− Logistics / Shipping', val: '-' + INR(selected.logi), color: '#E8344A', bold: false },
              { label: '− Returns Deducted', val: '-' + INR(selected.ret), color: '#E8344A', bold: false },
              { label: '− TCS Deducted (1%)', val: '-' + INR(selected.tcs), color: '#E8344A', bold: false },
              selected.pen > 0 ? { label: '− Penalty Charge', val: '-' + INR(selected.pen), color: '#E9930D', bold: false } : null,
              { label: '= Net Settlement', val: INR(selected.net), color: '#0DB07A', bold: true },
            ].filter(Boolean).map(function(row, i) {
              return (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '10px 16px',
                  borderBottom: '1px solid #E2EBF3',
                  background: row.bold ? 'rgba(13,176,122,.08)' : 'transparent',
                }}>
                  <span style={{ color: '#4B6080', fontWeight: row.bold ? 700 : 400 }}>{row.label}</span>
                  <span style={{ color: row.color, fontWeight: row.bold ? 800 : 600 }}>{row.val}</span>
                </div>
              )
            })}
          </div>

          {/* Penalty warning */}
          {selected.pen > 0 && (
            <div className="ab warn" style={{ marginTop: 16, marginBottom: 0 }}>
              <span>⚠️</span>
              <div className="ab-body">
                <div className="ab-title">Penalty deduction found</div>
                <div className="ab-sub">This penalty may be raisable as a dispute if no prior notice was given</div>
              </div>
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}

export default Settlements
