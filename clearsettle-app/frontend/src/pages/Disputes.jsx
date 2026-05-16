import React, { useState } from 'react'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import { Modal } from '../components/ui/Modal'
import useUIStore from '../store/uiStore'
import { INR } from '../utils/format'
import api from '../utils/api'

var borderColor = { open: '#E9930D', pending: '#2563EB', won: '#0DB07A', lost: '#E8344A' }

function Disputes() {
  var { data, loading, error } = useApi('/disputes/')
  var addToast = useUIStore(function(s) { return s.addToast })
  var [newOpen, setNewOpen] = useState(false)
  var [viewItem, setViewItem] = useState(null)
  var [form, setForm] = useState({ platform: 'Amazon', dispute_type: 'Commission Overcharge', settlement_id: '', amount: '', description: '' })

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary
  var winRate = s.won_count > 0 ? Math.round((s.won_count / data.items.length) * 100) : 0

  function handleSubmit() {
    api.post('/disputes/', { ...form, amount: Number(form.amount) })
      .then(function() {
        addToast('Dispute raised successfully', 'success', 'Ref: ' + form.platform + ' · ' + form.dispute_type)
        setNewOpen(false)
        setForm({ platform: 'Amazon', dispute_type: 'Commission Overcharge', settlement_id: '', amount: '', description: '' })
      })
      .catch(function() { addToast('Failed to raise dispute', 'error') })
  }

  return (
    <div className="page page-anim">
      {/* Stats */}
      <div className="stats-row cols-4">
        {[
          { label: 'Total Disputed', val: INR(s.total_amount), stripe: 'tl' },
          { label: 'Open / Pending', val: s.open_count, stripe: 'am' },
          { label: 'Won', val: s.won_count, stripe: 'gn' },
          { label: 'Win Rate', val: winRate + '%', stripe: 'tl' },
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

      {/* Header + new button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <button className="btn btn-p" onClick={function() { setNewOpen(true) }}>
          + Raise New Dispute
        </button>
      </div>

      {/* Dispute cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {data.items.map(function(d) {
          return (
            <div key={d.id} className="card" style={{
              borderLeft: '4px solid ' + (borderColor[d.status] || '#8FA5BD'),
            }}>
              <div style={{ padding: '16px 20px' }}>
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 15 }}>
                      {d.icon} {d.plat} — {d.type}
                    </div>
                    <div style={{ fontSize: 12, color: '#8FA5BD', marginTop: 3 }}>
                      <span className="mono">{d.ref}</span> · Raised {d.raised} · Expected {d.expected}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: '#E8344A' }}>{INR(d.amt)}</div>
                    <StatusChip status={d.status} />
                  </div>
                </div>

                {/* Description */}
                <div style={{ fontSize: 13, color: '#4B6080', lineHeight: 1.6, marginBottom: 12 }}>
                  {d.desc}
                </div>

                {/* Won resolution */}
                {d.status === 'won' && d.resolution && (
                  <div style={{
                    background: '#E6F7F2', border: '1px solid rgba(13,176,122,.25)',
                    borderRadius: 10, padding: '10px 14px', marginBottom: 12,
                    fontSize: 13, color: '#065F46',
                  }}>
                    ✅ {d.resolution}
                  </div>
                )}

                {/* Footer buttons */}
                <div style={{ display: 'flex', gap: 8 }}>
                  {d.status !== 'won' && (
                    <>
                      <button className="btn btn-s btn-sm" onClick={function() { addToast('Update added for ' + d.ref, 'info') }}>
                        Add Update
                      </button>
                      <button className="btn btn-d btn-sm" onClick={function() { addToast('Escalated: ' + d.ref, 'warn', 'Dispute elevated to senior review') }}>
                        Escalate
                      </button>
                    </>
                  )}
                  <button className="btn btn-g btn-sm" onClick={function() { setViewItem(d) }}>
                    View Full →
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* New Dispute Modal */}
      <Modal
        open={newOpen}
        title="Raise New Dispute"
        sub="File a dispute for overcharges, penalties, or errors"
        onClose={function() { setNewOpen(false) }}
        size="lg"
        footer={
          <>
            <button className="btn btn-s" onClick={function() { setNewOpen(false) }}>Cancel</button>
            <button className="btn btn-p" onClick={handleSubmit}>Submit Dispute</button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="fr">
            <div className="fg">
              <label>Platform</label>
              <select value={form.platform} onChange={function(e) { setForm({ ...form, platform: e.target.value }) }}>
                {['Amazon', 'Flipkart', 'Meesho', 'Myntra', 'Nykaa'].map(function(p) {
                  return <option key={p}>{p}</option>
                })}
              </select>
            </div>
            <div className="fg">
              <label>Dispute Type</label>
              <select value={form.dispute_type} onChange={function(e) { setForm({ ...form, dispute_type: e.target.value }) }}>
                {['Commission Overcharge', 'Penalty Charge', 'Return Shipping Overcharge', 'Weight Overcharge', 'Duplicate Deduction'].map(function(t) {
                  return <option key={t}>{t}</option>
                })}
              </select>
            </div>
          </div>
          <div className="fr">
            <div className="fg">
              <label>Settlement ID</label>
              <input
                placeholder="e.g. AMZN-2026-0448"
                value={form.settlement_id}
                onChange={function(e) { setForm({ ...form, settlement_id: e.target.value }) }}
              />
            </div>
            <div className="fg">
              <label>Disputed Amount (₹)</label>
              <input
                type="number"
                placeholder="e.g. 5368"
                value={form.amount}
                onChange={function(e) { setForm({ ...form, amount: e.target.value }) }}
              />
            </div>
          </div>
          <div className="fg">
            <label>Description</label>
            <textarea
              rows={4}
              placeholder="Describe the overcharge or error in detail..."
              value={form.description}
              onChange={function(e) { setForm({ ...form, description: e.target.value }) }}
              style={{ resize: 'vertical' }}
            />
          </div>
          <div
            onClick={function() { addToast('File attachment feature coming soon', 'info') }}
            style={{
              border: '2px dashed #E2EBF3', borderRadius: 12,
              padding: '20px', textAlign: 'center',
              cursor: 'pointer', color: '#8FA5BD', fontSize: 13,
            }}
          >
            📎 Click to attach evidence files (PDF, PNG, XLSX)
          </div>
        </div>
      </Modal>

      {/* View detail modal */}
      {viewItem && (
        <Modal
          open={!!viewItem}
          title={viewItem.plat + ' — ' + viewItem.type}
          sub={viewItem.ref + ' · ' + INR(viewItem.amt)}
          onClose={function() { setViewItem(null) }}
          footer={<button className="btn btn-s" onClick={function() { setViewItem(null) }}>Close</button>}
        >
          <div style={{
            background: '#F1F5F9', borderRadius: 12, padding: '14px 18px',
            fontSize: 13, color: '#4B6080', lineHeight: 1.7, marginBottom: 16,
          }}>
            {viewItem.desc}
          </div>
          {viewItem.resolution ? (
            <div className="ab ok" style={{ marginBottom: 0 }}>
              <span>✅</span>
              <div className="ab-body">
                <div className="ab-title">Resolved</div>
                <div className="ab-sub">{viewItem.resolution}</div>
              </div>
            </div>
          ) : (
            <div className="ab inf" style={{ marginBottom: 0 }}>
              <span>⏳</span>
              <div className="ab-body">
                <div className="ab-title">Awaiting Response</div>
                <div className="ab-sub">Expected resolution by {viewItem.expected}</div>
              </div>
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}

export default Disputes
