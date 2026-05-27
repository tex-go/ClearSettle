import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import useAuthStore from '../store/authStore'

// ── colours ───────────────────────────────────────────────────────────────────
const C = {
  teal: '#0ABFCA', dark: '#0D1F35', mid: '#4B6080', light: '#8FA5BD',
  red: '#E8344A', amber: '#E9930D', green: '#10B981', purple: '#8B5CF6',
  bg: '#F1F5F9', white: '#fff', border: '#E8EFF6', rowBg: '#F7FAFC',
}
const PIE_COLORS = ['#0ABFCA','#E9930D','#10B981','#8B5CF6','#E8344A','#3B82F6']

const PRIORITY_STYLE = {
  hot:     { background: 'rgba(232,52,74,.15)',   color: '#E8344A', label: '🔥 Hot' },
  warm:    { background: 'rgba(233,147,13,.15)',  color: '#E9930D', label: '🌤 Warm' },
  cold:    { background: 'rgba(10,191,202,.15)',  color: '#0ABFCA', label: '❄️ Cold' },
  skip:    { background: 'rgba(75,96,128,.15)',   color: '#8FA5BD', label: 'Skip' },
  unscored:{ background: 'rgba(75,96,128,.1)',    color: '#8FA5BD', label: '— Unscored' },
}
const STATUS_STYLE = {
  new:           { background: 'rgba(10,191,202,.12)',  color: '#0ABFCA', label: 'New' },
  review_pending:{ background: 'rgba(233,147,13,.12)',  color: '#E9930D', label: 'Review Pending' },
  reviewing:     { background: 'rgba(233,147,13,.12)',  color: '#E9930D', label: 'Reviewing' },
  approved:      { background: 'rgba(16,185,129,.12)',  color: '#10B981', label: 'Approved' },
  qualified:     { background: 'rgba(16,185,129,.12)',  color: '#10B981', label: 'Qualified' },
  rejected:      { background: 'rgba(232,52,74,.12)',   color: '#E8344A', label: 'Rejected' },
  contact_ready: { background: 'rgba(139,92,246,.12)',  color: '#8B5CF6', label: 'Contact Ready' },
  contacted:     { background: 'rgba(16,185,129,.12)',  color: '#10B981', label: 'Contacted' },
  deleted:       { background: 'rgba(75,96,128,.12)',   color: '#8FA5BD', label: 'Deleted' },
}
const JOB_STATUS_STYLE = {
  queued:    { background: 'rgba(10,191,202,.15)',  color: '#0ABFCA', label: 'Queued' },
  running:   { background: 'rgba(233,147,13,.15)',  color: '#E9930D', label: 'Running' },
  completed: { background: 'rgba(16,185,129,.15)',  color: '#10B981', label: 'Completed' },
  failed:    { background: 'rgba(232,52,74,.15)',   color: '#E8344A', label: 'Failed' },
  cancelled: { background: 'rgba(75,96,128,.15)',   color: '#8FA5BD', label: 'Cancelled' },
}

// ── API helper ─────────────────────────────────────────────────────────────────
function api(token, path, opts = {}) {
  return fetch(`/api${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(opts.headers || {}),
    },
  }).then(r => {
    if (!r.ok) return r.json().then(e => Promise.reject(e.detail || 'Request failed'))
    return r.json()
  })
}

// ── Mini components ───────────────────────────────────────────────────────────
function Spinner({ size = 20 }) {
  return (
    <div style={{
      width: size, height: size,
      border: `${size / 7}px solid rgba(10,191,202,.2)`,
      borderTop: `${size / 7}px solid #0ABFCA`,
      borderRadius: '50%', animation: 'spin 1s linear infinite',
    }} />
  )
}

function StatCard({ label, value, sub, color = C.teal, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: C.white, borderRadius: 12, padding: '18px 22px',
      border: `1px solid ${C.border}`, flex: 1, minWidth: 140,
      cursor: onClick ? 'pointer' : 'default',
    }}>
      <div style={{ fontSize: 11, color: C.light, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 800, color }}>{value ?? '—'}</div>
      {sub && <div style={{ fontSize: 11, color: C.light, marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function Badge({ label, styleMap, value }) {
  const entry = styleMap[value] || styleMap.unscored || { background: '#eee', color: '#888', label: value }
  const { label: entryLabel, ...style } = entry
  return (
    <span style={{ ...style, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap' }}>
      {label || entryLabel || value}
    </span>
  )
}

function ScoreBar({ score }) {
  if (score == null) return <span style={{ color: C.light, fontSize: 12 }}>—</span>
  const color = score >= 70 ? C.red : score >= 40 ? C.amber : score >= 20 ? C.teal : C.light
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 48, height: 6, background: '#E8EFF6', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: 3, transition: 'width .4s' }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color }}>{score.toFixed(0)}</span>
    </div>
  )
}

function EmptyState({ icon, title, sub }) {
  return (
    <div style={{ background: C.white, borderRadius: 14, padding: '60px 20px', textAlign: 'center', border: `1px solid ${C.border}` }}>
      <div style={{ fontSize: 48, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 15, fontWeight: 700, color: C.dark }}>{title}</div>
      {sub && <div style={{ fontSize: 13, color: C.light, marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

const inputStyle = {
  padding: '8px 12px', borderRadius: 8, border: `1px solid ${C.border}`,
  fontSize: 13, color: C.dark, background: C.rowBg, outline: 'none',
}

// ── Activity type config ──────────────────────────────────────────────────────
const ACT_TYPES = [
  { value: 'note',         label: '📝 Note',       placeholder: 'Add a note…' },
  { value: 'follow_up',    label: '📅 Follow-up',  placeholder: 'Follow-up details…' },
  { value: 'call_log',     label: '📞 Call',        placeholder: 'Call summary…' },
  { value: 'email_log',    label: '✉️ Email',       placeholder: 'Email summary…' },
  { value: 'whatsapp_log', label: '💬 WhatsApp',   placeholder: 'Message summary…' },
  { value: 'tag',          label: '🏷️ Tag',         placeholder: 'Tag name…' },
]
const ACT_BG = {
  note: 'rgba(10,191,202,.15)', follow_up: 'rgba(233,147,13,.15)',
  call_log: 'rgba(16,185,129,.15)', email_log: 'rgba(139,92,246,.15)',
  whatsapp_log: 'rgba(16,185,129,.2)', tag: 'rgba(10,191,202,.1)',
  status_change: 'rgba(75,96,128,.15)', classify: 'rgba(10,191,202,.12)',
  score: 'rgba(139,92,246,.12)', outreach: 'rgba(139,92,246,.15)',
}

// ── Lead Detail Panel ─────────────────────────────────────────────────────────
function LeadDetail({ lead: initLead, token, onClose, onUpdate }) {
  const [lead, setLead]         = useState(initLead)
  const [section, setSection]   = useState('overview')  // overview | activity
  const [acting, setActing]     = useState(null)
  const [classifying, setClassifying] = useState(false)
  const [scoring, setScoring]   = useState(false)
  const [error, setError]       = useState(null)

  // CRM properties
  const [assignedTo, setAssignedTo] = useState(initLead.assigned_to || '')
  const [followUpAt, setFollowUpAt] = useState(initLead.follow_up_at ? initLead.follow_up_at.slice(0, 10) : '')
  const [savingProp, setSavingProp] = useState(null)

  // Tags
  const [userTags, setUserTags] = useState(() => { try { return JSON.parse(initLead.tags_json || '[]') } catch { return [] } })
  const [newTag, setNewTag]     = useState('')

  // Activity
  const [activities, setActivities]   = useState([])
  const [loadingAct, setLoadingAct]   = useState(true)
  const [actType, setActType]         = useState('note')
  const [actContent, setActContent]   = useState('')
  const [actFuDate, setActFuDate]     = useState('')
  const [addingAct, setAddingAct]     = useState(false)
  const [actError, setActError]       = useState(null)

  // load activity once
  useEffect(() => {
    api(token, `/seller-discovery/leads/${lead.id}/activity`)
      .then(setActivities).catch(() => {}).finally(() => setLoadingAct(false))
  }, [lead.id, token])

  function sync(updated) { setLead(updated); onUpdate(updated) }

  async function doAction(action) {
    setActing(action); setError(null)
    try {
      const updated = await api(token, `/seller-discovery/leads/${lead.id}/review`, { method: 'POST', body: JSON.stringify({ action }) })
      sync(updated)
      // reload activity to show auto-logged status_change
      api(token, `/seller-discovery/leads/${lead.id}/activity`).then(setActivities).catch(() => {})
    } catch (e) { setError(String(e)) }
    finally { setActing(null) }
  }

  async function doClassify() {
    setClassifying(true); setError(null)
    try {
      const updated = await api(token, `/seller-discovery/leads/${lead.id}/classify`, { method: 'POST' })
      sync(updated)
      api(token, `/seller-discovery/leads/${lead.id}/activity`).then(setActivities).catch(() => {})
    } catch (e) { setError(String(e)) }
    finally { setClassifying(false) }
  }

  async function doScore() {
    setScoring(true); setError(null)
    try {
      const updated = await api(token, `/seller-discovery/leads/${lead.id}/score`, { method: 'POST' })
      sync(updated)
      api(token, `/seller-discovery/leads/${lead.id}/activity`).then(setActivities).catch(() => {})
    } catch (e) { setError(String(e)) }
    finally { setScoring(false) }
  }

  async function saveProp(field, value) {
    setSavingProp(field)
    try {
      const updated = await api(token, `/seller-discovery/leads/${lead.id}`, { method: 'PATCH', body: JSON.stringify({ [field]: value || null }) })
      sync(updated)
    } catch (e) { setError(String(e)) }
    finally { setSavingProp(null) }
  }

  async function addTag() {
    const tag = newTag.trim()
    if (!tag) return
    const next = [...userTags, tag]
    try {
      const updated = await api(token, `/seller-discovery/leads/${lead.id}`, { method: 'PATCH', body: JSON.stringify({ tags_json: JSON.stringify(next) }) })
      sync(updated); setUserTags(next); setNewTag('')
      const act = await api(token, `/seller-discovery/leads/${lead.id}/activity`, { method: 'POST', body: JSON.stringify({ activity_type: 'tag', content: `Tag added: ${tag}` }) })
      setActivities(prev => [act, ...prev])
    } catch (e) { setError(String(e)) }
  }

  async function removeTag(tag) {
    const next = userTags.filter(t => t !== tag)
    try {
      const updated = await api(token, `/seller-discovery/leads/${lead.id}`, { method: 'PATCH', body: JSON.stringify({ tags_json: JSON.stringify(next) }) })
      sync(updated); setUserTags(next)
      const act = await api(token, `/seller-discovery/leads/${lead.id}/activity`, { method: 'POST', body: JSON.stringify({ activity_type: 'tag', content: `Tag removed: ${tag}` }) })
      setActivities(prev => [act, ...prev])
    } catch (e) { setError(String(e)) }
  }

  async function submitActivity(e) {
    e.preventDefault()
    const isFollowUp = actType === 'follow_up'
    if (!actContent.trim() && !isFollowUp) return
    if (isFollowUp && !actFuDate) { setActError('Choose a follow-up date'); return }
    setAddingAct(true); setActError(null)
    try {
      const body = { activity_type: actType, content: actContent || undefined }
      if (isFollowUp) body.follow_up_at = new Date(actFuDate).toISOString()
      const act = await api(token, `/seller-discovery/leads/${lead.id}/activity`, { method: 'POST', body: JSON.stringify(body) })
      setActivities(prev => [act, ...prev])
      setActContent(''); setActFuDate('')
      if (isFollowUp) {
        setFollowUpAt(actFuDate)
        setLead(prev => ({ ...prev, follow_up_at: actFuDate }))
      }
    } catch (e) { setActError(String(e)) }
    finally { setAddingAct(false) }
  }

  const aiTags = (() => { try { return JSON.parse(lead.ai_tags_json || '[]') } catch { return [] } })()
  const actTypeCfg = ACT_TYPES.find(t => t.value === actType) || ACT_TYPES[0]

  const SectionLabel = ({ label }) => (
    <div style={{ fontSize: 10, fontWeight: 700, color: C.light, textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 8 }}>{label}</div>
  )

  return (
    <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 520, background: C.white, boxShadow: '-8px 0 40px rgba(0,0,0,.15)', zIndex: 1000, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

      {/* ── Header ── */}
      <div style={{ padding: '14px 18px', borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          {lead.profile_image_url
            ? <img src={lead.profile_image_url} alt="" style={{ width: 42, height: 42, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} onError={e => e.target.style.display='none'} />
            : <div style={{ width: 42, height: 42, borderRadius: '50%', background: 'rgba(10,191,202,.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17, color: C.teal, flexShrink: 0 }}>{lead.username[0]?.toUpperCase()}</div>
          }
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: C.dark }}>@{lead.username}</div>
            <div style={{ fontSize: 11, color: C.light, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {lead.source} · {lead.full_name || 'Unknown'}{lead.country ? ` · ${lead.country}` : ''}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 18, color: C.light, cursor: 'pointer', padding: 4 }}>✕</button>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <ScoreBar score={lead.lead_score} />
          <Badge value={lead.priority_level || 'unscored'} styleMap={PRIORITY_STYLE} />
          <Badge value={lead.lead_status} styleMap={STATUS_STYLE} />
          {lead.follow_up_at && <span style={{ fontSize: 11, color: C.amber, fontWeight: 600, background: 'rgba(233,147,13,.1)', borderRadius: 6, padding: '2px 8px' }}>📅 {new Date(lead.follow_up_at).toLocaleDateString('en-IN')}</span>}
          {lead.assigned_to && <span style={{ fontSize: 11, color: C.purple, fontWeight: 600, background: 'rgba(139,92,246,.1)', borderRadius: 6, padding: '2px 8px' }}>👤 {lead.assigned_to}</span>}
        </div>
      </div>

      {/* ── Sub-tabs ── */}
      <div style={{ display: 'flex', background: C.rowBg, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        {[['overview', '📋 Overview'], ['activity', `🕐 Activity${activities.length ? ` (${activities.length})` : ''}`]].map(([id, label]) => (
          <button key={id} onClick={() => setSection(id)} style={{ flex: 1, padding: '9px 0', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 700, background: section === id ? C.white : 'transparent', color: section === id ? C.teal : C.mid, borderBottom: section === id ? `2px solid ${C.teal}` : '2px solid transparent' }}>
            {label}
          </button>
        ))}
      </div>

      {/* ── Scrollable body ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 18px' }}>

        {section === 'overview' ? (
          <>
            {/* Profile stats */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 14 }}>
              {[
                ['Followers', lead.followers_count?.toLocaleString('en-IN')],
                ['Following', lead.following_count?.toLocaleString('en-IN')],
                ['Engagement', lead.engagement_rate != null ? `${(lead.engagement_rate * 100).toFixed(2)}%` : null],
              ].map(([label, val]) => val != null && (
                <div key={label} style={{ background: C.rowBg, borderRadius: 8, padding: '8px 10px', textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: C.light, textTransform: 'uppercase', fontWeight: 600, marginBottom: 2 }}>{label}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: C.dark }}>{val}</div>
                </div>
              ))}
            </div>

            {/* Bio */}
            {lead.bio && <div style={{ marginBottom: 12, background: C.rowBg, borderRadius: 8, padding: '8px 10px' }}><SectionLabel label="Bio" /><div style={{ fontSize: 13, color: C.dark, lineHeight: 1.5 }}>{lead.bio}</div></div>}

            {/* Contact */}
            {(lead.website || lead.email || lead.whatsapp) && (
              <div style={{ marginBottom: 14 }}>
                <SectionLabel label="Contact" />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {lead.website && <a href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: C.teal, textDecoration: 'none' }}>🌐 {lead.website}</a>}
                  {lead.email    && <span style={{ fontSize: 13, color: C.dark }}>✉️ {lead.email}</span>}
                  {lead.whatsapp && <span style={{ fontSize: 13, color: C.dark }}>💬 {lead.whatsapp}</span>}
                </div>
              </div>
            )}

            {/* JIRA-style properties */}
            <div style={{ marginBottom: 14, border: `1px solid ${C.border}`, borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ padding: '7px 12px', background: C.rowBg, borderBottom: `1px solid ${C.border}`, fontSize: 10, fontWeight: 700, color: C.mid, textTransform: 'uppercase', letterSpacing: '.05em' }}>Properties</div>
              <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Assigned To */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 12, color: C.mid, minWidth: 88 }}>Assigned To</span>
                  <input value={assignedTo} onChange={e => setAssignedTo(e.target.value)}
                    onBlur={() => saveProp('assigned_to', assignedTo)}
                    placeholder="e.g. ranjith" style={{ ...inputStyle, flex: 1, padding: '5px 9px', fontSize: 12 }} />
                  {savingProp === 'assigned_to' && <Spinner size={14} />}
                </div>
                {/* Follow-up date */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 12, color: C.mid, minWidth: 88 }}>Follow-up</span>
                  <input type="date" value={followUpAt} onChange={e => setFollowUpAt(e.target.value)}
                    onBlur={async () => {
                      if (followUpAt) {
                        await saveProp('follow_up_at', new Date(followUpAt + 'T00:00:00').toISOString())
                        const act = await api(token, `/seller-discovery/leads/${lead.id}/activity`, { method: 'POST', body: JSON.stringify({ activity_type: 'follow_up', content: `Follow-up scheduled for ${followUpAt}`, follow_up_at: new Date(followUpAt + 'T00:00:00').toISOString() }) }).catch(() => null)
                        if (act) setActivities(prev => [act, ...prev])
                      }
                    }}
                    style={{ ...inputStyle, flex: 1, padding: '5px 9px', fontSize: 12 }} />
                  {savingProp === 'follow_up_at' && <Spinner size={14} />}
                </div>
                {/* Outreach status */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 12, color: C.mid, minWidth: 88 }}>Outreach</span>
                  <select value={lead.outreach_status || 'pending'}
                    onChange={async e => {
                      try {
                        const updated = await api(token, `/seller-discovery/leads/${lead.id}/outreach`, { method: 'PATCH', body: JSON.stringify({ outreach_status: e.target.value }) })
                        sync(updated)
                        api(token, `/seller-discovery/leads/${lead.id}/activity`).then(setActivities).catch(() => {})
                      } catch (err) { setError(String(err)) }
                    }}
                    style={{ ...inputStyle, flex: 1, padding: '5px 9px', fontSize: 12 }}>
                    <option value="pending">⏳ Pending</option>
                    <option value="ready">✅ Ready</option>
                    <option value="contacted">📤 Contacted</option>
                    <option value="skipped">⏭️ Skipped</option>
                  </select>
                </div>
                {/* Tags */}
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ fontSize: 12, color: C.mid, minWidth: 88, paddingTop: 4 }}>Tags</span>
                  <div style={{ flex: 1 }}>
                    {userTags.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 6 }}>
                        {userTags.map((t, i) => (
                          <span key={i} style={{ background: 'rgba(10,191,202,.1)', color: C.teal, borderRadius: 6, padding: '2px 8px', fontSize: 11, display: 'flex', alignItems: 'center', gap: 3 }}>
                            {t}
                            <button onClick={() => removeTag(t)} style={{ background: 'none', border: 'none', color: C.light, cursor: 'pointer', padding: 0, fontSize: 12, lineHeight: 1 }}>×</button>
                          </span>
                        ))}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 5 }}>
                      <input value={newTag} onChange={e => setNewTag(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())}
                        placeholder="Add tag…" style={{ ...inputStyle, flex: 1, padding: '4px 8px', fontSize: 12 }} />
                      <button onClick={addTag} disabled={!newTag.trim()} style={{ padding: '4px 10px', borderRadius: 7, background: 'rgba(10,191,202,.12)', color: C.teal, border: 'none', fontSize: 12, cursor: 'pointer' }}>+ Add</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Classification */}
            {lead.ai_classified_at && (
              <div style={{ marginBottom: 14, background: 'rgba(10,191,202,.06)', borderRadius: 10, padding: '10px 12px', border: `1px solid rgba(10,191,202,.15)` }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: C.teal, textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 8 }}>AI Classification · {new Date(lead.ai_classified_at).toLocaleDateString('en-IN')}</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: aiTags.length || lead.ai_outreach_suggestion ? 8 : 0 }}>
                  {[
                    ['eCommerce', lead.ai_is_ecommerce ? '✓ Yes' : '✗ No'],
                    ['India Seller', lead.ai_is_india_seller ? '✓ Yes' : '✗ No'],
                    ['Category', lead.ai_category],
                    ['Biz Type', lead.ai_estimated_biz_type],
                    ['Revenue Stage', lead.ai_revenue_stage],
                    ['Relevance', lead.ai_relevance_score != null ? `${(lead.ai_relevance_score * 100).toFixed(0)}%` : null],
                    ['Confidence', lead.ai_confidence_score != null ? `${(lead.ai_confidence_score * 100).toFixed(0)}%` : null],
                    ['Fake', lead.ai_is_fake_account ? '⚠️ Suspicious' : null],
                  ].filter(([, v]) => v != null).map(([label, val]) => (
                    <div key={label}><div style={{ fontSize: 10, color: C.light }}>{label}</div><div style={{ fontSize: 12, fontWeight: 600, color: C.dark }}>{val}</div></div>
                  ))}
                </div>
                {aiTags.length > 0 && <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: lead.ai_outreach_suggestion ? 8 : 0 }}>{aiTags.map((t, i) => <span key={i} style={{ background: 'rgba(10,191,202,.12)', color: C.teal, borderRadius: 6, padding: '1px 7px', fontSize: 11 }}>{t}</span>)}</div>}
                {lead.ai_outreach_suggestion && <div style={{ fontSize: 12, color: C.mid, fontStyle: 'italic', lineHeight: 1.5, borderTop: `1px solid rgba(10,191,202,.15)`, paddingTop: 8 }}>💬 {lead.ai_outreach_suggestion}</div>}
              </div>
            )}

            {/* Actions */}
            <div style={{ marginBottom: 14 }}>
              <SectionLabel label="Actions" />
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <button onClick={doClassify} disabled={classifying} style={{ padding: '6px 12px', borderRadius: 7, background: 'rgba(10,191,202,.12)', color: C.teal, border: `1px solid rgba(10,191,202,.25)`, fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                  {classifying ? <Spinner size={13} /> : '🤖'} Classify
                </button>
                <button onClick={doScore} disabled={scoring} style={{ padding: '6px 12px', borderRadius: 7, background: 'rgba(139,92,246,.12)', color: C.purple, border: `1px solid rgba(139,92,246,.25)`, fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                  {scoring ? <Spinner size={13} /> : '⭐'} Score
                </button>
                {['new','review_pending','reviewing'].includes(lead.lead_status) && <>
                  <button onClick={() => doAction('approve')} disabled={!!acting} style={{ padding: '6px 12px', borderRadius: 7, background: 'rgba(16,185,129,.12)', color: C.green, border: `1px solid rgba(16,185,129,.25)`, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                    {acting === 'approve' ? <Spinner size={13} /> : '✓ Approve'}
                  </button>
                  <button onClick={() => doAction('reject')} disabled={!!acting} style={{ padding: '6px 12px', borderRadius: 7, background: 'rgba(232,52,74,.1)', color: C.red, border: `1px solid rgba(232,52,74,.2)`, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                    {acting === 'reject' ? <Spinner size={13} /> : '✕ Reject'}
                  </button>
                </>}
                {['approved','reviewing','review_pending'].includes(lead.lead_status) && (
                  <button onClick={() => doAction('qualify')} disabled={!!acting} style={{ padding: '6px 12px', borderRadius: 7, background: 'rgba(16,185,129,.15)', color: C.green, border: `1px solid rgba(16,185,129,.3)`, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                    {acting === 'qualify' ? <Spinner size={13} /> : '🎯 Qualify'}
                  </button>
                )}
                {['qualified','approved'].includes(lead.lead_status) && (
                  <button onClick={() => doAction('contact_ready')} disabled={!!acting} style={{ padding: '6px 12px', borderRadius: 7, background: 'rgba(139,92,246,.12)', color: C.purple, border: `1px solid rgba(139,92,246,.25)`, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                    {acting === 'contact_ready' ? <Spinner size={13} /> : '📤 Contact Ready'}
                  </button>
                )}
              </div>
              {error && <div style={{ fontSize: 12, color: C.red, marginTop: 6 }}>{error}</div>}
            </div>

            {/* Meta */}
            <div style={{ fontSize: 11, color: C.light, borderTop: `1px solid ${C.border}`, paddingTop: 10 }}>
              Created {new Date(lead.created_at).toLocaleDateString('en-IN')}
              {lead.reviewed_by && ` · Reviewed by ${lead.reviewed_by}`}
              {lead.discovery_keyword && ` · via ${lead.discovery_keyword}`}
            </div>
          </>
        ) : (
          /* ── Activity tab ── */
          <>
            {/* Add activity form */}
            <form onSubmit={submitActivity} style={{ marginBottom: 18, background: C.rowBg, borderRadius: 10, border: `1px solid ${C.border}`, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: C.dark, marginBottom: 8 }}>Log Activity</div>
              {/* Type pills */}
              <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 8 }}>
                {ACT_TYPES.map(t => (
                  <button key={t.value} type="button" onClick={() => setActType(t.value)}
                    style={{ padding: '3px 10px', borderRadius: 6, border: actType === t.value ? `2px solid ${C.teal}` : `1px solid ${C.border}`, background: actType === t.value ? 'rgba(10,191,202,.1)' : C.white, color: actType === t.value ? C.teal : C.mid, fontSize: 11, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                    {t.label}
                  </button>
                ))}
              </div>
              {/* Follow-up date input */}
              {actType === 'follow_up' && (
                <input type="date" value={actFuDate} onChange={e => setActFuDate(e.target.value)} required
                  style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', marginBottom: 8, fontSize: 12 }} />
              )}
              <textarea value={actContent} onChange={e => setActContent(e.target.value)}
                placeholder={actTypeCfg.placeholder} rows={3}
                style={{ ...inputStyle, width: '100%', resize: 'vertical', boxSizing: 'border-box', fontSize: 12, marginBottom: 8 }} />
              {actError && <div style={{ fontSize: 11, color: C.red, marginBottom: 6 }}>{actError}</div>}
              <button type="submit" disabled={addingAct || (actType !== 'follow_up' && !actContent.trim())}
                style={{ padding: '7px 16px', borderRadius: 8, background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', border: 'none', fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                {addingAct ? <><Spinner size={13} /> Saving…</> : '+ Log'}
              </button>
            </form>

            {/* Timeline */}
            {loadingAct ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner size={28} /></div>
            ) : activities.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: C.light, fontSize: 13 }}>No activity yet. Log a note, call, or follow-up to get started.</div>
            ) : (
              <div>
                {activities.map((act, i) => (
                  <div key={act.id} style={{ display: 'flex', gap: 10, paddingBottom: 16 }}>
                    {/* Node + line */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                      <div style={{ width: 30, height: 30, borderRadius: '50%', background: ACT_BG[act.activity_type] || 'rgba(75,96,128,.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>{act.icon}</div>
                      {i < activities.length - 1 && <div style={{ width: 2, flex: 1, background: C.border, marginTop: 4, minHeight: 14 }} />}
                    </div>
                    {/* Content */}
                    <div style={{ flex: 1, paddingTop: 4, minWidth: 0 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 3, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: C.dark, textTransform: 'capitalize' }}>{act.activity_type.replace('_', ' ')}</span>
                        {act.metadata_json?.old_status && (
                          <span style={{ fontSize: 11, color: C.light }}>{act.metadata_json.old_status} → {act.metadata_json.new_status}</span>
                        )}
                        {act.metadata_json?.follow_up_at && (
                          <span style={{ fontSize: 11, color: C.amber, fontWeight: 600 }}>📅 {new Date(act.metadata_json.follow_up_at).toLocaleDateString('en-IN')}</span>
                        )}
                        {act.metadata_json?.lead_score != null && (
                          <span style={{ fontSize: 11, color: C.purple, fontWeight: 600 }}>Score: {act.metadata_json.lead_score?.toFixed(0)}</span>
                        )}
                      </div>
                      {act.content && (
                        <div style={{ fontSize: 13, color: C.dark, lineHeight: 1.5, background: C.rowBg, borderRadius: 8, padding: '7px 10px', marginBottom: 4, wordBreak: 'break-word' }}>{act.content}</div>
                      )}
                      <div style={{ fontSize: 11, color: C.light }}>
                        {act.created_by} · {new Date(act.created_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Leads Tab ─────────────────────────────────────────────────────────────────
function LeadsTab({ token, jobFilter, onClearJobFilter }) {
  const [leads, setLeads]             = useState([])
  const [total, setTotal]             = useState(0)
  const [page, setPage]               = useState(1)
  const [loading, setLoading]         = useState(true)
  const [search, setSearch]           = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [source, setSource]           = useState('')
  const [status, setStatus_]          = useState('')
  const [priority, setPriority]       = useState('')
  const [selectedLead, setSelectedLead] = useState(null)
  // manual add
  const [addOpen, setAddOpen]         = useState(false)
  const [addForm, setAddForm]         = useState({ username: '', source: 'instagram' })
  const [addErr, setAddErr]           = useState(null)
  const [adding, setAdding]           = useState(false)

  const PAGE_SIZE = 20

  // reset page when job filter changes
  useEffect(() => { setPage(1) }, [jobFilter])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page, page_size: PAGE_SIZE })
      if (search)              params.set('search', search)
      if (source)              params.set('source', source)
      if (status)              params.set('lead_status', status)
      if (priority)            params.set('priority_level', priority)
      if (jobFilter?.jobId)    params.set('job_id', jobFilter.jobId)
      const data = await api(token, `/seller-discovery/leads?${params}`)
      setLeads(data.items || [])
      setTotal(data.total || 0)
    } catch { setLeads([]) }
    finally { setLoading(false) }
  }, [token, page, search, source, status, priority, jobFilter])

  useEffect(() => { load() }, [load])

  function handleSearch(e) {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  function handleLeadUpdate(updated) {
    setLeads(prev => prev.map(l => l.id === updated.id ? updated : l))
    setSelectedLead(updated)
  }

  async function submitAddLead(e) {
    e.preventDefault()
    if (!addForm.username.trim()) { setAddErr('Username is required'); return }
    setAdding(true); setAddErr(null)
    try {
      const lead = await api(token, '/seller-discovery/leads', {
        method: 'POST',
        body: JSON.stringify({ username: addForm.username.trim().replace(/^@/, ''), source: addForm.source }),
      })
      setLeads(prev => [lead, ...prev])
      setTotal(t => t + 1)
      setAddForm({ username: '', source: 'instagram' })
      setAddOpen(false)
      setSelectedLead(lead)
    } catch (e) { setAddErr(String(e)) }
    finally { setAdding(false) }
  }

  const pages = Math.ceil(total / PAGE_SIZE)

  return (
    <div>
      {/* Job filter banner */}
      {jobFilter && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, background: 'rgba(10,191,202,.08)', border: `1px solid rgba(10,191,202,.2)`, borderRadius: 10, padding: '10px 16px' }}>
          <span style={{ fontSize: 13, color: C.teal, fontWeight: 600 }}>
            Showing leads from job: <strong>{jobFilter.keyword}</strong>
          </span>
          <button onClick={() => { onClearJobFilter(); setPage(1) }} style={{ marginLeft: 'auto', padding: '3px 10px', borderRadius: 6, background: 'rgba(10,191,202,.15)', color: C.teal, border: 'none', fontSize: 12, cursor: 'pointer', fontWeight: 600 }}>
            ✕ Clear filter
          </button>
        </div>
      )}

      {/* Add Lead inline form */}
      {addOpen && (
        <form onSubmit={submitAddLead} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 14, background: C.white, border: `1px solid ${C.border}`, borderRadius: 10, padding: '14px 16px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: C.mid, display: 'block', marginBottom: 4 }}>Instagram username</label>
            <input autoFocus value={addForm.username} onChange={e => setAddForm(f => ({ ...f, username: e.target.value }))} placeholder="e.g. ranju_dood" style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }} />
          </div>
          <div style={{ minWidth: 130 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: C.mid, display: 'block', marginBottom: 4 }}>Source</label>
            <select value={addForm.source} onChange={e => setAddForm(f => ({ ...f, source: e.target.value }))} style={{ ...inputStyle }}>
              <option value="instagram">Instagram</option>
              <option value="manual">Manual</option>
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 4 }}>
            <label style={{ fontSize: 11, color: 'transparent' }}>x</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <button type="submit" disabled={adding} style={{ padding: '8px 16px', borderRadius: 8, background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                {adding ? 'Adding…' : '+ Add Lead'}
              </button>
              <button type="button" onClick={() => { setAddOpen(false); setAddErr(null) }} style={{ padding: '8px 12px', borderRadius: 8, background: C.rowBg, color: C.mid, border: `1px solid ${C.border}`, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
            </div>
            {addErr && <div style={{ fontSize: 11, color: C.red }}>{addErr}</div>}
          </div>
        </form>
      )}

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 6 }}>
          <input value={searchInput} onChange={e => setSearchInput(e.target.value)} placeholder="Search username, bio, website…" style={{ ...inputStyle, width: 220 }} />
          <button type="submit" style={{ padding: '8px 14px', borderRadius: 8, background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Search</button>
        </form>
        <select value={source} onChange={e => { setSource(e.target.value); setPage(1) }} style={{ ...inputStyle }}>
          <option value="">All Sources</option>
          <option value="instagram">Instagram</option>
          <option value="linkedin">LinkedIn</option>
          <option value="manual">Manual</option>
        </select>
        <select value={priority} onChange={e => { setPriority(e.target.value); setPage(1) }} style={{ ...inputStyle }}>
          <option value="">All Priority</option>
          <option value="hot">🔥 Hot</option>
          <option value="warm">🌤 Warm</option>
          <option value="cold">❄️ Cold</option>
          <option value="skip">Skip</option>
          <option value="unscored">— Unscored</option>
        </select>
        <select value={status} onChange={e => { setStatus_(e.target.value); setPage(1) }} style={{ ...inputStyle }}>
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="review_pending">Review Pending</option>
          <option value="reviewing">Reviewing</option>
          <option value="approved">Approved</option>
          <option value="qualified">Qualified</option>
          <option value="rejected">Rejected</option>
          <option value="contact_ready">Contact Ready</option>
          <option value="contacted">Contacted</option>
        </select>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: C.light }}>{total} leads</span>
          {!addOpen && (
            <button onClick={() => setAddOpen(true)} style={{ padding: '7px 14px', borderRadius: 8, background: 'rgba(10,191,202,.12)', color: C.teal, border: `1px solid rgba(10,191,202,.25)`, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
              + Add Lead
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner size={32} /></div>
      ) : leads.length === 0 ? (
        <EmptyState icon="👥" title="No leads found" sub="Start a discovery job or adjust your filters" />
      ) : (
        <div style={{ background: C.white, borderRadius: 14, border: `1px solid ${C.border}`, overflow: 'hidden' }}>
          {/* Table header */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 90px 80px 100px 100px 100px 90px', padding: '10px 16px', background: C.rowBg, borderBottom: `1px solid ${C.border}` }}>
            {['Account','Source','Score','Priority','Status','Followers','Actions'].map(h => (
              <div key={h} style={{ fontSize: 11, fontWeight: 700, color: C.mid, textTransform: 'uppercase', letterSpacing: '.04em' }}>{h}</div>
            ))}
          </div>
          {leads.map((lead, i) => (
            <div key={lead.id} style={{
              display: 'grid', gridTemplateColumns: '2fr 90px 80px 100px 100px 100px 90px',
              padding: '12px 16px', borderBottom: i < leads.length - 1 ? `1px solid ${C.border}` : 'none',
              alignItems: 'center', cursor: 'pointer', transition: 'background .1s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = C.rowBg}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            onClick={() => setSelectedLead(lead)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                {lead.profile_image_url ? (
                  <img src={lead.profile_image_url} alt="" style={{ width: 32, height: 32, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }}
                    onError={e => { e.target.style.display='none' }} />
                ) : (
                  <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(10,191,202,.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, color: C.teal, flexShrink: 0 }}>
                    {lead.username[0]?.toUpperCase()}
                  </div>
                )}
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: C.dark, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>@{lead.username}</div>
                  <div style={{ fontSize: 11, color: C.light, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.full_name || lead.website || '—'}</div>
                </div>
              </div>
              <div style={{ fontSize: 12, color: C.mid }}>{lead.source}</div>
              <ScoreBar score={lead.lead_score} />
              <Badge value={lead.priority_level || 'unscored'} styleMap={PRIORITY_STYLE} />
              <Badge value={lead.lead_status} styleMap={STATUS_STYLE} />
              <div style={{ fontSize: 12, color: C.mid }}>{lead.followers_count?.toLocaleString('en-IN') || '—'}</div>
              <button onClick={e => { e.stopPropagation(); setSelectedLead(lead) }} style={{ padding: '4px 10px', borderRadius: 6, background: 'rgba(10,191,202,.1)', color: C.teal, border: 'none', fontSize: 12, cursor: 'pointer' }}>View →</button>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginTop: 16 }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ padding: '6px 12px', borderRadius: 7, border: `1px solid ${C.border}`, background: C.white, cursor: page === 1 ? 'not-allowed' : 'pointer', fontSize: 12 }}>‹ Prev</button>
          <span style={{ padding: '6px 12px', fontSize: 12, color: C.mid }}>Page {page} of {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages} style={{ padding: '6px 12px', borderRadius: 7, border: `1px solid ${C.border}`, background: C.white, cursor: page === pages ? 'not-allowed' : 'pointer', fontSize: 12 }}>Next ›</button>
        </div>
      )}

      {/* Lead detail panel */}
      {selectedLead && (
        <>
          <div onClick={() => setSelectedLead(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.35)', zIndex: 999 }} />
          <LeadDetail lead={selectedLead} token={token} onClose={() => setSelectedLead(null)} onUpdate={handleLeadUpdate} />
        </>
      )}
    </div>
  )
}

// ── Jobs Tab ──────────────────────────────────────────────────────────────────
function JobsTab({ token, onViewLeads }) {
  const [jobs, setJobs]     = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [form, setForm]     = useState({ source: 'instagram', job_type: 'hashtag', keyword: '', max_leads: 100 })
  const [formErr, setFormErr]= useState(null)
  const [liveJob, setLiveJob]= useState(null)
  const [events, setEvents] = useState([])
  const readerRef = useRef(null)

  const load = useCallback(async () => {
    try {
      const data = await api(token, '/seller-discovery/jobs?page_size=50')
      setJobs(data.items || [])
    } catch {}
    finally { setLoading(false) }
  }, [token])

  useEffect(() => { load() }, [load])

  async function createJob() {
    if (!form.keyword.trim()) { setFormErr('Keyword is required'); return }
    setCreating(true)
    setFormErr(null)
    try {
      const job = await api(token, '/seller-discovery/jobs', { method: 'POST', body: JSON.stringify(form) })
      setJobs(prev => [job, ...prev])
      setForm(f => ({ ...f, keyword: '' }))
      watchJob(job.id)
    } catch (e) { setFormErr(String(e)) }
    finally { setCreating(false) }
  }

  function watchJob(jobId) {
    if (readerRef.current) { readerRef.current.cancel() }
    setLiveJob(jobId)
    setEvents([])
    fetch(`/api/seller-discovery/jobs/${jobId}/events`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(resp => {
      const reader = resp.body.getReader()
      readerRef.current = reader
      const decoder = new TextDecoder()
      ;(async () => {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const text = decoder.decode(value)
          for (const line of text.split('\n')) {
            if (!line.startsWith('data: ')) continue
            try {
              const evt = JSON.parse(line.slice(6))
              if (evt.type === 'stream_end') { load(); return }
              setEvents(prev => [...prev.slice(-49), evt])
            } catch {}
          }
        }
        load()
      })()
    }).catch(() => {})
  }

  useEffect(() => () => { readerRef.current?.cancel() }, [])

  const EVENT_ICON = { job_started: '▶', profile_found: '👤', lead_created: '✓', lead_duplicate: '⟳', progress: '📊', job_completed: '✅', job_failed: '❌', blocked: '🚫', lead_skipped: '⚠️' }

  return (
    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
      {/* Create form */}
      <div style={{ flex: '0 0 320px', background: C.white, borderRadius: 14, padding: 24, border: `1px solid ${C.border}` }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: C.dark }}>New Discovery Job</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: C.mid, display: 'block', marginBottom: 4 }}>Source</label>
            <select value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))} style={{ ...inputStyle, width: '100%' }}>
              <option value="instagram">Instagram</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: C.mid, display: 'block', marginBottom: 4 }}>Job Type</label>
            <select value={form.job_type} onChange={e => setForm(f => ({ ...f, job_type: e.target.value }))} style={{ ...inputStyle, width: '100%' }}>
              <option value="hashtag">Hashtag Search</option>
              <option value="direct">Direct Profile</option>
              <option value="competitor_followers">Competitor Followers</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: C.mid, display: 'block', marginBottom: 4 }}>
              {form.job_type === 'hashtag' ? 'Hashtag (e.g. #ethnicwear)' : 'Username / Profile'}
            </label>
            <input value={form.keyword} onChange={e => setForm(f => ({ ...f, keyword: e.target.value }))} placeholder={form.job_type === 'hashtag' ? '#ethnicwear' : 'username'} style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }} />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: C.mid, display: 'block', marginBottom: 4 }}>Max Leads</label>
            <input type="number" min={1} max={500} value={form.max_leads} onChange={e => setForm(f => ({ ...f, max_leads: parseInt(e.target.value) || 10 }))} style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }} />
          </div>
          {formErr && <div style={{ fontSize: 12, color: C.red }}>{formErr}</div>}
          <button onClick={createJob} disabled={creating} style={{ padding: 10, borderRadius: 8, background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', border: 'none', fontWeight: 700, fontSize: 13, cursor: creating ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            {creating ? <><Spinner size={16} /> Creating…</> : '⚡ Launch Job'}
          </button>
        </div>

        {/* Live SSE events */}
        {liveJob && (
          <div style={{ marginTop: 20, background: C.dark, borderRadius: 10, padding: 14, maxHeight: 220, overflowY: 'auto' }}>
            <div style={{ fontSize: 11, color: C.teal, fontWeight: 700, marginBottom: 8 }}>LIVE EVENTS</div>
            {events.length === 0 && <div style={{ fontSize: 12, color: C.light }}>Waiting for events…</div>}
            {events.map((evt, i) => (
              <div key={i} style={{ fontSize: 11, color: '#C8D9E8', marginBottom: 4, display: 'flex', gap: 6 }}>
                <span>{EVENT_ICON[evt.type] || '•'}</span>
                <span style={{ color: evt.type.includes('failed') || evt.type === 'blocked' ? C.red : C.teal }}>{evt.type}</span>
                {evt.username && <span style={{ color: '#8FA5BD' }}>@{evt.username}</span>}
                {evt.leads_found != null && <span style={{ color: '#8FA5BD' }}>found:{evt.leads_found} created:{evt.leads_created}</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Job list */}
      <div style={{ flex: 1, minWidth: 300 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.dark }}>Discovery Jobs ({jobs.length})</h3>
          <button onClick={load} style={{ padding: '5px 10px', borderRadius: 7, background: C.rowBg, border: `1px solid ${C.border}`, fontSize: 12, cursor: 'pointer', color: C.mid }}>↺ Refresh</button>
        </div>
        {loading ? <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner /></div>
        : jobs.length === 0 ? <EmptyState icon="⚡" title="No jobs yet" sub="Create a job to start discovering sellers" />
        : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {jobs.map(job => {
              const { label: jobStatusLabel, ...jobStatusStyle } = JOB_STATUS_STYLE[job.status] || JOB_STATUS_STYLE.queued
              const isDone = job.status === 'completed'
              const hasFailed = job.status === 'failed'
              const leadsFound = job.leads_found ?? job.leads_created ?? 0
              return (
                <div key={job.id} style={{ background: C.white, borderRadius: 12, padding: '14px 18px', border: `1px solid ${isDone && leadsFound > 0 ? 'rgba(10,191,202,.3)' : C.border}` }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 14, fontWeight: 700, color: C.dark }}>{job.keyword}</span>
                        <span style={{ ...jobStatusStyle, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700 }}>{jobStatusLabel || job.status}</span>
                        <span style={{ fontSize: 11, color: C.light }}>{job.job_type}</span>
                      </div>
                      <div style={{ fontSize: 12, color: C.light, marginBottom: isDone ? 8 : 0 }}>
                        {job.source} · by {job.triggered_by} · {new Date(job.created_at).toLocaleDateString('en-IN')}
                      </div>
                      {isDone && (
                        <div style={{ display: 'flex', gap: 14, fontSize: 12 }}>
                          <span style={{ color: leadsFound > 0 ? C.teal : C.light, fontWeight: leadsFound > 0 ? 700 : 400 }}>
                            {leadsFound > 0 ? `✓ ${job.leads_created ?? 0} leads created` : '— 0 leads found'}
                          </span>
                          {(job.leads_found ?? 0) > (job.leads_created ?? 0) && (
                            <span style={{ color: C.light }}>⟳ {(job.leads_found ?? 0) - (job.leads_created ?? 0)} duplicates</span>
                          )}
                        </div>
                      )}
                      {hasFailed && job.error_message && (
                        <div style={{ fontSize: 11, color: C.red, marginTop: 4 }}>{job.error_message.slice(0, 120)}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      {job.status === 'running' && (
                        <button onClick={() => watchJob(job.id)} style={{ padding: '5px 12px', borderRadius: 6, background: 'rgba(233,147,13,.12)', color: C.amber, border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Watch</button>
                      )}
                      {isDone && leadsFound > 0 && (
                        <button
                          onClick={() => onViewLeads(job)}
                          style={{ padding: '5px 14px', borderRadius: 6, background: 'linear-gradient(135deg,rgba(10,191,202,.15),rgba(10,191,202,.08))', color: C.teal, border: `1px solid rgba(10,191,202,.3)`, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}
                        >
                          View Leads →
                        </button>
                      )}
                      {isDone && leadsFound === 0 && (
                        <span style={{ fontSize: 11, color: C.light, padding: '5px 0' }}>No leads found</span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Keywords Tab ──────────────────────────────────────────────────────────────
function KeywordsTab({ token }) {
  const [keywords, setKeywords] = useState([])
  const [loading, setLoading]   = useState(true)
  const [form, setForm]         = useState({ keyword: '', keyword_type: 'hashtag', source: 'instagram', priority: 5 })
  const [adding, setAdding]     = useState(false)
  const [err, setErr]           = useState(null)

  const load = useCallback(async () => {
    try {
      const data = await api(token, '/seller-discovery/keywords?page_size=200')
      setKeywords(data.items || [])
    } catch {}
    finally { setLoading(false) }
  }, [token])

  useEffect(() => { load() }, [load])

  async function addKeyword() {
    if (!form.keyword.trim()) { setErr('Keyword required'); return }
    setAdding(true); setErr(null)
    try {
      const kw = await api(token, '/seller-discovery/keywords', { method: 'POST', body: JSON.stringify(form) })
      setKeywords(prev => [kw, ...prev])
      setForm(f => ({ ...f, keyword: '' }))
    } catch (e) { setErr(String(e)) }
    finally { setAdding(false) }
  }

  async function toggleActive(kw) {
    const updated = await api(token, `/seller-discovery/keywords/${kw.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: !kw.is_active }),
    })
    setKeywords(prev => prev.map(k => k.id === kw.id ? updated : k))
  }

  return (
    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
      {/* Add form */}
      <div style={{ flex: '0 0 300px', background: C.white, borderRadius: 14, padding: 22, border: `1px solid ${C.border}` }}>
        <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 700, color: C.dark }}>Add Keyword</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input value={form.keyword} onChange={e => setForm(f => ({ ...f, keyword: e.target.value }))} placeholder="#fashion or @competitor" style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }} />
          <select value={form.keyword_type} onChange={e => setForm(f => ({ ...f, keyword_type: e.target.value }))} style={{ ...inputStyle, width: '100%' }}>
            <option value="hashtag">Hashtag</option>
            <option value="competitor">Competitor</option>
            <option value="direct">Direct</option>
          </select>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: C.mid }}>Priority:</label>
            <input type="range" min={1} max={10} value={form.priority} onChange={e => setForm(f => ({ ...f, priority: parseInt(e.target.value) }))} style={{ flex: 1 }} />
            <span style={{ fontSize: 12, fontWeight: 700, color: C.teal, minWidth: 16 }}>{form.priority}</span>
          </div>
          {err && <div style={{ fontSize: 12, color: C.red }}>{err}</div>}
          <button onClick={addKeyword} disabled={adding} style={{ padding: '9px', borderRadius: 8, background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', border: 'none', fontWeight: 700, fontSize: 13, cursor: 'pointer' }}>
            {adding ? 'Adding…' : '+ Add Keyword'}
          </button>
        </div>
      </div>

      {/* Keyword list */}
      <div style={{ flex: 1 }}>
        <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 700, color: C.dark }}>Keywords ({keywords.length})</h3>
        {loading ? <Spinner /> : keywords.length === 0 ? <EmptyState icon="🔑" title="No keywords yet" sub="Add a hashtag or competitor to start discovering sellers" />
        : (
          <div style={{ background: C.white, borderRadius: 14, border: `1px solid ${C.border}`, overflow: 'hidden' }}>
            {keywords.map((kw, i) => (
              <div key={kw.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderBottom: i < keywords.length - 1 ? `1px solid ${C.border}` : 'none', opacity: kw.is_active ? 1 : 0.5 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: C.dark }}>{kw.keyword}</div>
                  <div style={{ fontSize: 11, color: C.light }}>{kw.keyword_type} · {kw.source} · {kw.leads_found} leads · {kw.crawl_count} crawls</div>
                </div>
                <span style={{ fontSize: 11, color: C.light }}>P{kw.priority}</span>
                <button onClick={() => toggleActive(kw)} style={{ padding: '4px 10px', borderRadius: 6, background: kw.is_active ? 'rgba(16,185,129,.12)' : 'rgba(75,96,128,.12)', color: kw.is_active ? C.green : C.light, border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                  {kw.is_active ? 'Active' : 'Paused'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Analytics Tab ─────────────────────────────────────────────────────────────
function AnalyticsTab({ token }) {
  const [data, setData]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api(token, '/seller-discovery/analytics')
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}><Spinner size={36} /></div>
  if (!data)   return <EmptyState icon="📊" title="Analytics unavailable" sub="Could not load analytics data" />

  const ov = data.overview || {}

  return (
    <div>
      {/* KPI cards */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <StatCard label="Total Leads"    value={ov.total_leads}                 color={C.teal}   />
        <StatCard label="Hot Leads"      value={ov.hot_leads}                   color={C.red}    />
        <StatCard label="Classified"     value={`${ov.classification_rate}%`}   color={C.purple} sub={`${ov.classified_leads} leads`} />
        <StatCard label="Qualified"      value={ov.qualified_leads}             color={C.green}  sub={`${ov.qualification_rate}% rate`} />
        <StatCard label="Review Queue"   value={ov.review_queue_size}           color={C.amber}  />
        <StatCard label="Outreach Ready" value={ov.outreach_ready}              color={C.teal}   />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        {/* Leads per day */}
        <div style={{ background: C.white, borderRadius: 14, padding: '20px 24px', border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.dark, marginBottom: 16 }}>Leads Discovered / Day (30d)</div>
          {(data.leads_per_day || []).length === 0
            ? <div style={{ color: C.light, fontSize: 13, textAlign: 'center', padding: 40 }}>No data yet</div>
            : <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data.leads_per_day}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis dataKey="day" tick={{ fontSize: 10 }} tickFormatter={d => d?.slice(5)} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip formatter={(v) => [v, 'Leads']} labelFormatter={l => `Date: ${l}`} />
                  <Line type="monotone" dataKey="count" stroke={C.teal} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
          }
        </div>

        {/* Score distribution */}
        <div style={{ background: C.white, borderRadius: 14, padding: '20px 24px', border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.dark, marginBottom: 16 }}>Score Distribution</div>
          {(data.score_distribution || []).length === 0
            ? <div style={{ color: C.light, fontSize: 13, textAlign: 'center', padding: 40 }}>No scored leads yet</div>
            : <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.score_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis dataKey="priority" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill={C.teal} radius={[4, 4, 0, 0]}>
                    {(data.score_distribution || []).map((entry, i) => {
                      const col = { hot: C.red, warm: C.amber, cold: C.teal, skip: C.light, unscored: C.light }
                      return <Cell key={i} fill={col[entry.priority] || C.teal} />
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
          }
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Category breakdown */}
        <div style={{ background: C.white, borderRadius: 14, padding: '20px 24px', border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.dark, marginBottom: 16 }}>AI Category Breakdown</div>
          {(data.category_breakdown || []).length === 0
            ? <div style={{ color: C.light, fontSize: 13, textAlign: 'center', padding: 30 }}>Classify leads to see categories</div>
            : <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie data={data.category_breakdown} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={70}>
                      {data.category_breakdown.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ flex: 1 }}>
                  {data.category_breakdown.map((row, i) => (
                    <div key={row.category} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: C.mid, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: PIE_COLORS[i % PIE_COLORS.length], display: 'inline-block' }} />
                        {row.category}
                      </span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: C.dark }}>{row.count}</span>
                    </div>
                  ))}
                </div>
              </div>
          }
        </div>

        {/* Keyword performance */}
        <div style={{ background: C.white, borderRadius: 14, padding: '20px 24px', border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.dark, marginBottom: 16 }}>Keyword Performance</div>
          {(data.keyword_performance || []).length === 0
            ? <div style={{ color: C.light, fontSize: 13, textAlign: 'center', padding: 30 }}>No keyword data yet</div>
            : (data.keyword_performance || []).slice(0, 8).map(kw => (
                <div key={kw.keyword} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: C.dark, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{kw.keyword}</span>
                  <span style={{ fontSize: 11, color: C.light }}>{kw.crawl_count} crawls</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: C.teal }}>{kw.leads_found} leads</span>
                </div>
              ))
          }
        </div>
      </div>
    </div>
  )
}

// ── Review Queue Tab ──────────────────────────────────────────────────────────
function ReviewTab({ token }) {
  const [subTab, setSubTab]   = useState('review')
  const [leads, setLeads]     = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [acting, setActing]   = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const endpoint = subTab === 'review' ? '/seller-discovery/review-queue' : '/seller-discovery/outreach-queue'
      const data = await api(token, `${endpoint}?page_size=100`)
      setLeads(data.items || [])
    } catch {}
    finally { setLoading(false) }
  }, [token, subTab])

  useEffect(() => { load() }, [load])

  async function doAction(leadId, action, notes = '') {
    setActing(leadId)
    try {
      const updated = await api(token, `/seller-discovery/leads/${leadId}/review`, {
        method: 'POST',
        body: JSON.stringify({ action, notes: notes || undefined }),
      })
      setLeads(prev => prev.filter(l => l.id !== leadId))
      if (selected?.id === leadId) setSelected(updated)
    } catch {}
    finally { setActing(null) }
  }

  async function doOutreach(leadId, outreachStatus) {
    setActing(leadId)
    try {
      await api(token, `/seller-discovery/leads/${leadId}/outreach`, {
        method: 'PATCH',
        body: JSON.stringify({ outreach_status: outreachStatus }),
      })
      setLeads(prev => prev.map(l => l.id === leadId ? { ...l, outreach_status: outreachStatus } : l))
    } catch {}
    finally { setActing(null) }
  }

  return (
    <div>
      {/* Sub-tab selector */}
      <div style={{ display: 'flex', gap: 2, marginBottom: 20, background: C.white, borderRadius: 10, padding: 3, width: 'fit-content', border: `1px solid ${C.border}` }}>
        {[{ id: 'review', label: '📋 Review Queue' }, { id: 'outreach', label: '📤 Outreach Queue' }].map(t => (
          <button key={t.id} onClick={() => setSubTab(t.id)} style={{ padding: '7px 18px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600, background: subTab === t.id ? 'linear-gradient(135deg,#0ABFCA,#088F99)' : 'transparent', color: subTab === t.id ? '#fff' : C.mid, transition: 'all .15s' }}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner size={32} /></div>
      : leads.length === 0 ? <EmptyState icon={subTab === 'review' ? '📋' : '📤'} title={subTab === 'review' ? 'Review queue empty' : 'No outreach-ready leads'} sub={subTab === 'review' ? 'All leads have been reviewed' : 'Qualify or approve leads to add them here'} />
      : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {leads.map(lead => (
            <div key={lead.id} style={{ background: C.white, borderRadius: 12, border: `1px solid ${C.border}`, padding: '14px 18px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: C.dark }}>@{lead.username}</span>
                    <Badge value={lead.priority_level || 'unscored'} styleMap={PRIORITY_STYLE} />
                    <Badge value={lead.lead_status} styleMap={STATUS_STYLE} />
                    {lead.lead_score != null && <ScoreBar score={lead.lead_score} />}
                  </div>
                  <div style={{ fontSize: 12, color: C.light, marginBottom: 4 }}>
                    {lead.source} · {lead.followers_count?.toLocaleString('en-IN')} followers
                    {lead.website && ` · ${lead.website}`}
                  </div>
                  {lead.bio && <div style={{ fontSize: 12, color: C.mid, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 500 }}>{lead.bio}</div>}
                  {subTab === 'outreach' && lead.ai_outreach_suggestion && (
                    <div style={{ fontSize: 12, color: C.teal, marginTop: 6, fontStyle: 'italic' }}>💬 {lead.ai_outreach_suggestion}</div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  {subTab === 'review' && (
                    <>
                      <button onClick={() => doAction(lead.id, 'approve')} disabled={acting === lead.id} style={{ padding: '5px 10px', borderRadius: 6, background: 'rgba(16,185,129,.12)', color: C.green, border: 'none', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>✓ Approve</button>
                      <button onClick={() => doAction(lead.id, 'qualify')} disabled={acting === lead.id} style={{ padding: '5px 10px', borderRadius: 6, background: 'rgba(16,185,129,.15)', color: C.green, border: 'none', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>🎯 Qualify</button>
                      <button onClick={() => doAction(lead.id, 'reject')} disabled={acting === lead.id} style={{ padding: '5px 10px', borderRadius: 6, background: 'rgba(232,52,74,.1)', color: C.red, border: 'none', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>✕ Reject</button>
                      <button onClick={() => setSelected(lead)} style={{ padding: '5px 10px', borderRadius: 6, background: 'rgba(10,191,202,.1)', color: C.teal, border: 'none', fontSize: 12, cursor: 'pointer' }}>View</button>
                    </>
                  )}
                  {subTab === 'outreach' && (
                    <>
                      <select value={lead.outreach_status || 'pending'} onChange={e => doOutreach(lead.id, e.target.value)} style={{ ...inputStyle, fontSize: 12, padding: '5px 8px' }}>
                        <option value="pending">Pending</option>
                        <option value="ready">Ready</option>
                        <option value="contacted">Contacted</option>
                        <option value="skipped">Skipped</option>
                      </select>
                      <button onClick={() => setSelected(lead)} style={{ padding: '5px 10px', borderRadius: 6, background: 'rgba(10,191,202,.1)', color: C.teal, border: 'none', fontSize: 12, cursor: 'pointer' }}>View</button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <>
          <div onClick={() => setSelected(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.35)', zIndex: 999 }} />
          <LeadDetail lead={selected} token={token} onClose={() => setSelected(null)} onUpdate={updated => { setLeads(prev => prev.map(l => l.id === updated.id ? updated : l)); setSelected(updated) }} />
        </>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function SellerDiscovery() {
  const token = useAuthStore(s => s.token)
  const [tab, setTab] = useState('leads')
  const [overview, setOverview] = useState(null)
  // lifted state: job → leads cross-tab navigation
  const [leadsFilter, setLeadsFilter] = useState(null)   // null | { jobId, keyword }

  function handleViewLeads(job) {
    setLeadsFilter({ jobId: job.id, keyword: job.keyword })
    setTab('leads')
  }

  useEffect(() => {
    api(token, '/seller-discovery/analytics')
      .then(d => setOverview(d.overview))
      .catch(() => {})
  }, [token, tab])

  const TABS = [
    { id: 'leads',     label: 'Leads',        icon: '👥' },
    { id: 'jobs',      label: 'Discovery',    icon: '⚡' },
    { id: 'keywords',  label: 'Keywords',     icon: '🔑' },
    { id: 'analytics', label: 'Analytics',    icon: '📊' },
    { id: 'review',    label: 'Review',       icon: '📋' },
  ]

  return (
    <div style={{ padding: '24px 28px', minHeight: '100vh', background: C.bg }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>

      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <div style={{ fontSize: 24 }}>🔭</div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: C.dark }}>Seller Discovery</h1>
          <span style={{ background: 'rgba(10,191,202,.15)', color: C.teal, borderRadius: 20, padding: '3px 12px', fontSize: 11, fontWeight: 700 }}>AI-POWERED</span>
        </div>
        <div style={{ fontSize: 13, color: C.light }}>
          Instagram scraping · AI classification · Lead scoring · CRM workflows · Outreach preparation
        </div>
      </div>

      {/* Overview KPIs */}
      {overview && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 22, flexWrap: 'wrap' }}>
          <StatCard label="Total Leads"    value={overview.total_leads}     color={C.teal}   onClick={() => setTab('leads')}     />
          <StatCard label="Hot Leads"      value={overview.hot_leads}       color={C.red}    onClick={() => setTab('leads')}     />
          <StatCard label="Review Queue"   value={overview.review_queue_size} color={C.amber} onClick={() => setTab('review')}   />
          <StatCard label="Outreach Ready" value={overview.outreach_ready}  color={C.purple} onClick={() => setTab('review')}    />
          <StatCard label="Active Jobs"    value={overview.active_jobs}     color={C.green}  onClick={() => setTab('jobs')}      />
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 2, marginBottom: 24, background: C.white, borderRadius: 12, padding: 4, width: 'fit-content', border: `1px solid ${C.border}` }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{ padding: '8px 20px', borderRadius: 9, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600, background: tab === t.id ? 'linear-gradient(135deg,#0ABFCA,#088F99)' : 'transparent', color: tab === t.id ? '#fff' : C.mid, display: 'flex', alignItems: 'center', gap: 6, transition: 'all .15s' }}>
            <span>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'leads'     && <LeadsTab     token={token} jobFilter={leadsFilter} onClearJobFilter={() => setLeadsFilter(null)} />}
      {tab === 'jobs'      && <JobsTab      token={token} onViewLeads={handleViewLeads} />}
      {tab === 'keywords'  && <KeywordsTab  token={token} />}
      {tab === 'analytics' && <AnalyticsTab token={token} />}
      {tab === 'review'    && <ReviewTab    token={token} />}
    </div>
  )
}
