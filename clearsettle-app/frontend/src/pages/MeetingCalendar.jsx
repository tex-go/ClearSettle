import React, { useState, useEffect, useCallback, useRef } from 'react'
import useAuthStore from '../store/authStore'
import _axiosApi from '../utils/api'

// Proxy through the shared axios client (which handles 401 refresh automatically).
// Token parameter is kept for backward-compat with child component calls but is ignored —
// axios interceptor injects the token from localStorage on every request.
function api(_token, path, opts) {
  var method = (opts && opts.method ? opts.method : 'GET').toLowerCase()
  var body = opts && opts.body ? JSON.parse(opts.body) : undefined
  if (method === 'get') return _axiosApi.get(path).then(function(r) { return r.data })
  return _axiosApi[method](path, body).then(function(r) { return r.data || null })
}

var TYPE_STYLE = {
  internal: { background: 'rgba(99,102,241,.15)', color: '#6366F1' },
  external: { background: 'rgba(10,191,202,.15)',  color: '#0ABFCA' },
  client:   { background: 'rgba(34,197,94,.15)',   color: '#22C55E' },
  vendor:   { background: 'rgba(245,158,11,.15)',  color: '#E9930D' },
  team:     { background: 'rgba(168,85,247,.15)',  color: '#A855F7' },
}

var STATUS_STYLE = {
  scheduled:    { background: 'rgba(10,191,202,.1)',   color: '#0ABFCA' },
  confirmed:    { background: 'rgba(34,197,94,.1)',    color: '#22C55E' },
  cancelled:    { background: 'rgba(239,68,68,.1)',    color: '#EF4444' },
  completed:    { background: 'rgba(100,116,139,.1)',  color: '#64748B' },
  rescheduled:  { background: 'rgba(245,158,11,.1)',   color: '#E9930D' },
}

var PLATFORM_ICONS = {
  teams:     '💼',
  zoom:      '🎥',
  meet:      '📹',
  in_person: '🏢',
  phone:     '📞',
}

var NOTE_TYPE_COLORS = {
  pre_meeting:  '#6366F1',
  action_item:  '#EF4444',
  decision:     '#22C55E',
  general:      '#64748B',
  follow_up:    '#E9930D',
}

function Badge({ style, label }) {
  return (
    <span style={{
      ...style, borderRadius: 20, padding: '2px 10px',
      fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
    }}>{label}</span>
  )
}

var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
var MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December']

function calendarWeeks(year, month) {
  var first = new Date(year, month, 1)
  var last  = new Date(year, month + 1, 0)
  var weeks = []
  var day   = new Date(first)
  day.setDate(day.getDate() - day.getDay())   // start from Sunday
  while (day <= last || day.getDay() !== 0) {
    var week = []
    for (var i = 0; i < 7; i++) {
      week.push(new Date(day))
      day.setDate(day.getDate() + 1)
    }
    weeks.push(week)
    if (day > last && day.getDay() === 0) break
  }
  return weeks
}

function toISO(d) { return d.toISOString().slice(0, 10) }

// ── Create Meeting Modal ───────────────────────────────────────────────────────

function CreateMeetingModal({ token, defaultDate, onCreated, onClose }) {
  var [form, setForm] = useState({
    title: '',
    meeting_type: 'internal',
    start_at: defaultDate ? defaultDate + 'T10:00' : '',
    end_at:   defaultDate ? defaultDate + 'T11:00' : '',
    timezone: 'Asia/Kolkata',
    location: '',
    platform: '',
    organizer_email: '',
    organizer_name: '',
    agenda: '',
    description: '',
  })
  var [participants, setParticipants] = useState([])
  var [reminders, setReminders] = useState([{ reminder_type: 'in_app', minutes_before: 15 }])
  var [newEmail, setNewEmail] = useState('')
  var [saving, setSaving] = useState(false)
  var [err, setErr] = useState(null)

  function setField(k, v) { setForm(function(f) { return { ...f, [k]: v } }) }

  function addParticipant() {
    if (!newEmail.trim()) return
    setParticipants(function(p) { return [...p, { email: newEmail.trim(), role: 'required' }] })
    setNewEmail('')
  }

  function submit() {
    setSaving(true)
    setErr(null)
    var payload = {
      ...form,
      participants: participants,
      reminders: reminders,
    }
    api(token, '/meetings', { method: 'POST', body: JSON.stringify(payload) })
      .then(function(m) { onCreated(m) })
      .catch(function(e) { setErr(e.message) })
      .finally(function() { setSaving(false) })
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: '#fff', borderRadius: 16, padding: '28px 32px',
        width: '100%', maxWidth: 580, maxHeight: '90vh', overflowY: 'auto',
        boxShadow: '0 24px 64px rgba(0,0,0,.25)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#0D1F35' }}>Schedule Meeting</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#8FA5BD' }}>✕</button>
        </div>

        {err && <div style={{ background: 'rgba(239,68,68,.08)', color: '#EF4444', borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 13 }}>{err}</div>}

        <div style={{ display: 'grid', gap: 14 }}>
          {[
            { label: 'Title *', key: 'title', type: 'text' },
            { label: 'Organizer Email *', key: 'organizer_email', type: 'email' },
            { label: 'Organizer Name', key: 'organizer_name', type: 'text' },
          ].map(function(f) {
            return (
              <div key={f.key}>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>{f.label}</label>
                <input value={form[f.key]} onChange={function(e) { setField(f.key, e.target.value) }}
                  type={f.type} style={{
                    width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                    border: '1px solid #E8EEF4', outline: 'none', boxSizing: 'border-box',
                  }} />
              </div>
            )
          })}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Start</label>
              <input type="datetime-local" value={form.start_at} onChange={function(e) { setField('start_at', e.target.value) }}
                style={{ width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, border: '1px solid #E8EEF4', boxSizing: 'border-box' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>End</label>
              <input type="datetime-local" value={form.end_at} onChange={function(e) { setField('end_at', e.target.value) }}
                style={{ width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, border: '1px solid #E8EEF4', boxSizing: 'border-box' }} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Type</label>
              <select value={form.meeting_type} onChange={function(e) { setField('meeting_type', e.target.value) }}
                style={{ width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, border: '1px solid #E8EEF4', background: '#fff' }}>
                {['internal','external','client','vendor','team'].map(function(t) {
                  return <option key={t} value={t}>{t[0].toUpperCase() + t.slice(1)}</option>
                })}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Platform</label>
              <select value={form.platform} onChange={function(e) { setField('platform', e.target.value) }}
                style={{ width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, border: '1px solid #E8EEF4', background: '#fff' }}>
                <option value="">— None —</option>
                {['teams','zoom','meet','in_person','phone'].map(function(p) {
                  return <option key={p} value={p}>{PLATFORM_ICONS[p]} {p}</option>
                })}
              </select>
            </div>
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Location / Meeting URL</label>
            <input value={form.location} onChange={function(e) { setField('location', e.target.value) }}
              style={{ width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, border: '1px solid #E8EEF4', boxSizing: 'border-box' }} />
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Agenda</label>
            <textarea value={form.agenda} onChange={function(e) { setField('agenda', e.target.value) }} rows={3}
              style={{ width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, border: '1px solid #E8EEF4', resize: 'vertical', boxSizing: 'border-box' }} />
          </div>

          {/* Participants */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 6 }}>Participants</label>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input value={newEmail} onChange={function(e) { setNewEmail(e.target.value) }} placeholder="email@example.com"
                onKeyDown={function(e) { if (e.key === 'Enter') { e.preventDefault(); addParticipant() } }}
                style={{ flex: 1, padding: '8px 12px', borderRadius: 8, fontSize: 13, border: '1px solid #E8EEF4' }} />
              <button onClick={addParticipant} style={{
                padding: '8px 14px', borderRadius: 8, background: '#0ABFCA', color: '#fff',
                border: 'none', fontSize: 13, fontWeight: 700, cursor: 'pointer',
              }}>Add</button>
            </div>
            {participants.map(function(p, i) {
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <div style={{ flex: 1, background: '#F8FAFC', border: '1px solid #E8EEF4', borderRadius: 8, padding: '7px 12px', fontSize: 12 }}>
                    {p.email}
                    <select value={p.role} onChange={function(e) {
                      setParticipants(function(ps) { return ps.map(function(x, j) { return j === i ? { ...x, role: e.target.value } : x }) })
                    }} style={{ marginLeft: 10, border: 'none', background: 'transparent', fontSize: 11, color: '#8FA5BD' }}>
                      <option value="required">Required</option>
                      <option value="optional">Optional</option>
                    </select>
                  </div>
                  <button onClick={function() { setParticipants(function(ps) { return ps.filter(function(_, j) { return j !== i }) }) }}
                    style={{ background: 'none', border: 'none', color: '#EF4444', cursor: 'pointer', fontSize: 16, padding: '0 4px' }}>✕</button>
                </div>
              )
            })}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 24 }}>
          <button onClick={onClose} style={{
            padding: '10px 20px', borderRadius: 8, border: '1px solid #E8EEF4',
            background: '#fff', color: '#4B6080', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}>Cancel</button>
          <button onClick={submit} disabled={saving || !form.title || !form.start_at || !form.end_at || !form.organizer_email} style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: saving ? '#CBD5E1' : '#0ABFCA', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer',
          }}>
            {saving ? 'Saving…' : 'Create Meeting'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Meeting Detail Panel ───────────────────────────────────────────────────────

function MeetingPanel({ meeting, token, onUpdated, onClose }) {
  var [noteContent, setNoteContent] = useState('')
  var [noteType, setNoteType] = useState('general')
  var [savingNote, setSavingNote] = useState(false)
  var [tab, setTab] = useState('details')

  function addNote() {
    if (!noteContent.trim()) return
    setSavingNote(true)
    api(token, '/meetings/' + meeting.id + '/notes', {
      method: 'POST',
      body: JSON.stringify({ note_type: noteType, content: noteContent }),
    })
      .then(function(n) {
        setNoteContent('')
        onUpdated({ ...meeting, notes: [...(meeting.notes || []), n] })
      })
      .finally(function() { setSavingNote(false) })
  }

  function updateStatus(newStatus) {
    api(token, '/meetings/' + meeting.id, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus, status_reason: 'Updated via UI' }),
    }).then(onUpdated)
  }

  var typeStyle = TYPE_STYLE[meeting.meeting_type] || { background: '#F1F5F9', color: '#64748B' }
  var statusStyle = STATUS_STYLE[meeting.status] || { background: '#F1F5F9', color: '#64748B' }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)',
      display: 'flex', alignItems: 'stretch', justifyContent: 'flex-end', zIndex: 1000,
    }}>
      <div style={{
        background: '#fff', width: '100%', maxWidth: 560,
        display: 'flex', flexDirection: 'column', overflowY: 'auto',
        boxShadow: '-8px 0 32px rgba(0,0,0,.18)',
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px', borderBottom: '1px solid #E8EEF4',
          background: '#F8FAFC', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              <Badge style={typeStyle}   label={meeting.meeting_type} />
              <Badge style={statusStyle} label={meeting.status} />
              {meeting.platform && <Badge style={{ background: '#F1F5F9', color: '#4B6080' }} label={PLATFORM_ICONS[meeting.platform] + ' ' + meeting.platform} />}
            </div>
            <div style={{ fontWeight: 800, fontSize: 17, color: '#0D1F35', marginBottom: 4 }}>{meeting.title}</div>
            <div style={{ fontSize: 12, color: '#8FA5BD' }}>
              {new Date(meeting.start_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
              {' – '}
              {new Date(meeting.end_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#8FA5BD', flexShrink: 0 }}>✕</button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #E8EEF4', padding: '0 24px' }}>
          {[['details', 'Details'], ['notes', 'Notes (' + (meeting.notes?.length || 0) + ')'], ['participants', 'People (' + (meeting.participants?.length || 0) + ')'], ['history', 'History']].map(function([k, l]) {
            return (
              <button key={k} onClick={function() { setTab(k) }} style={{
                padding: '10px 14px', border: 'none', background: 'none', cursor: 'pointer',
                fontSize: 13, fontWeight: 600,
                color: tab === k ? '#0ABFCA' : '#8FA5BD',
                borderBottom: tab === k ? '2px solid #0ABFCA' : '2px solid transparent',
                marginBottom: -1,
              }}>{l}</button>
            )
          })}
        </div>

        {/* Content */}
        <div style={{ flex: 1, padding: '20px 24px', overflowY: 'auto' }}>

          {tab === 'details' && (
            <div>
              {meeting.organizer_name && <Row label="Organizer" value={meeting.organizer_name + ' (' + meeting.organizer_email + ')'} />}
              {meeting.location && <Row label="Location" value={meeting.location} />}
              {meeting.agenda && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#8FA5BD', marginBottom: 6, textTransform: 'uppercase' }}>Agenda</div>
                  <div style={{ background: '#F8FAFC', borderRadius: 8, padding: '12px 14px', fontSize: 13, color: '#0D1F35', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{meeting.agenda}</div>
                </div>
              )}
              {meeting.description && <Row label="Description" value={meeting.description} />}

              {/* Status actions */}
              {meeting.status !== 'cancelled' && meeting.status !== 'completed' && (
                <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #E8EEF4' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#8FA5BD', marginBottom: 10, textTransform: 'uppercase' }}>Actions</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {meeting.status !== 'confirmed' && (
                      <button onClick={function() { updateStatus('confirmed') }} style={{ padding: '7px 14px', borderRadius: 8, border: '1px solid #22C55E', background: 'rgba(34,197,94,.08)', color: '#22C55E', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>✓ Confirm</button>
                    )}
                    <button onClick={function() { updateStatus('completed') }} style={{ padding: '7px 14px', borderRadius: 8, border: '1px solid #64748B', background: 'rgba(100,116,139,.08)', color: '#64748B', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>✓ Complete</button>
                    <button onClick={function() { updateStatus('cancelled') }} style={{ padding: '7px 14px', borderRadius: 8, border: '1px solid #EF4444', background: 'rgba(239,68,68,.08)', color: '#EF4444', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>✕ Cancel</button>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === 'notes' && (
            <div>
              {/* Add note */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E8EEF4', borderRadius: 10, padding: '14px 16px', marginBottom: 20 }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <select value={noteType} onChange={function(e) { setNoteType(e.target.value) }} style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid #E8EEF4', fontSize: 12, background: '#fff' }}>
                    {Object.keys(NOTE_TYPE_COLORS).map(function(t) {
                      return <option key={t} value={t}>{t.replace('_', ' ')}</option>
                    })}
                  </select>
                </div>
                <textarea value={noteContent} onChange={function(e) { setNoteContent(e.target.value) }}
                  placeholder="Add a note, action item, or decision…" rows={3}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, border: '1px solid #E8EEF4', resize: 'vertical', boxSizing: 'border-box', outline: 'none' }} />
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                  <button onClick={addNote} disabled={savingNote || !noteContent.trim()} style={{
                    padding: '7px 16px', borderRadius: 8, border: 'none',
                    background: savingNote || !noteContent.trim() ? '#CBD5E1' : '#0ABFCA',
                    color: '#fff', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                  }}>
                    {savingNote ? 'Saving…' : 'Add Note'}
                  </button>
                </div>
              </div>

              {/* Notes list */}
              {(meeting.notes || []).slice().reverse().map(function(n) {
                var c = NOTE_TYPE_COLORS[n.note_type] || '#64748B'
                return (
                  <div key={n.id} style={{ borderLeft: '3px solid ' + c, paddingLeft: 14, marginBottom: 14 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: c, background: c + '15', borderRadius: 20, padding: '1px 8px' }}>{n.note_type.replace('_', ' ')}</span>
                      <span style={{ fontSize: 11, color: '#8FA5BD' }}>{n.created_by} · {new Date(n.created_at).toLocaleString('en-IN')}</span>
                    </div>
                    <div style={{ fontSize: 13, color: '#0D1F35', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{n.content}</div>
                  </div>
                )
              })}
              {!meeting.notes?.length && (
                <div style={{ color: '#8FA5BD', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>No notes yet</div>
              )}
            </div>
          )}

          {tab === 'participants' && (
            <div>
              {(meeting.participants || []).map(function(p) {
                var rsvpColor = p.rsvp_status === 'accepted' ? '#22C55E' : p.rsvp_status === 'declined' ? '#EF4444' : p.rsvp_status === 'tentative' ? '#E9930D' : '#8FA5BD'
                return (
                  <div key={p.id} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '12px 0', borderBottom: '1px solid #F1F5F9',
                  }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: '50%',
                      background: 'linear-gradient(135deg,#0ABFCA,#088F99)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 14, fontWeight: 700, color: '#fff', flexShrink: 0,
                    }}>
                      {(p.name || p.email)[0].toUpperCase()}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, color: '#0D1F35', fontSize: 13 }}>{p.name || p.email}</div>
                      {p.name && <div style={{ fontSize: 11, color: '#8FA5BD' }}>{p.email}</div>}
                      <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 2 }}>{p.role}</div>
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: rsvpColor, background: rsvpColor + '15', borderRadius: 20, padding: '2px 10px' }}>
                      {p.rsvp_status}
                    </div>
                  </div>
                )
              })}
              {!meeting.participants?.length && (
                <div style={{ color: '#8FA5BD', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>No participants added</div>
              )}
            </div>
          )}

          {tab === 'history' && (
            <div>
              {(meeting.status_history || []).slice().reverse().map(function(h) {
                return (
                  <div key={h.id} style={{ padding: '10px 0', borderBottom: '1px solid #F1F5F9' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: '#8FA5BD' }}>{h.old_status || '—'}</span>
                      <span style={{ color: '#8FA5BD' }}>→</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: '#0ABFCA' }}>{h.new_status}</span>
                    </div>
                    <div style={{ fontSize: 11, color: '#8FA5BD' }}>
                      by {h.changed_by} · {new Date(h.changed_at).toLocaleString('en-IN')}
                    </div>
                    {h.reason && <div style={{ fontSize: 12, color: '#4B6080', marginTop: 4 }}>{h.reason}</div>}
                  </div>
                )
              })}
              {!meeting.status_history?.length && (
                <div style={{ color: '#8FA5BD', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>No history</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#8FA5BD', marginBottom: 4, textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 13, color: '#0D1F35' }}>{value}</div>
    </div>
  )
}

// ── Calendar Grid ─────────────────────────────────────────────────────────────

function CalendarGrid({ year, month, events, onDayClick, onEventClick }) {
  var today = toISO(new Date())
  var weeks = calendarWeeks(year, month)
  var eventMap = {}
  events.forEach(function(e) {
    var d = e.start_at.slice(0, 10)
    if (!eventMap[d]) eventMap[d] = []
    eventMap[d].push(e)
  })

  return (
    <div style={{ background: '#fff', border: '1px solid #E8EEF4', borderRadius: 14, overflow: 'hidden' }}>
      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', borderBottom: '1px solid #E8EEF4' }}>
        {DAYS.map(function(d) {
          return (
            <div key={d} style={{ padding: '10px 0', textAlign: 'center', fontSize: 11, fontWeight: 700, color: '#8FA5BD', background: '#F8FAFC' }}>
              {d}
            </div>
          )
        })}
      </div>
      {/* Weeks */}
      {weeks.map(function(week, wi) {
        return (
          <div key={wi} style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)' }}>
            {week.map(function(d, di) {
              var diso = toISO(d)
              var isCurrentMonth = d.getMonth() === month
              var isToday = diso === today
              var dayEvents = eventMap[diso] || []
              return (
                <div
                  key={di}
                  onClick={function() { onDayClick(diso) }}
                  style={{
                    minHeight: 80, padding: '6px', cursor: 'pointer',
                    borderRight: di < 6 ? '1px solid #F1F5F9' : 'none',
                    borderBottom: wi < weeks.length - 1 ? '1px solid #F1F5F9' : 'none',
                    background: isToday ? 'rgba(10,191,202,.04)' : '#fff',
                    opacity: isCurrentMonth ? 1 : 0.4,
                    transition: 'background .1s',
                  }}
                  onMouseEnter={function(e) { e.currentTarget.style.background = 'rgba(10,191,202,.07)' }}
                  onMouseLeave={function(e) { e.currentTarget.style.background = isToday ? 'rgba(10,191,202,.04)' : '#fff' }}
                >
                  <div style={{
                    width: 24, height: 24, borderRadius: '50%',
                    background: isToday ? '#0ABFCA' : 'transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: isToday ? 700 : 500,
                    color: isToday ? '#fff' : isCurrentMonth ? '#0D1F35' : '#8FA5BD',
                    marginBottom: 4,
                  }}>{d.getDate()}</div>
                  {dayEvents.slice(0, 3).map(function(ev) {
                    var ts = TYPE_STYLE[ev.meeting_type] || { background: '#F1F5F9', color: '#64748B' }
                    return (
                      <div key={ev.id} onClick={function(e) { e.stopPropagation(); onEventClick(ev) }} style={{
                        ...ts, fontSize: 10, fontWeight: 600, borderRadius: 4,
                        padding: '2px 5px', marginBottom: 2, overflow: 'hidden',
                        textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        cursor: 'pointer',
                      }}>
                        {ev.start_at.slice(11, 16)} {ev.title}
                      </div>
                    )
                  })}
                  {dayEvents.length > 3 && (
                    <div style={{ fontSize: 10, color: '#8FA5BD' }}>+{dayEvents.length - 3} more</div>
                  )}
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function MeetingCalendar() {
  var { token } = useAuthStore()
  var now = new Date()
  var [year, setYear]   = useState(now.getFullYear())
  var [month, setMonth] = useState(now.getMonth())
  var [view, setView]   = useState('month')   // month | list

  var [meetings, setMeetings]       = useState([])
  var [calEvents, setCalEvents]     = useState([])
  var [loading, setLoading]         = useState(true)
  var [selectedMeeting, setSelectedMeeting] = useState(null)
  var [showCreate, setShowCreate]   = useState(false)
  var [defaultDate, setDefaultDate] = useState(null)
  var [statusFilter, setStatusFilter] = useState('')

  var monthStart = new Date(year, month, 1)
  var monthEnd   = new Date(year, month + 1, 0, 23, 59, 59)

  function loadCalendar() {
    var sf = monthStart.toISOString()
    var st = monthEnd.toISOString()
    setLoading(true)
    Promise.all([
      api(token, '/meetings/calendar?start_from=' + sf + '&start_to=' + st),
      api(token, '/meetings?start_from=' + sf + '&start_to=' + st + '&page_size=100' + (statusFilter ? '&status=' + statusFilter : '')),
    ])
      .then(function([cal, list]) {
        setCalEvents(cal)
        setMeetings(list.items || [])
      })
      .catch(function() {})
      .finally(function() { setLoading(false) })
  }

  useEffect(function() { loadCalendar() }, [year, month, statusFilter])

  function prevMonth() {
    if (month === 0) { setMonth(11); setYear(function(y) { return y - 1 }) }
    else setMonth(function(m) { return m - 1 })
  }
  function nextMonth() {
    if (month === 11) { setMonth(0); setYear(function(y) { return y + 1 }) }
    else setMonth(function(m) { return m + 1 })
  }

  function handleDayClick(dateStr) {
    setDefaultDate(dateStr)
    setShowCreate(true)
  }

  function handleEventClick(ev) {
    // Load full meeting detail
    api(token, '/meetings/' + ev.id)
      .then(function(m) { setSelectedMeeting(m) })
      .catch(function() {})
  }

  function onCreated(m) {
    setShowCreate(false)
    loadCalendar()
  }

  function onUpdated(m) {
    setSelectedMeeting(m)
    loadCalendar()
  }

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: '#0D1F35', margin: 0 }}>Meeting Calendar</h1>
          <div style={{ fontSize: 13, color: '#8FA5BD', marginTop: 2 }}>Schedule and manage meetings with your team and partners</div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Status filter */}
          <select value={statusFilter} onChange={function(e) { setStatusFilter(e.target.value) }} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #E8EEF4', fontSize: 13, background: '#fff' }}>
            <option value="">All Statuses</option>
            {['scheduled','confirmed','cancelled','completed','rescheduled'].map(function(s) {
              return <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>
            })}
          </select>
          {/* View toggle */}
          <div style={{ display: 'flex', border: '1px solid #E8EEF4', borderRadius: 8, overflow: 'hidden' }}>
            {[['month', '📅'], ['list', '📋']].map(function([k, icon]) {
              return (
                <button key={k} onClick={function() { setView(k) }} style={{
                  padding: '8px 14px', border: 'none', cursor: 'pointer', fontSize: 14,
                  background: view === k ? '#0ABFCA' : '#fff',
                  color: view === k ? '#fff' : '#8FA5BD',
                }}>{icon}</button>
              )
            })}
          </div>
          <button onClick={function() { setDefaultDate(toISO(new Date())); setShowCreate(true) }} style={{
            padding: '8px 18px', borderRadius: 8, border: 'none',
            background: '#0ABFCA', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer',
          }}>+ New Meeting</button>
        </div>
      </div>

      {/* Month nav */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
        <button onClick={prevMonth} style={{ width: 34, height: 34, borderRadius: 8, border: '1px solid #E8EEF4', background: '#fff', fontSize: 16, cursor: 'pointer' }}>‹</button>
        <div style={{ fontSize: 18, fontWeight: 800, color: '#0D1F35', minWidth: 180, textAlign: 'center' }}>
          {MONTHS[month]} {year}
        </div>
        <button onClick={nextMonth} style={{ width: 34, height: 34, borderRadius: 8, border: '1px solid #E8EEF4', background: '#fff', fontSize: 16, cursor: 'pointer' }}>›</button>
        <button onClick={function() { var n = new Date(); setYear(n.getFullYear()); setMonth(n.getMonth()) }} style={{
          padding: '6px 14px', borderRadius: 8, border: '1px solid #E8EEF4', background: '#fff',
          fontSize: 12, fontWeight: 600, color: '#4B6080', cursor: 'pointer',
        }}>Today</button>
        {loading && <span style={{ color: '#8FA5BD', fontSize: 13 }}>Loading…</span>}
      </div>

      {/* Calendar grid */}
      {view === 'month' && (
        <CalendarGrid year={year} month={month} events={calEvents} onDayClick={handleDayClick} onEventClick={handleEventClick} />
      )}

      {/* List view */}
      {view === 'list' && (
        <div>
          {meetings.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#8FA5BD' }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>📆</div>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>No meetings this month</div>
              <div style={{ fontSize: 13, marginBottom: 16 }}>Click "New Meeting" to schedule one.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {meetings.map(function(m) {
                var ts = TYPE_STYLE[m.meeting_type] || { background: '#F1F5F9', color: '#64748B' }
                var ss = STATUS_STYLE[m.status]     || { background: '#F1F5F9', color: '#64748B' }
                return (
                  <div key={m.id} onClick={function() { handleEventClick(m) }} style={{
                    background: '#fff', border: '1px solid #E8EEF4', borderRadius: 12, padding: '14px 20px',
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 16,
                    transition: 'border-color .15s',
                  }}
                    onMouseEnter={function(e) { e.currentTarget.style.borderColor = '#0ABFCA' }}
                    onMouseLeave={function(e) { e.currentTarget.style.borderColor = '#E8EEF4' }}
                  >
                    <div style={{ textAlign: 'center', minWidth: 48 }}>
                      <div style={{ fontSize: 11, color: '#8FA5BD', fontWeight: 700 }}>
                        {new Date(m.start_at).toLocaleDateString('en-IN', { weekday: 'short' }).toUpperCase()}
                      </div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: '#0D1F35', lineHeight: 1 }}>
                        {new Date(m.start_at).getDate()}
                      </div>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, color: '#0D1F35', fontSize: 14, marginBottom: 4 }}>{m.title}</div>
                      <div style={{ fontSize: 12, color: '#8FA5BD' }}>
                        {new Date(m.start_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                        {' – '}
                        {new Date(m.end_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                        {m.location && ' · ' + m.location}
                        {m.platform && ' · ' + PLATFORM_ICONS[m.platform] + ' ' + m.platform}
                      </div>
                      <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 4 }}>
                        {m.participant_count || 0} participants
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                      <Badge style={ts} label={m.meeting_type} />
                      <Badge style={ss} label={m.status} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {showCreate && (
        <CreateMeetingModal token={token} defaultDate={defaultDate} onCreated={onCreated} onClose={function() { setShowCreate(false) }} />
      )}
      {selectedMeeting && (
        <MeetingPanel meeting={selectedMeeting} token={token} onUpdated={onUpdated} onClose={function() { setSelectedMeeting(null) }} />
      )}
    </div>
  )
}
