import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import { Modal } from '../components/ui/Modal'
import useUIStore from '../store/uiStore'
import { INR } from '../utils/format'
import api from '../utils/api'

var borderColors = { won: '#0DB07A', open: '#E9930D', pending: '#2563EB', gst_pending: '#7B52E8' }
var routeColors = { Platform: '#0ABFCA', 'GST Revision': '#7B52E8', Legal: '#E8344A' }

var TIMELINE_EVENTS = [
  { title: 'Commission Overcharge Detected', sub: 'Rule Engine auto-flagged Amazon TRP-KNT-001', date: '2026-05-04', color: '#E8344A' },
  { title: 'Dispute Filed — Amazon', sub: 'AMZ-DISP-2026-4421 submitted via SPN portal', date: '2026-05-04', color: '#0ABFCA' },
  { title: 'Penalty Dispute Won', sub: 'FK-DISP-2026-6901 resolved — ₹640 credit confirmed', date: '2026-04-28', color: '#0DB07A' },
  { title: 'Return Overcharge Dispute', sub: 'MSH-DISP-2026-3312 filed for SPF violation', date: '2026-05-09', color: '#E9930D' },
  { title: 'TCS Claim Initiated', sub: 'GST-TCS-2026-Q4 — CA review in progress', date: '2026-04-15', color: '#7B52E8' },
  { title: 'Legal Notice Drafted', sub: 'Amazon weight overcharge — FBA § 8.4', date: '2026-05-11', color: '#E8344A' },
  { title: 'Flipkart Commission Dispute', sub: 'FK-DISP-2026-7823 escalated to Tier 2', date: '2026-05-06', color: '#2563EB' },
]

function Recovery() {
  var { data, loading } = useApi('/recovery/')
  var addToast = useUIStore(function(s) { return s.addToast })
  var navigate = useNavigate()
  var [updateModal, setUpdateModal] = useState(null)
  var [updateForm, setUpdateForm] = useState({ note: '', new_status: '' })

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary

  function handleLegalNotice(item) {
    api.post('/recovery/' + item.id + '/legal-notice').then(function() {
      addToast('Legal notice drafted for ' + item.ref, 'info', 'Ready for review')
    })
  }

  function handleUpdate() {
    api.put('/recovery/' + updateModal.id + '/update', updateForm).then(function() {
      addToast('Recovery case updated', 'success')
      setUpdateModal(null)
    })
  }

  return (
    <div className="page page-anim">
      {/* Stats */}
      <div className="stats-row cols-4">
        {[
          { label: 'Total Disputes Filed', val: data.items.length, stripe: 'tl' },
          { label: 'Won / Recovered', val: INR(s.won_amount), stripe: 'gn' },
          { label: 'In Progress', val: INR(s.open_amount), stripe: 'am' },
          { label: 'GST Recovery', val: INR(s.gst_amount), stripe: 'pu' },
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

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <button className="btn btn-p" onClick={function() { navigate('/dispute-engine') }}>
          + New via Rule Engine
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        {/* Recovery cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {data.items.map(function(item) {
            var route = item.route
            var routeColor = routeColors[route] || '#8FA5BD'
            return (
              <div key={item.id} className="card" style={{
                borderLeft: '4px solid ' + (borderColors[item.status] || '#8FA5BD'),
              }}>
                <div style={{ padding: '16px 20px' }}>
                  {/* Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: 15 }}>{item.type} — {item.platform}</div>
                      <div style={{ fontSize: 12, color: '#8FA5BD', marginTop: 2 }}>
                        <span className="mono">{item.ref}</span>
                        {item.sku && ' · ' + item.sku}
                        {' · Raised ' + item.raised}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ fontSize: 20, fontWeight: 800, color: '#0D1F35' }}>{INR(item.amount)}</div>
                      <StatusChip status={item.status} />
                    </div>
                  </div>

                  {/* Route badge + deadline */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <span style={{
                      padding: '3px 10px', borderRadius: 20,
                      background: routeColor + '20', color: routeColor,
                      fontSize: 11, fontWeight: 700,
                    }}>
                      {route}
                    </span>
                    {item.status !== 'won' && item.days_left !== null && (
                      <span style={{
                        fontSize: 12, color: item.days_left < 5 ? '#E8344A' : '#4B6080',
                        fontWeight: item.days_left < 5 ? 700 : 400,
                      }}>
                        {item.days_left < 5 ? '⚠️ ' : ''}
                        Expected {item.expected} · {item.days_left} days left
                      </span>
                    )}
                  </div>

                  {/* Notes */}
                  <div style={{ fontSize: 12, color: '#4B6080', marginBottom: 12 }}>{item.notes}</div>

                  {/* Won box */}
                  {item.status === 'won' && (
                    <div style={{
                      background: '#E6F7F2', border: '1px solid rgba(13,176,122,.25)',
                      borderRadius: 10, padding: '10px 14px', marginBottom: 12,
                      fontSize: 13, color: '#065F46', fontWeight: 600,
                    }}>
                      ✅ Recovered: {INR(item.amount)} credited
                    </div>
                  )}

                  {/* Footer buttons */}
                  <div style={{ display: 'flex', gap: 8 }}>
                    {(item.status === 'open' || item.status === 'pending') && (
                      <>
                        <button className="btn btn-s btn-sm" onClick={function() { setUpdateModal(item); setUpdateForm({ note: '', new_status: item.status }) }}>
                          Add Update
                        </button>
                        <button className="btn btn-d btn-sm" onClick={function() { addToast('Case escalated', 'warn') }}>
                          Escalate
                        </button>
                      </>
                    )}
                    {item.status === 'open' && (
                      <button className="btn btn-s btn-sm" onClick={function() { handleLegalNotice(item) }}>
                        ⚖ Legal Notice
                      </button>
                    )}
                    <button className="btn btn-g btn-sm" onClick={function() { addToast('Downloading evidence pack...', 'info') }}>
                      ⬇ Evidence Pack
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Timeline */}
        <div className="card">
          <div className="card-hd">
            <div className="card-title">Recovery Timeline</div>
          </div>
          <div className="card-bd">
            <div style={{ position: 'relative', paddingLeft: 24 }}>
              {/* Vertical line */}
              <div style={{
                position: 'absolute', left: 8, top: 8, bottom: 8,
                width: 2, background: '#E2EBF3',
              }} />
              {TIMELINE_EVENTS.map(function(ev, i) {
                return (
                  <div key={i} style={{ position: 'relative', marginBottom: 16 }}>
                    {/* Dot */}
                    <div style={{
                      position: 'absolute', left: -20, top: 2,
                      width: 10, height: 10, borderRadius: '50%',
                      background: ev.color, border: '2px solid #fff',
                      boxShadow: '0 0 0 2px ' + ev.color + '33',
                    }} />
                    <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 2 }}>{ev.title}</div>
                    <div style={{ fontSize: 11, color: '#4B6080', marginBottom: 2 }}>{ev.sub}</div>
                    <div className="mono" style={{ fontSize: 10, color: '#8FA5BD' }}>{ev.date}</div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Update Modal */}
      {updateModal && (
        <Modal
          open={!!updateModal}
          title={'Update Recovery Case ' + updateModal.id}
          sub={updateModal.type + ' — ' + updateModal.platform}
          onClose={function() { setUpdateModal(null) }}
          size="sm"
          footer={
            <>
              <button className="btn btn-s" onClick={function() { setUpdateModal(null) }}>Cancel</button>
              <button className="btn btn-p" onClick={handleUpdate}>Submit Update</button>
            </>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="fg">
              <label>Note</label>
              <textarea
                rows={3}
                value={updateForm.note}
                onChange={function(e) { setUpdateForm({ ...updateForm, note: e.target.value }) }}
                placeholder="Add a note about the latest development..."
              />
            </div>
            <div className="fg">
              <label>Update Status</label>
              <select value={updateForm.new_status} onChange={function(e) { setUpdateForm({ ...updateForm, new_status: e.target.value }) }}>
                {['open', 'pending', 'won', 'lost'].map(function(s) {
                  return <option key={s} value={s}>{s}</option>
                })}
              </select>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default Recovery
