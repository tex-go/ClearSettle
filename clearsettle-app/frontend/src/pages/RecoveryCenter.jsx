/**
 * RecoveryCenter — Phase 1 merge of Disputes + DisputeEngine + Recovery.
 *
 * Three tabs:
 *   ⚖️  Active Cases   — DiscrepancyEvent list (/disputes/), raise modal, escalation actions
 *   🤖  Detection Rules — Accordion of rule-engine rules (/dispute-engine/rules)
 *   💰  Calculator      — Recovery value estimator (/dispute-engine/calculator)
 *
 * Old routes /disputes, /recovery, /dispute-engine redirect here via App.jsx.
 */
import React, { useState, useEffect } from 'react'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import { Modal } from '../components/ui/Modal'
import useUIStore from '../store/uiStore'
import { INR } from '../utils/format'
import api from '../utils/api'

var RECOVERY_TABS = [
  { key: 'cases',      label: '⚖️ Active Cases' },
  { key: 'rules',      label: '🤖 Detection Rules' },
  { key: 'calculator', label: '💰 Calculator' },
]

var BORDER_COLOR = { open: '#E9930D', pending: '#2563EB', won: '#0DB07A', lost: '#E8344A' }

var VERDICT_STYLE = {
  'AUTO-DISPUTE': { bg: 'rgba(13,176,122,.12)',  color: '#065F46' },
  'GST RECOVERY': { bg: 'rgba(37,99,235,.12)',   color: '#1E40AF' },
  'INVESTIGATE':  { bg: 'rgba(233,147,13,.12)',  color: '#7A4E09' },
  'LISTING ALERT':{ bg: 'rgba(10,191,202,.12)',  color: '#088F99' },
}

var EMPTY_FORM = {
  platform: 'Amazon', dispute_type: 'Commission Overcharge',
  settlement_id: '', amount: '', description: '',
}

function RecoveryCenter() {
  var { data, loading }   = useApi('/disputes/')
  var addToast            = useUIStore(function(s) { return s.addToast })
  var [activeTab, setActiveTab] = useState('cases')

  // Cases tab
  var [newOpen, setNewOpen]   = useState(false)
  var [viewItem, setViewItem] = useState(null)
  var [form, setForm]         = useState(EMPTY_FORM)

  // Rules tab
  var [rulesData, setRulesData]       = useState(null)
  var [rulesLoading, setRulesLoading] = useState(false)
  var [expanded, setExpanded]         = useState(null)

  // Calculator tab
  var [calcParams, setCalcParams] = useState({ gmv: 5000000, years: 1, platform: 'multi', model: 's15' })
  var [calcResult, setCalcResult] = useState(null)

  // Load rules lazily when tab is first opened
  useEffect(function() {
    if (activeTab !== 'rules' || rulesData) return
    setRulesLoading(true)
    api.get('/dispute-engine/rules')
      .then(function(res) { setRulesData(res.data) })
      .catch(function() {})
      .finally(function() { setRulesLoading(false) })
  }, [activeTab, rulesData])

  // Refresh calculator when params change or tab is opened
  useEffect(function() {
    if (activeTab !== 'calculator') return
    var params = new URLSearchParams({
      gmv: calcParams.gmv, years: calcParams.years,
      platform: calcParams.platform, model: calcParams.model,
    })
    api.get('/dispute-engine/calculator?' + params.toString())
      .then(function(res) { setCalcResult(res.data) })
      .catch(function() {})
  }, [activeTab, calcParams.gmv, calcParams.years, calcParams.platform, calcParams.model])

  function handleSubmit() {
    api.post('/disputes/', { ...form, amount: Number(form.amount) })
      .then(function() {
        addToast('Dispute raised', 'success', form.platform + ' · ' + form.dispute_type)
        setNewOpen(false)
        setForm(EMPTY_FORM)
      })
      .catch(function() { addToast('Failed to raise dispute', 'error') })
  }

  function handleLegalNotice(item) {
    api.post('/recovery/' + item.id + '/legal-notice')
      .then(function() { addToast('Legal notice drafted for ' + item.ref, 'info', 'Ready for review') })
  }

  // ── Tab bar ───────────────────────────────────────────────────
  var tabBar = (
    <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '2px solid #E8EEF4' }}>
      {RECOVERY_TABS.map(function(t) {
        var active = activeTab === t.key
        return (
          <button key={t.key} onClick={function() { setActiveTab(t.key) }} style={{
            padding: '10px 20px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            background: 'transparent',
            color: active ? '#0ABFCA' : '#8FA5BD',
            borderBottom: active ? '2px solid #0ABFCA' : '2px solid transparent',
            marginBottom: -2,
          }}>{t.label}</button>
        )
      })}
    </div>
  )

  return (
    <div className="page page-anim">
      {tabBar}

      {/* ════════ ACTIVE CASES ════════════════════════════════════════ */}
      {activeTab === 'cases' && (
        <>
          {(loading || !data) ? (
            <div className="loading-wrap"><div className="spinner" /></div>
          ) : (
            <>
              {/* Stats */}
              {(function() {
                var s = data.summary
                var winRate = s.won_count > 0 ? Math.round((s.won_count / (data.items.length || 1)) * 100) : 0
                return (
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
                )
              })()}

              {/* Action bar */}
              <div className="page-hd-actions" style={{ marginBottom: 20, justifyContent: 'flex-end' }}>
                <button className="btn btn-p" onClick={function() { setNewOpen(true) }}>
                  + Raise New Dispute
                </button>
              </div>

              {data.items.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '60px 0', color: '#8FA5BD' }}>
                  <div style={{ fontSize: 40, marginBottom: 12 }}>⚖️</div>
                  <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>No disputes yet</div>
                  <div style={{ fontSize: 13 }}>
                    File disputes from Commission Audit or Returns, or raise one manually.
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {data.items.map(function(d) {
                    return (
                      <div key={d.id} className="card" style={{
                        borderLeft: '4px solid ' + (BORDER_COLOR[d.status] || '#8FA5BD'),
                      }}>
                        <div style={{ padding: '16px 20px' }}>
                          {/* Header */}
                          <div className="dispute-hd">
                            <div>
                              <div style={{ fontWeight: 800, fontSize: 15 }}>
                                {d.icon} {d.plat} — {d.type}
                              </div>
                              <div style={{ fontSize: 12, color: '#8FA5BD', marginTop: 3 }}>
                                <span className="mono">{d.ref}</span>
                                {' · Raised '}{d.raised}{' · Expected '}{d.expected}
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

                          {/* Action buttons */}
                          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                            {d.status !== 'won' && (
                              <>
                                <button className="btn btn-s btn-sm" onClick={function() {
                                  addToast('Update added for ' + d.ref, 'info')
                                }}>
                                  Add Update
                                </button>
                                <button className="btn btn-d btn-sm" onClick={function() {
                                  addToast('Escalated: ' + d.ref, 'warn', 'Elevated to senior review')
                                }}>
                                  Escalate
                                </button>
                                <button className="btn btn-s btn-sm" onClick={function() { handleLegalNotice(d) }}>
                                  ⚖ Legal Notice
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
              )}
            </>
          )}
        </>
      )}

      {/* ════════ DETECTION RULES ════════════════════════════════════ */}
      {activeTab === 'rules' && (
        <>
          {rulesLoading || !rulesData ? (
            <div className="loading-wrap"><div className="spinner" /></div>
          ) : (
            <>
              <div className="stats-row cols-2" style={{ marginBottom: 20 }}>
                {[
                  { label: 'Rules Active',     val: rulesData.items.length,      stripe: 'tl' },
                  { label: 'Auto-Raise Rules', val: rulesData.auto_raise_count,  stripe: 'gn' },
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

              <div className="ab inf" style={{ marginBottom: 20 }}>
                <span>🤖</span>
                <div className="ab-body">
                  <div className="ab-title">How the Dispute Rule Engine works</div>
                  <div className="ab-sub">
                    Every settlement is scanned against these rules. Auto-raise rules file disputes instantly.
                    Manual rules flag items for review. All evidence is auto-collected for platform portals.
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {rulesData.items.map(function(rule) {
                  var isOpen = expanded === rule.id
                  var vs = VERDICT_STYLE[rule.verdict] || { bg: '#F1F5F9', color: '#4B6080' }
                  return (
                    <div key={rule.id} className="card" style={{ overflow: 'hidden' }}>
                      {/* Collapsed header */}
                      <div
                        onClick={function() { setExpanded(isOpen ? null : rule.id) }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 14,
                          padding: '14px 20px', cursor: 'pointer',
                          borderBottom: isOpen ? '1px solid #E2EBF3' : 'none',
                        }}
                      >
                        <div style={{ flex: 1, fontWeight: 700, fontSize: 14 }}>{rule.name}</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          {rule.verdict && (
                            <span style={{
                              padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                              background: vs.bg, color: vs.color,
                            }}>
                              {rule.verdict}
                            </span>
                          )}
                          {rule.auto_raise && (
                            <span className="cs-chip cs-chip-gn" style={{ fontSize: 10 }}>AUTO</span>
                          )}
                          <span style={{
                            fontSize: 16, color: '#8FA5BD',
                            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                            transition: 'transform .2s', display: 'inline-block',
                          }}>▼</span>
                        </div>
                      </div>

                      {/* Expanded body */}
                      {isOpen && (
                        <div style={{ padding: '18px 20px', animation: 'slideDown .2s ease both' }}>
                          {rule.description && (
                            <div style={{ fontSize: 13, color: '#4B6080', marginBottom: 14, lineHeight: 1.6 }}>
                              {rule.description}
                            </div>
                          )}
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10, marginBottom: 14 }}>
                            {[
                              { k: 'Category',      v: rule.category },
                              { k: 'Severity',      v: rule.severity },
                              { k: 'Rule Type',     v: rule.rule_type },
                              { k: 'Platform',      v: rule.platform || 'All' },
                              { k: 'Dispute Window', v: rule.dispute_window },
                              { k: 'Success Rate',  v: rule.success_rate_pct != null ? rule.success_rate_pct + '%' : '—' },
                            ].map(function(m) {
                              return (
                                <div key={m.k} style={{ padding: '10px 14px', borderRadius: 10, background: '#F1F5F9' }}>
                                  <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#8FA5BD', marginBottom: 4 }}>{m.k}</div>
                                  <div style={{ fontSize: 12, color: '#0D1F35', fontWeight: 600 }}>{m.v || '—'}</div>
                                </div>
                              )
                            })}
                          </div>
                          {rule.legal_basis && (
                            <div style={{ fontSize: 12, color: '#4B6080', marginBottom: 10 }}>
                              <span style={{ fontWeight: 700 }}>Legal Basis: </span>{rule.legal_basis}
                            </div>
                          )}
                          {rule.playbook_notes && (
                            <div style={{ fontSize: 12, color: '#4B6080' }}>
                              <span style={{ fontWeight: 700 }}>Playbook: </span>{rule.playbook_notes}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </>
      )}

      {/* ════════ RECOVERY CALCULATOR ════════════════════════════════ */}
      {activeTab === 'calculator' && (
        <div className="card" style={{ border: '1.5px solid #0ABFCA' }}>
          <div className="card-hd">
            <div>
              <div className="card-title">💰 Recovery Calculator</div>
              <div className="card-sub">Estimate your recoverable amount based on GMV and platform</div>
            </div>
          </div>
          <div className="card-bd">
            <div className="input-grid-4">
              <div className="fg">
                <label>Annual GMV (₹)</label>
                <input
                  type="number"
                  value={calcParams.gmv}
                  onChange={function(e) { setCalcParams({ ...calcParams, gmv: Number(e.target.value) }) }}
                />
              </div>
              <div className="fg">
                <label>Years of Data</label>
                <select value={calcParams.years} onChange={function(e) { setCalcParams({ ...calcParams, years: Number(e.target.value) }) }}>
                  {[1, 2, 3].map(function(y) { return <option key={y} value={y}>{y} Year{y > 1 ? 's' : ''}</option> })}
                </select>
              </div>
              <div className="fg">
                <label>Primary Platform</label>
                <select value={calcParams.platform} onChange={function(e) { setCalcParams({ ...calcParams, platform: e.target.value }) }}>
                  {[
                    { val: 'amazon',   label: 'Amazon' },
                    { val: 'flipkart', label: 'Flipkart' },
                    { val: 'meesho',   label: 'Meesho' },
                    { val: 'multi',    label: 'Multi-Platform' },
                  ].map(function(o) { return <option key={o.val} value={o.val}>{o.label}</option> })}
                </select>
              </div>
              <div className="fg">
                <label>Fee Model</label>
                <select value={calcParams.model} onChange={function(e) { setCalcParams({ ...calcParams, model: e.target.value }) }}>
                  {[
                    { val: 's15',  label: 'Success Fee 15%' },
                    { val: 's20',  label: 'Success Fee 20%' },
                    { val: 's25',  label: 'Success Fee 25%' },
                    { val: 'saas', label: 'SaaS ₹1,499/mo' },
                  ].map(function(o) { return <option key={o.val} value={o.val}>{o.label}</option> })}
                </select>
              </div>
            </div>

            {calcResult && (
              <div style={{
                background: '#0D1F35', borderRadius: 14, padding: '20px 24px', marginTop: 20,
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
              }}>
                {[
                  { label: 'Total GMV Analysed',            val: INR(calcResult.total_gmv),             color: '#E2EBF3' },
                  { label: 'Raw Overcharges Found',         val: INR(calcResult.raw_overcharge),         color: '#F87171' },
                  { label: '→ Platform dispute window',     val: INR(calcResult.platform_dispute),       color: '#FCD34D' },
                  { label: '→ Legal notice route (2yr CPA)',val: INR(calcResult.legal_route),            color: '#FCD34D' },
                  { label: 'TCS/GST Unclaimed',             val: INR(calcResult.gst_recovery),          color: '#FCD34D' },
                  null,
                  { label: 'Total Recoverable for Vendor',  val: INR(calcResult.total_recoverable),     color: '#34D399', large: true },
                  { label: 'ClearSettle Earnings',          val: INR(calcResult.clearsettle_earnings),  color: '#0ABFCA', large: true },
                ].map(function(row, i) {
                  if (!row) return <div key={i} />
                  return (
                    <div key={i}>
                      <div style={{ fontSize: 11, color: '#4B6080', marginBottom: 4 }}>{row.label}</div>
                      <div style={{
                        fontSize: row.large ? 22 : 16, fontWeight: row.large ? 800 : 700,
                        color: row.color, fontFamily: 'JetBrains Mono, monospace',
                      }}>{row.val}</div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── New Dispute Modal ────────────────────────────────────── */}
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
              border: '2px dashed #E2EBF3', borderRadius: 12, padding: '20px',
              textAlign: 'center', cursor: 'pointer', color: '#8FA5BD', fontSize: 13,
            }}
          >
            📎 Click to attach evidence files (PDF, PNG, XLSX)
          </div>
        </div>
      </Modal>

      {/* ── View Detail Modal ───────────────────────────────────── */}
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

export default RecoveryCenter
