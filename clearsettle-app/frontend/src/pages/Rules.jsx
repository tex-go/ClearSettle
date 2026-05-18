import React, { useState, useEffect, useCallback } from 'react'
import api from '../utils/api'
import { INR } from '../utils/format'

var VERDICT_STYLE = {
  'AUTO-DISPUTE':  { bg: 'rgba(13,176,122,.12)',  color: '#065F46',  border: '#0DB07A' },
  'GST RECOVERY':  { bg: 'rgba(37,99,235,.12)',   color: '#1E40AF',  border: '#2563EB' },
  'INVESTIGATE':   { bg: 'rgba(233,147,13,.12)',  color: '#7A4E09',  border: '#E9930D' },
  'LISTING ALERT': { bg: 'rgba(10,191,202,.12)',  color: '#088F99',  border: '#0ABFCA' },
}

var SEV_COLOR = { critical: '#E8344A', warning: '#E9930D', info: '#0ABFCA' }
var CATEGORIES = ['fees', 'payout', 'tax', 'returns', 'risk', 'custom']
var RULE_TYPES = [
  'commission_overcharge', 'missing_payout', 'duplicate_deduction', 'tcs_mismatch',
  'penalty_overcharge', 'high_return_rate', 'payout_delay', 'gst_discrepancy', 'custom',
]
var SEVERITIES = ['info', 'warning', 'critical']
var VERDICTS   = ['AUTO-DISPUTE', 'GST RECOVERY', 'INVESTIGATE', 'LISTING ALERT']
var OPERATORS  = ['gt', 'lt', 'gte', 'lte', 'eq', 'neq', 'contains', 'in', 'not_in', 'exists']
var VALUE_TYPES = ['number', 'string', 'boolean', 'list']
var PLATFORMS  = ['amazon', 'flipkart', 'meesho', 'myntra', 'nykaa', 'ajio', 'snapdeal', 'jiomart']
var ACTIONS    = ['create_discrepancy', 'create_alert', 'auto_dispute', 'recommend_recovery', 'send_notification', 'escalate_case']

var EMPTY_RULE = {
  name: '', description: '', category: 'fees', rule_type: 'custom', severity: 'warning',
  priority: 100, platform: '', is_enabled: true, condition_logic: 'all',
  parameters_json: '{}', recovery_metadata_json: '{}',
  verdict: '', legal_basis: '', evidence_json: '[]', dispute_window: '',
  success_rate_pct: '', recovery_min: '', recovery_max: '',
  auto_raise: false, playbook_notes: '',
  conditions: [], actions: [],
}

function Badge({ text, style }) {
  if (!text) return null
  var vs = style || VERDICT_STYLE[text] || { bg: '#F1F5F9', color: '#475569', border: '#CBD5E1' }
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, letterSpacing: '0.04em',
      padding: '2px 8px', borderRadius: 99,
      background: vs.bg, color: vs.color,
      border: `1px solid ${vs.border || vs.color}`,
    }}>
      {text}
    </span>
  )
}

function SevDot({ sev }) {
  return <span style={{ width: 8, height: 8, borderRadius: '50%', background: SEV_COLOR[sev] || '#94A3B8', display: 'inline-block', marginRight: 4 }} />
}

function Toggle({ checked, onChange }) {
  return (
    <div
      onClick={function(e) { e.stopPropagation(); onChange(!checked) }}
      style={{
        width: 40, height: 22, borderRadius: 11, cursor: 'pointer',
        background: checked ? '#0DB07A' : '#CBD5E1',
        position: 'relative', transition: 'background .2s', flexShrink: 0,
      }}
    >
      <div style={{
        position: 'absolute', top: 3, left: checked ? 20 : 3,
        width: 16, height: 16, borderRadius: '50%', background: '#fff',
        transition: 'left .2s', boxShadow: '0 1px 3px rgba(0,0,0,.2)',
      }} />
    </div>
  )
}

function EvidenceList({ json }) {
  var items = []
  try { items = JSON.parse(json || '[]') } catch { items = [] }
  if (!items.length) return <span style={{ color: '#94A3B8' }}>—</span>
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
      {items.map(function(ev, i) {
        return (
          <span key={i} style={{ fontSize: 11, padding: '2px 7px', borderRadius: 99, background: '#F1F5F9', color: '#475569', border: '1px solid #E2E8F0' }}>
            {ev}
          </span>
        )
      })}
    </div>
  )
}

function ConditionBuilder({ conditions, onChange }) {
  function add() {
    onChange([...conditions, { field: '', operator: 'gt', value: '', value_type: 'number', description: '' }])
  }
  function remove(i) {
    onChange(conditions.filter(function(_, idx) { return idx !== i }))
  }
  function update(i, key, val) {
    onChange(conditions.map(function(c, idx) { return idx === i ? { ...c, [key]: val } : c }))
  }

  return (
    <div>
      {conditions.map(function(c, i) {
        return (
          <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' }}>
            <input
              placeholder="field (e.g. fee_rate_pct)"
              value={c.field} onChange={function(e) { update(i, 'field', e.target.value) }}
              style={{ flex: 2, minWidth: 120, padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}
            />
            <select value={c.operator} onChange={function(e) { update(i, 'operator', e.target.value) }}
              style={{ padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}>
              {OPERATORS.map(function(op) { return <option key={op} value={op}>{op}</option> })}
            </select>
            <input
              placeholder="value"
              value={c.value} onChange={function(e) { update(i, 'value', e.target.value) }}
              style={{ flex: 1, minWidth: 80, padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}
            />
            <select value={c.value_type} onChange={function(e) { update(i, 'value_type', e.target.value) }}
              style={{ padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}>
              {VALUE_TYPES.map(function(vt) { return <option key={vt} value={vt}>{vt}</option> })}
            </select>
            <input
              placeholder="description (optional)"
              value={c.description} onChange={function(e) { update(i, 'description', e.target.value) }}
              style={{ flex: 2, minWidth: 120, padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}
            />
            <button onClick={function() { remove(i) }}
              style={{ padding: '6px 10px', background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FECACA', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
              ✕
            </button>
          </div>
        )
      })}
      <button onClick={add}
        style={{ padding: '6px 14px', background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', borderRadius: 6, cursor: 'pointer', fontSize: 13, marginTop: 2 }}>
        + Add Condition
      </button>
    </div>
  )
}

function ActionBuilder({ actions, onChange }) {
  function add() {
    onChange([...actions, { action_type: 'create_discrepancy', action_order: actions.length + 1, parameters_json: '{}', is_enabled: true }])
  }
  function remove(i) {
    onChange(actions.filter(function(_, idx) { return idx !== i }))
  }
  function update(i, key, val) {
    onChange(actions.map(function(a, idx) { return idx === i ? { ...a, [key]: val } : a }))
  }

  return (
    <div>
      {actions.map(function(a, i) {
        return (
          <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' }}>
            <select value={a.action_type} onChange={function(e) { update(i, 'action_type', e.target.value) }}
              style={{ flex: 2, minWidth: 180, padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}>
              {ACTIONS.map(function(at) { return <option key={at} value={at}>{at}</option> })}
            </select>
            <input
              type="number" placeholder="order" value={a.action_order}
              onChange={function(e) { update(i, 'action_order', parseInt(e.target.value) || 1) }}
              style={{ width: 60, padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}
            />
            <input
              placeholder='params JSON e.g. {"auto_log": true}'
              value={a.parameters_json} onChange={function(e) { update(i, 'parameters_json', e.target.value) }}
              style={{ flex: 3, minWidth: 120, padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}
            />
            <Toggle checked={a.is_enabled} onChange={function(v) { update(i, 'is_enabled', v) }} />
            <button onClick={function() { remove(i) }}
              style={{ padding: '6px 10px', background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FECACA', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
              ✕
            </button>
          </div>
        )
      })}
      <button onClick={add}
        style={{ padding: '6px 14px', background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', borderRadius: 6, cursor: 'pointer', fontSize: 13, marginTop: 2 }}>
        + Add Action
      </button>
    </div>
  )
}

function EvidenceEditor({ value, onChange }) {
  var items = []
  try { items = JSON.parse(value || '[]') } catch { items = [] }

  function addItem() {
    var next = [...items, '']
    onChange(JSON.stringify(next))
  }
  function updateItem(i, v) {
    var next = items.map(function(it, idx) { return idx === i ? v : it })
    onChange(JSON.stringify(next))
  }
  function removeItem(i) {
    var next = items.filter(function(_, idx) { return idx !== i })
    onChange(JSON.stringify(next))
  }

  return (
    <div>
      {items.map(function(item, i) {
        return (
          <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
            <input value={item} onChange={function(e) { updateItem(i, e.target.value) }}
              placeholder="Evidence document"
              style={{ flex: 1, padding: '6px 8px', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 13 }}
            />
            <button onClick={function() { removeItem(i) }}
              style={{ padding: '6px 10px', background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FECACA', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
              ✕
            </button>
          </div>
        )
      })}
      <button onClick={addItem}
        style={{ padding: '6px 14px', background: '#F0FDF4', color: '#059669', border: '1px solid #A7F3D0', borderRadius: 6, cursor: 'pointer', fontSize: 13, marginTop: 2 }}>
        + Add Evidence
      </button>
    </div>
  )
}

function Modal({ rule, onClose, onSave, saving }) {
  var [form, setForm] = useState(function() {
    if (!rule) return { ...EMPTY_RULE }
    return {
      ...rule,
      platform: rule.platform || '',
      verdict: rule.verdict || '',
      legal_basis: rule.legal_basis || '',
      dispute_window: rule.dispute_window || '',
      success_rate_pct: rule.success_rate_pct != null ? String(rule.success_rate_pct) : '',
      recovery_min: rule.recovery_min != null ? String(rule.recovery_min) : '',
      recovery_max: rule.recovery_max != null ? String(rule.recovery_max) : '',
      playbook_notes: rule.playbook_notes || '',
      evidence_json: rule.evidence_json || '[]',
      conditions: rule.conditions || [],
      actions: rule.actions || [],
    }
  })
  var [tab, setTab] = useState('basic')

  function set(key, val) {
    setForm(function(f) { return { ...f, [key]: val } })
  }

  function handleSave() {
    var payload = {
      ...form,
      platform: form.platform || null,
      verdict: form.verdict || null,
      legal_basis: form.legal_basis || null,
      dispute_window: form.dispute_window || null,
      success_rate_pct: form.success_rate_pct !== '' ? parseFloat(form.success_rate_pct) : null,
      recovery_min: form.recovery_min !== '' ? parseFloat(form.recovery_min) : null,
      recovery_max: form.recovery_max !== '' ? parseFloat(form.recovery_max) : null,
      playbook_notes: form.playbook_notes || null,
      priority: parseInt(form.priority) || 100,
    }
    onSave(payload)
  }

  var tabs = [
    { id: 'basic',    label: 'Basic' },
    { id: 'conditions', label: `Conditions (${form.conditions.length})` },
    { id: 'actions',  label: `Actions (${(form.actions || []).length})` },
    { id: 'legal',    label: 'Legal & Recovery' },
  ]

  var inputStyle = { width: '100%', padding: '8px 10px', border: '1px solid #E2E8F0', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }
  var labelStyle = { fontSize: 12, fontWeight: 600, color: '#64748B', marginBottom: 4, display: 'block' }
  var rowStyle   = { marginBottom: 14 }
  var halfRow    = { display: 'flex', gap: 12, marginBottom: 14 }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ background: '#fff', borderRadius: 16, width: '100%', maxWidth: 780, maxHeight: '92vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(0,0,0,.2)' }}>
        {/* Header */}
        <div style={{ padding: '20px 24px 0', borderBottom: '1px solid #F1F5F9' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#0F172A' }}>
              {rule ? 'Edit Rule' : 'Create Rule'}
            </h2>
            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#94A3B8' }}>✕</button>
          </div>
          <div style={{ display: 'flex', gap: 0, marginBottom: -1 }}>
            {tabs.map(function(t) {
              return (
                <button key={t.id} onClick={function() { setTab(t.id) }}
                  style={{
                    padding: '8px 16px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                    borderBottom: tab === t.id ? '2px solid #2563EB' : '2px solid transparent',
                    color: tab === t.id ? '#2563EB' : '#64748B',
                    background: 'none',
                  }}>
                  {t.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>

          {tab === 'basic' && (
            <div>
              <div style={rowStyle}>
                <label style={labelStyle}>Rule Name *</label>
                <input value={form.name} onChange={function(e) { set('name', e.target.value) }} style={inputStyle} placeholder="e.g. Commission Rate Overcharge" />
              </div>
              <div style={rowStyle}>
                <label style={labelStyle}>Description</label>
                <textarea value={form.description} onChange={function(e) { set('description', e.target.value) }}
                  style={{ ...inputStyle, minHeight: 70, resize: 'vertical' }} placeholder="What this rule detects..." />
              </div>
              <div style={halfRow}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Category *</label>
                  <select value={form.category} onChange={function(e) { set('category', e.target.value) }} style={inputStyle}>
                    {CATEGORIES.map(function(c) { return <option key={c} value={c}>{c}</option> })}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Rule Type *</label>
                  <select value={form.rule_type} onChange={function(e) { set('rule_type', e.target.value) }} style={inputStyle}>
                    {RULE_TYPES.map(function(rt) { return <option key={rt} value={rt}>{rt}</option> })}
                  </select>
                </div>
              </div>
              <div style={halfRow}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Severity *</label>
                  <select value={form.severity} onChange={function(e) { set('severity', e.target.value) }} style={inputStyle}>
                    {SEVERITIES.map(function(s) { return <option key={s} value={s}>{s}</option> })}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Priority (lower = first)</label>
                  <input type="number" value={form.priority} onChange={function(e) { set('priority', e.target.value) }} style={inputStyle} />
                </div>
              </div>
              <div style={halfRow}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Platform (blank = all)</label>
                  <select value={form.platform} onChange={function(e) { set('platform', e.target.value) }} style={inputStyle}>
                    <option value="">All Platforms</option>
                    {PLATFORMS.map(function(p) { return <option key={p} value={p}>{p}</option> })}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Condition Logic</label>
                  <select value={form.condition_logic} onChange={function(e) { set('condition_logic', e.target.value) }} style={inputStyle}>
                    <option value="all">ALL must match (AND)</option>
                    <option value="any">ANY must match (OR)</option>
                  </select>
                </div>
              </div>
              <div style={halfRow}>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10, paddingTop: 18 }}>
                  <Toggle checked={form.is_enabled} onChange={function(v) { set('is_enabled', v) }} />
                  <span style={{ fontSize: 14, color: '#374151' }}>Rule Enabled</span>
                </div>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10, paddingTop: 18 }}>
                  <Toggle checked={form.auto_raise} onChange={function(v) { set('auto_raise', v) }} />
                  <span style={{ fontSize: 14, color: '#374151' }}>Auto-Raise Dispute</span>
                </div>
              </div>
            </div>
          )}

          {tab === 'conditions' && (
            <div>
              <p style={{ margin: '0 0 12px', fontSize: 13, color: '#64748B' }}>
                Define when this rule fires. Fields are checked against the settlement context.
              </p>
              <ConditionBuilder conditions={form.conditions} onChange={function(v) { set('conditions', v) }} />
            </div>
          )}

          {tab === 'actions' && (
            <div>
              <p style={{ margin: '0 0 12px', fontSize: 13, color: '#64748B' }}>
                Actions executed when the rule matches (in priority order).
              </p>
              <ActionBuilder actions={form.actions || []} onChange={function(v) { set('actions', v) }} />
            </div>
          )}

          {tab === 'legal' && (
            <div>
              <div style={halfRow}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Verdict / Outcome Type</label>
                  <select value={form.verdict} onChange={function(e) { set('verdict', e.target.value) }} style={inputStyle}>
                    <option value="">Select verdict...</option>
                    {VERDICTS.map(function(v) { return <option key={v} value={v}>{v}</option> })}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Dispute Window</label>
                  <input value={form.dispute_window} onChange={function(e) { set('dispute_window', e.target.value) }}
                    style={inputStyle} placeholder="e.g. 90 days from settlement date" />
                </div>
              </div>
              <div style={rowStyle}>
                <label style={labelStyle}>Legal Basis</label>
                <textarea value={form.legal_basis} onChange={function(e) { set('legal_basis', e.target.value) }}
                  style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }}
                  placeholder="e.g. Consumer Protection Act 2019 § 2(47) — unfair trade practice" />
              </div>
              <div style={rowStyle}>
                <label style={labelStyle}>Required Evidence Documents</label>
                <EvidenceEditor value={form.evidence_json} onChange={function(v) { set('evidence_json', v) }} />
              </div>
              <div style={rowStyle}>
                <label style={labelStyle}>Immediate Action / Playbook</label>
                <textarea value={form.playbook_notes} onChange={function(e) { set('playbook_notes', e.target.value) }}
                  style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }}
                  placeholder="What to do immediately when this rule fires..." />
              </div>
              <div style={halfRow}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Success Rate (%)</label>
                  <input type="number" step="0.1" value={form.success_rate_pct}
                    onChange={function(e) { set('success_rate_pct', e.target.value) }}
                    style={inputStyle} placeholder="e.g. 92.0" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Recovery Min (₹)</label>
                  <input type="number" value={form.recovery_min}
                    onChange={function(e) { set('recovery_min', e.target.value) }}
                    style={inputStyle} placeholder="e.g. 8000" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Recovery Max (₹)</label>
                  <input type="number" value={form.recovery_max}
                    onChange={function(e) { set('recovery_max', e.target.value) }}
                    style={inputStyle} placeholder="e.g. 55000" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid #F1F5F9', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button onClick={onClose}
            style={{ padding: '9px 20px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, cursor: 'pointer', fontSize: 14, color: '#374151' }}>
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving || !form.name}
            style={{ padding: '9px 20px', background: saving || !form.name ? '#93C5FD' : '#2563EB', color: '#fff', border: 'none', borderRadius: 8, cursor: saving || !form.name ? 'default' : 'pointer', fontSize: 14, fontWeight: 600 }}>
            {saving ? 'Saving…' : rule ? 'Save Changes' : 'Create Rule'}
          </button>
        </div>
      </div>
    </div>
  )
}

function RuleCard({ rule, onToggle, onEdit, onDelete, expanded, onExpand }) {
  var vs = VERDICT_STYLE[rule.verdict] || {}
  var isGlobal = !rule.company_id
  var evidence = []
  try { evidence = JSON.parse(rule.evidence_json || '[]') } catch { evidence = [] }

  return (
    <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E2E8F0', marginBottom: 10, overflow: 'hidden' }}>
      <div
        onClick={function() { onExpand(expanded ? null : rule.id) }}
        style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', background: expanded ? '#F8FAFC' : '#fff' }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: 14, color: '#0F172A' }}>{rule.name}</span>
            {rule.verdict && <Badge text={rule.verdict} />}
            {isGlobal && (
              <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 99, background: '#FEF3C7', color: '#92400E', border: '1px solid #FDE68A', fontWeight: 600 }}>
                GLOBAL
              </span>
            )}
            {rule.auto_raise && (
              <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 99, background: '#DCFCE7', color: '#166534', border: '1px solid #BBF7D0', fontWeight: 600 }}>
                AUTO
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: '#64748B' }}>
              <SevDot sev={rule.severity} />{rule.severity}
            </span>
            <span style={{ fontSize: 12, color: '#94A3B8' }}>•</span>
            <span style={{ fontSize: 12, color: '#64748B' }}>{rule.category}</span>
            <span style={{ fontSize: 12, color: '#94A3B8' }}>•</span>
            <span style={{ fontSize: 12, color: '#64748B' }}>{rule.rule_type}</span>
            {rule.platform && (
              <>
                <span style={{ fontSize: 12, color: '#94A3B8' }}>•</span>
                <span style={{ fontSize: 12, color: '#2563EB' }}>{rule.platform}</span>
              </>
            )}
            {rule.success_rate_pct != null && (
              <>
                <span style={{ fontSize: 12, color: '#94A3B8' }}>•</span>
                <span style={{ fontSize: 12, color: '#059669', fontWeight: 600 }}>{rule.success_rate_pct}% success</span>
              </>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Toggle checked={rule.is_enabled} onChange={function() { onToggle(rule) }} />
          {!isGlobal && (
            <>
              <button onClick={function(e) { e.stopPropagation(); onEdit(rule) }}
                style={{ padding: '5px 12px', background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                Edit
              </button>
              <button onClick={function(e) { e.stopPropagation(); onDelete(rule) }}
                style={{ padding: '5px 12px', background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FECACA', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                Delete
              </button>
            </>
          )}
          {isGlobal && (
            <button onClick={function(e) { e.stopPropagation(); onEdit(rule) }}
              style={{ padding: '5px 12px', background: '#F8FAFC', color: '#64748B', border: '1px solid #E2E8F0', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              View
            </button>
          )}
          <span style={{ fontSize: 12, color: '#94A3B8', userSelect: 'none' }}>{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid #F1F5F9' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginTop: 14 }}>
            {/* Conditions */}
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', letterSpacing: '0.06em', marginBottom: 8 }}>CONDITIONS ({rule.condition_logic?.toUpperCase()})</div>
              {(rule.conditions || []).length === 0 ? (
                <span style={{ fontSize: 13, color: '#94A3B8' }}>No conditions defined</span>
              ) : (rule.conditions || []).map(function(c, i) {
                return (
                  <div key={i} style={{ fontSize: 13, color: '#374151', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, color: '#2563EB' }}>{c.field}</span>
                    {' '}<span style={{ color: '#94A3B8' }}>{c.operator}</span>{' '}
                    <span style={{ fontWeight: 600 }}>{c.value}</span>
                    {' '}<span style={{ color: '#94A3B8', fontSize: 11 }}>({c.value_type})</span>
                    {c.description && <div style={{ fontSize: 11, color: '#94A3B8' }}>{c.description}</div>}
                  </div>
                )
              })}
            </div>

            {/* Legal */}
            {(rule.legal_basis || rule.dispute_window) && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', letterSpacing: '0.06em', marginBottom: 8 }}>LEGAL BASIS</div>
                {rule.legal_basis && <div style={{ fontSize: 13, color: '#374151', marginBottom: 6 }}>{rule.legal_basis}</div>}
                {rule.dispute_window && (
                  <div style={{ fontSize: 13, color: '#64748B' }}>
                    <span style={{ fontWeight: 600 }}>Window:</span> {rule.dispute_window}
                  </div>
                )}
              </div>
            )}

            {/* Evidence */}
            {evidence.length > 0 && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', letterSpacing: '0.06em', marginBottom: 8 }}>EVIDENCE REQUIRED</div>
                <EvidenceList json={rule.evidence_json} />
              </div>
            )}

            {/* Recovery */}
            {(rule.recovery_min != null || rule.playbook_notes) && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94A3B8', letterSpacing: '0.06em', marginBottom: 8 }}>RECOVERY</div>
                {rule.recovery_min != null && rule.recovery_max != null && (
                  <div style={{ fontSize: 13, color: '#059669', fontWeight: 600, marginBottom: 4 }}>
                    {INR(rule.recovery_min)} – {INR(rule.recovery_max)}
                  </div>
                )}
                {rule.playbook_notes && (
                  <div style={{ fontSize: 13, color: '#374151' }}>{rule.playbook_notes}</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Rules() {
  var [rules, setRules] = useState([])
  var [loading, setLoading] = useState(true)
  var [error, setError] = useState(null)
  var [expanded, setExpanded] = useState(null)
  var [modal, setModal] = useState(null)  // null | {mode:'create'} | {mode:'edit', rule}
  var [saving, setSaving] = useState(false)
  var [toast, setToast] = useState(null)

  var [filterCat, setFilterCat] = useState('')
  var [filterSev, setFilterSev] = useState('')
  var [filterVerdict, setFilterVerdict] = useState('')
  var [filterAuto, setFilterAuto] = useState('')

  var showToast = useCallback(function(msg, type) {
    setToast({ msg, type })
    setTimeout(function() { setToast(null) }, 3000)
  }, [])

  var load = useCallback(async function() {
    try {
      setLoading(true)
      var params = new URLSearchParams()
      if (filterCat)     params.set('category', filterCat)
      if (filterSev)     params.set('severity', filterSev)
      if (filterVerdict) params.set('verdict', filterVerdict)
      var qs = params.toString()
      var res = await api.get('/dispute-engine/rules' + (qs ? '?' + qs : ''))
      var items = res.data.items || res.data || []
      if (filterAuto === 'yes') items = items.filter(function(r) { return r.auto_raise || r.auto })
      if (filterAuto === 'no')  items = items.filter(function(r) { return !(r.auto_raise || r.auto) })
      setRules(items)
      setError(null)
    } catch (e) {
      setError('Failed to load rules')
    } finally {
      setLoading(false)
    }
  }, [filterCat, filterSev, filterVerdict, filterAuto])

  useEffect(function() { load() }, [load])

  async function handleToggle(rule) {
    if (!rule.id || typeof rule.id !== 'string' || rule.id.length < 30) {
      showToast('Toggle not available for mock rules', 'info')
      return
    }
    try {
      await api.patch('/rules/' + rule.id + '/toggle')
      setRules(function(prev) {
        return prev.map(function(r) { return r.id === rule.id ? { ...r, is_enabled: !r.is_enabled } : r })
      })
    } catch (e) {
      showToast('Toggle failed: ' + (e.response?.data?.detail || e.message), 'error')
    }
  }

  async function handleSave(payload) {
    setSaving(true)
    try {
      var isEdit = modal.mode === 'edit' && modal.rule
      var ruleId = isEdit ? modal.rule.id : null
      if (isEdit && ruleId && ruleId.length > 30) {
        await api.patch('/rules/' + ruleId, payload)
        showToast('Rule updated', 'success')
      } else {
        await api.post('/rules/', payload)
        showToast('Rule created', 'success')
      }
      setModal(null)
      await load()
    } catch (e) {
      var detail = e.response?.data?.detail
      var msg = typeof detail === 'string' ? detail : JSON.stringify(detail) || e.message
      showToast('Save failed: ' + msg, 'error')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(rule) {
    if (!rule.id || rule.id.length < 30) {
      showToast('Cannot delete global or mock rules', 'error'); return
    }
    if (!window.confirm('Delete rule "' + rule.name + '"? This cannot be undone.')) return
    try {
      await api.delete('/rules/' + rule.id)
      showToast('Rule deleted', 'success')
      await load()
    } catch (e) {
      showToast('Delete failed: ' + (e.response?.data?.detail || e.message), 'error')
    }
  }

  var autoCount = rules.filter(function(r) { return r.auto_raise || r.auto }).length
  var enabledCount = rules.filter(function(r) { return r.is_enabled !== false }).length

  var selStyle = { padding: '7px 10px', border: '1px solid #E2E8F0', borderRadius: 8, fontSize: 13, background: '#fff', color: '#374151' }

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 2000,
          padding: '12px 20px', borderRadius: 10, fontWeight: 600, fontSize: 14,
          background: toast.type === 'error' ? '#FEE2E2' : toast.type === 'success' ? '#DCFCE7' : '#EFF6FF',
          color: toast.type === 'error' ? '#B91C1C' : toast.type === 'success' ? '#166534' : '#2563EB',
          boxShadow: '0 4px 16px rgba(0,0,0,.12)',
        }}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#0F172A' }}>Dispute Rules Engine</h1>
          <p style={{ margin: '4px 0 0', color: '#64748B', fontSize: 14 }}>
            {rules.length} rules · {enabledCount} active · {autoCount} auto-raise
          </p>
        </div>
        <button onClick={function() { setModal({ mode: 'create' }) }}
          style={{ padding: '10px 20px', background: '#2563EB', color: '#fff', border: 'none', borderRadius: 10, cursor: 'pointer', fontSize: 14, fontWeight: 700 }}>
          + New Rule
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Total Rules', value: rules.length, color: '#2563EB' },
          { label: 'Auto-Raise', value: autoCount, color: '#059669' },
          { label: 'Active', value: enabledCount, color: '#0DB07A' },
          { label: 'Paused', value: rules.length - enabledCount, color: '#E9930D' },
        ].map(function(s) {
          return (
            <div key={s.label} style={{ background: '#fff', borderRadius: 12, border: '1px solid #E2E8F0', padding: '14px 16px' }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 12, color: '#64748B', fontWeight: 600 }}>{s.label}</div>
            </div>
          )
        })}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        <select value={filterCat} onChange={function(e) { setFilterCat(e.target.value) }} style={selStyle}>
          <option value="">All Categories</option>
          {CATEGORIES.map(function(c) { return <option key={c} value={c}>{c}</option> })}
        </select>
        <select value={filterSev} onChange={function(e) { setFilterSev(e.target.value) }} style={selStyle}>
          <option value="">All Severities</option>
          {SEVERITIES.map(function(s) { return <option key={s} value={s}>{s}</option> })}
        </select>
        <select value={filterVerdict} onChange={function(e) { setFilterVerdict(e.target.value) }} style={selStyle}>
          <option value="">All Verdicts</option>
          {VERDICTS.map(function(v) { return <option key={v} value={v}>{v}</option> })}
        </select>
        <select value={filterAuto} onChange={function(e) { setFilterAuto(e.target.value) }} style={selStyle}>
          <option value="">All Rules</option>
          <option value="yes">Auto-Raise Only</option>
          <option value="no">Manual Only</option>
        </select>
        {(filterCat || filterSev || filterVerdict || filterAuto) && (
          <button onClick={function() { setFilterCat(''); setFilterSev(''); setFilterVerdict(''); setFilterAuto('') }}
            style={{ padding: '7px 14px', background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FECACA', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>
            Clear
          </button>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#94A3B8' }}>Loading rules…</div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#E8344A' }}>{error}</div>
      ) : rules.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#94A3B8' }}>No rules match your filters.</div>
      ) : (
        rules.map(function(rule) {
          return (
            <RuleCard
              key={rule.id}
              rule={rule}
              expanded={expanded === rule.id}
              onExpand={setExpanded}
              onToggle={handleToggle}
              onEdit={function(r) { setModal({ mode: 'edit', rule: r }) }}
              onDelete={handleDelete}
            />
          )
        })
      )}

      {modal && (
        <Modal
          rule={modal.mode === 'edit' ? modal.rule : null}
          onClose={function() { setModal(null) }}
          onSave={handleSave}
          saving={saving}
        />
      )}
    </div>
  )
}
