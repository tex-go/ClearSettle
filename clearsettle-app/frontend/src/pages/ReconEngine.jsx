import React, { useState, useEffect, useRef, useCallback } from 'react'
import { AnimatePresence } from 'framer-motion'
import useAuthStore from '../store/authStore'
import { ReconciliationPipeline } from '../components/recon/ReconciliationPipeline'

// ── constants ─────────────────────────────────────────────────────────────────
const FILE_TYPES = [
  { value: 'settlement',       label: 'Settlement Report',        icon: '📄', desc: 'Main payout & deduction summary' },
  { value: 'invoice',          label: 'Invoice Report',           icon: '🧾', desc: 'Expected receivable amounts' },
  { value: 'chargeback',       label: 'Chargeback / Deductions',  icon: '⚠️', desc: 'Operational penalty analysis' },
  { value: 'payment_advice',   label: 'Payment / Remittance',     icon: '🏦', desc: 'Actual bank payment validation' },
  { value: 'po',               label: 'Purchase Orders (PO)',      icon: '📋', desc: 'Base order commitment' },
  { value: 'asn',              label: 'ASN (Shipment Notice)',     icon: '🚚', desc: 'Shipment declaration validation' },
  { value: 'pod',              label: 'Proof of Delivery (POD)',   icon: '✅', desc: 'Physical delivery proof' },
  { value: 'receiving',        label: 'Receiving Report',         icon: '📦', desc: 'Warehouse receiving validation' },
  { value: 'otif',             label: 'OTIF Compliance',          icon: '⏱️', desc: 'SLA penalty reports' },
  { value: 'return',           label: 'Returns Report',           icon: '↩️', desc: 'Customer return deductions' },
  { value: 'damage',           label: 'Damage / Unsellable',      icon: '🔴', desc: 'Inventory loss deductions' },
  { value: 'shortage',         label: 'Shortage Claims',          icon: '📉', desc: 'Missing inventory claims' },
  { value: 'dispute_recovery', label: 'Dispute Recovery',         icon: '⚖️', desc: 'Track recovered leakage' },
  { value: 'sku_master',       label: 'SKU Master',               icon: '🏷️', desc: 'Cross-system entity mapping' },
]

const LEAKAGE_TYPES = {
  SHORT:            { label: 'Shortage Leakage',         color: '#E8344A', icon: '📉' },
  DUPLICATE:        { label: 'Duplicate Deductions',     color: '#E9930D', icon: '🔁' },
  OTIF:             { label: 'Invalid OTIF Penalty',     color: '#F59E0B', icon: '⏱️' },
  ACCRUAL:          { label: 'Accrual Mismatch',         color: '#8B5CF6', icon: '🔄' },
  COOP:             { label: 'Unauthorized Co-Op',       color: '#EC4899', icon: '🤝' },
  RETURN:           { label: 'Return Leakage',           color: '#06B6D4', icon: '↩️' },
  DAMAGE:           { label: 'Damage Overstatement',     color: '#F97316', icon: '🔴' },
  TIMING:           { label: 'Payment Timing',           color: '#10B981', icon: '⏰' },
  TAX:              { label: 'Tax Mismatch',             color: '#3B82F6', icon: '🧾' },
  DISPUTE_RECOVERY: { label: 'Unrecovered Disputes',    color: '#EF4444', icon: '⚖️' },
}

const SEVERITY_COLORS = {
  critical: { bg: 'rgba(232,52,74,.15)', color: '#E8344A', border: 'rgba(232,52,74,.3)' },
  warning:  { bg: 'rgba(233,147,13,.15)', color: '#E9930D', border: 'rgba(233,147,13,.3)' },
  info:     { bg: 'rgba(10,191,202,.15)', color: '#0ABFCA', border: 'rgba(10,191,202,.3)' },
}

const STATUS_COLORS = {
  open:     { bg: 'rgba(232,52,74,.12)', color: '#E8344A' },
  disputed: { bg: 'rgba(233,147,13,.12)', color: '#E9930D' },
  resolved: { bg: 'rgba(16,185,129,.12)', color: '#10B981' },
  waived:   { bg: 'rgba(139,92,246,.12)', color: '#8B5CF6' },
}

const JOB_STATUS_COLORS = {
  draft:     { bg: 'rgba(75,96,128,.15)', color: '#8FA5BD' },
  queued:    { bg: 'rgba(10,191,202,.15)', color: '#0ABFCA' },
  running:   { bg: 'rgba(233,147,13,.15)', color: '#E9930D' },
  completed: { bg: 'rgba(16,185,129,.15)', color: '#10B981' },
  failed:    { bg: 'rgba(232,52,74,.15)', color: '#E8344A' },
}

const fmt = n => n == null ? '—' : `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
const fmtPct = n => n == null ? '—' : `${Number(n).toFixed(2)}%`

function api(token, path, opts = {}) {
  return fetch(`/api${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...(opts.headers || {}) },
  }).then(r => r.json())
}

// ── mini components ───────────────────────────────────────────────────────────
function Badge({ type, label, style = {} }) {
  const s = SEVERITY_COLORS[type] || SEVERITY_COLORS.info
  return (
    <span style={{
      ...s, borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 700,
      border: `1px solid ${s.border || 'transparent'}`, ...style,
    }}>{label || type}</span>
  )
}

function StatusBadge({ status, colors = STATUS_COLORS }) {
  const s = colors[status] || colors.open || { bg: '#eee', color: '#333' }
  return (
    <span style={{
      ...s, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700,
    }}>{status}</span>
  )
}

function StatCard({ label, value, sub, color = '#0ABFCA', onClick }) {
  return (
    <div onClick={onClick} style={{
      background: '#fff', borderRadius: 12, padding: '20px 24px',
      border: '1px solid #E8EFF6', flex: 1, minWidth: 160,
      cursor: onClick ? 'pointer' : 'default',
      transition: 'box-shadow .15s',
    }}
    onMouseEnter={e => onClick && (e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,.08)')}
    onMouseLeave={e => onClick && (e.currentTarget.style.boxShadow = 'none')}
    >
      <div style={{ fontSize: 11, color: '#8FA5BD', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 800, color }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function Spinner() {
  return <div style={{ width: 20, height: 20, border: '3px solid rgba(10,191,202,.2)', borderTop: '3px solid #0ABFCA', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
}

// ── Upload Tab ────────────────────────────────────────────────────────────────
function UploadTab({ token, files, onRefresh }) {
  const [dragging, setDragging]   = useState(false)
  const [fileType, setFileType]   = useState('settlement')
  const [uploading, setUploading] = useState(false)
  const [error, setError]         = useState(null)
  const inputRef = useRef()

  async function handleUpload(file) {
    if (!file) return
    setUploading(true)
    setError(null)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('file_type', fileType)
    try {
      const res = await fetch('/api/recon-engine/files/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      })
      if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed')
      onRefresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }

  async function deleteFile(id) {
    if (!window.confirm('Delete this file?')) return
    await fetch(`/api/recon-engine/files/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    onRefresh()
  }

  return (
    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
      {/* Upload card */}
      <div style={{ flex: '0 0 340px', background: '#fff', borderRadius: 14, padding: 24, border: '1px solid #E8EFF6' }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, color: '#0D1F35', fontWeight: 700 }}>Upload File</h3>

        <div style={{ marginBottom: 14 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 6 }}>File Type</label>
          <select value={fileType} onChange={e => setFileType(e.target.value)} style={{
            width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1DDE8',
            fontSize: 13, color: '#0D1F35', background: '#F7FAFC',
          }}>
            {FILE_TYPES.map(ft => (
              <option key={ft.value} value={ft.value}>{ft.icon} {ft.label}</option>
            ))}
          </select>
          <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 4 }}>
            {FILE_TYPES.find(f => f.value === fileType)?.desc}
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); handleUpload(e.dataTransfer.files[0]) }}
          onClick={() => inputRef.current?.click()}
          style={{
            border: `2px dashed ${dragging ? '#0ABFCA' : '#D1DDE8'}`,
            borderRadius: 12, padding: '32px 20px', textAlign: 'center',
            cursor: 'pointer', background: dragging ? 'rgba(10,191,202,.04)' : '#F7FAFC',
            transition: 'all .15s', marginBottom: 12,
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 8 }}>📁</div>
          <div style={{ fontSize: 13, color: '#4B6080', fontWeight: 500 }}>
            {uploading ? 'Uploading…' : 'Drop file here or click to browse'}
          </div>
          <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 4 }}>CSV, XLSX, TXT supported</div>
          <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls,.txt" style={{ display: 'none' }}
            onChange={e => handleUpload(e.target.files[0])} />
        </div>

        {error && <div style={{ color: '#E8344A', fontSize: 12, marginBottom: 8 }}>{error}</div>}

        {/* Supported types grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 4 }}>
          {FILE_TYPES.map(ft => (
            <div key={ft.value} onClick={() => setFileType(ft.value)} style={{
              padding: '6px 10px', borderRadius: 8, cursor: 'pointer',
              background: fileType === ft.value ? 'rgba(10,191,202,.12)' : '#F7FAFC',
              border: `1px solid ${fileType === ft.value ? '#0ABFCA' : '#E8EFF6'}`,
              fontSize: 11, color: fileType === ft.value ? '#0ABFCA' : '#4B6080',
            }}>
              {ft.icon} {ft.label}
            </div>
          ))}
        </div>
      </div>

      {/* File list */}
      <div style={{ flex: 1, minWidth: 300 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, color: '#0D1F35', fontWeight: 700 }}>
          Uploaded Files ({files.length})
        </h3>
        {files.length === 0 ? (
          <div style={{ background: '#fff', borderRadius: 12, padding: 40, textAlign: 'center', border: '1px solid #E8EFF6', color: '#8FA5BD', fontSize: 13 }}>
            No files uploaded yet
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {files.map(f => {
              const ft = FILE_TYPES.find(t => t.value === f.file_type)
              return (
                <div key={f.id} style={{
                  background: '#fff', borderRadius: 10, padding: '12px 16px',
                  border: '1px solid #E8EFF6', display: 'flex', alignItems: 'center', gap: 12,
                }}>
                  <div style={{ fontSize: 22, flexShrink: 0 }}>{ft?.icon || '📄'}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#0D1F35', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.original_name}
                    </div>
                    <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 2 }}>
                      {ft?.label} · {f.row_count != null ? `${f.row_count} rows` : 'parsing…'}
                      {f.file_size_bytes && ` · ${(f.file_size_bytes / 1024).toFixed(1)} KB`}
                    </div>
                  </div>
                  <StatusBadge status={f.status} colors={{ processed: { bg: 'rgba(16,185,129,.12)', color: '#10B981' }, pending: { bg: 'rgba(75,96,128,.12)', color: '#8FA5BD' }, failed: { bg: 'rgba(232,52,74,.12)', color: '#E8344A' } }} />
                  <button onClick={() => deleteFile(f.id)} style={{
                    background: 'rgba(232,52,74,.1)', color: '#E8344A', border: 'none',
                    borderRadius: 6, padding: '4px 8px', fontSize: 12, cursor: 'pointer',
                  }}>✕</button>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Jobs Tab ──────────────────────────────────────────────────────────────────
function JobsTab({ token, files, jobs, onRefresh, onSelectJob, onRunJob }) {
  const [creating, setCreating] = useState(false)
  const [running, setRunning]   = useState(null)
  const [form, setForm]         = useState({ name: '', description: '', period_start: '', period_end: '', platform: '', currency: 'INR', file_ids: [] })

  function toggleFile(id) {
    setForm(prev => ({
      ...prev,
      file_ids: prev.file_ids.includes(id) ? prev.file_ids.filter(i => i !== id) : [...prev.file_ids, id],
    }))
  }

  async function createJob() {
    if (!form.name) return
    setCreating(true)
    const body = { ...form }
    if (!body.period_start) delete body.period_start
    if (!body.period_end)   delete body.period_end
    if (!body.platform)     delete body.platform
    await api(token, '/recon-engine/jobs', { method: 'POST', body: JSON.stringify(body) })
    setCreating(false)
    setForm({ name: '', description: '', period_start: '', period_end: '', platform: '', currency: 'INR', file_ids: [] })
    onRefresh()
  }

  async function runJob(jobId, jobName) {
    setRunning(jobId)
    try {
      // Queue the job — returns immediately with {"status": "queued"}
      await api(token, `/recon-engine/jobs/${jobId}/run`, { method: 'POST' })
      // Open the live pipeline visualization overlay
      onRunJob(jobId, jobName)
    } catch (e) {
      // If already running or other conflict, just refresh
    } finally {
      setRunning(null)
    }
  }

  const inputStyle = { width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 13, color: '#0D1F35', background: '#F7FAFC', boxSizing: 'border-box' }

  return (
    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
      {/* Create job form */}
      <div style={{ flex: '0 0 340px', background: '#fff', borderRadius: 14, padding: 24, border: '1px solid #E8EFF6' }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, color: '#0D1F35', fontWeight: 700 }}>Create Reconciliation Job</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Job Name *</label>
            <input style={inputStyle} placeholder="e.g. Q1 2026 Settlement Recon" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Period Start</label>
              <input type="date" style={inputStyle} value={form.period_start} onChange={e => setForm(p => ({ ...p, period_start: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Period End</label>
              <input type="date" style={inputStyle} value={form.period_end} onChange={e => setForm(p => ({ ...p, period_end: e.target.value }))} />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Platform</label>
              <select style={inputStyle} value={form.platform} onChange={e => setForm(p => ({ ...p, platform: e.target.value }))}>
                <option value="">Generic</option>
                <option value="amazon">Amazon</option>
                <option value="flipkart">Flipkart</option>
                <option value="meesho">Meesho</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 4 }}>Currency</label>
              <select style={inputStyle} value={form.currency} onChange={e => setForm(p => ({ ...p, currency: e.target.value }))}>
                <option value="INR">INR</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>

          {/* File selector */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', display: 'block', marginBottom: 6 }}>
              Select Files ({form.file_ids.length} selected)
            </label>
            <div style={{ maxHeight: 200, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {files.length === 0 && <div style={{ fontSize: 12, color: '#8FA5BD' }}>Upload files first</div>}
              {files.map(f => {
                const ft = FILE_TYPES.find(t => t.value === f.file_type)
                const selected = form.file_ids.includes(f.id)
                return (
                  <div key={f.id} onClick={() => toggleFile(f.id)} style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
                    borderRadius: 8, cursor: 'pointer',
                    background: selected ? 'rgba(10,191,202,.1)' : '#F7FAFC',
                    border: `1px solid ${selected ? '#0ABFCA' : '#E8EFF6'}`,
                  }}>
                    <div style={{ width: 14, height: 14, borderRadius: 3, background: selected ? '#0ABFCA' : '#D1DDE8', flexShrink: 0 }} />
                    <span style={{ fontSize: 12 }}>{ft?.icon}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, color: '#0D1F35', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.original_name}</div>
                      <div style={{ fontSize: 10, color: '#8FA5BD' }}>{ft?.label}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <button onClick={createJob} disabled={!form.name || creating} style={{
            width: '100%', padding: 10, borderRadius: 8, fontWeight: 700, fontSize: 13,
            background: form.name ? 'linear-gradient(135deg,#0ABFCA,#088F99)' : '#E8EFF6',
            color: form.name ? '#fff' : '#8FA5BD', border: 'none', cursor: form.name ? 'pointer' : 'not-allowed',
          }}>
            {creating ? 'Creating…' : '+ Create Job'}
          </button>
        </div>
      </div>

      {/* Jobs list */}
      <div style={{ flex: 1, minWidth: 300 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, color: '#0D1F35', fontWeight: 700 }}>
          Reconciliation Jobs ({jobs.length})
        </h3>
        {jobs.length === 0 ? (
          <div style={{ background: '#fff', borderRadius: 12, padding: 40, textAlign: 'center', border: '1px solid #E8EFF6', color: '#8FA5BD', fontSize: 13 }}>
            No jobs yet — create one to start reconciling
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {jobs.map(job => {
              const sc = JOB_STATUS_COLORS[job.status] || JOB_STATUS_COLORS.draft
              return (
                <div key={job.id} style={{
                  background: '#fff', borderRadius: 12, padding: '16px 20px',
                  border: '1px solid #E8EFF6',
                  cursor: job.status === 'completed' ? 'pointer' : 'default',
                  transition: 'box-shadow .15s',
                }}
                onClick={() => job.status === 'completed' && onSelectJob(job.id)}
                onMouseEnter={e => job.status === 'completed' && (e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,.06)')}
                onMouseLeave={e => (e.currentTarget.style.boxShadow = 'none')}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#0D1F35' }}>{job.name}</div>
                        <span style={{ ...sc, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700 }}>{job.status}</span>
                      </div>
                      <div style={{ fontSize: 12, color: '#8FA5BD' }}>
                        {job.period_start && job.period_end && `${job.period_start} → ${job.period_end} · `}
                        {job.platform || 'Generic'} · {job.currency}
                        {job.created_at && ` · Created ${new Date(job.created_at).toLocaleDateString('en-IN')}`}
                      </div>
                    </div>
                    {job.status === 'completed' && (
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#E8344A' }}>{fmt(job.total_leakage)}</div>
                        <div style={{ fontSize: 10, color: '#8FA5BD' }}>total leakage</div>
                      </div>
                    )}
                  </div>

                  {job.status === 'completed' && (
                    <div style={{ display: 'flex', gap: 20, marginTop: 12, paddingTop: 12, borderTop: '1px solid #F1F5F9' }}>
                      <div>
                        <div style={{ fontSize: 11, color: '#8FA5BD' }}>Expected</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#0D1F35' }}>{fmt(job.expected_payout)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#8FA5BD' }}>Actual</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#0D1F35' }}>{fmt(job.actual_payout)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#8FA5BD' }}>Variance</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: job.variance_amount > 0 ? '#E8344A' : '#10B981' }}>{fmt(job.variance_amount)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#8FA5BD' }}>Leakage Events</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#0D1F35' }}>{job.leakage_count || 0}</div>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                    {job.status === 'draft' && (
                      <button onClick={e => { e.stopPropagation(); runJob(job.id, job.name) }} disabled={running === job.id} style={{
                        padding: '6px 14px', borderRadius: 7, background: 'linear-gradient(135deg,#0ABFCA,#088F99)',
                        color: '#fff', border: 'none', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: 6,
                      }}>
                        {running === job.id ? <Spinner /> : '▶'} Run Engine
                      </button>
                    )}
                    {job.status === 'failed' && (
                      <button onClick={e => { e.stopPropagation(); runJob(job.id, job.name) }} style={{
                        padding: '6px 14px', borderRadius: 7, background: 'rgba(232,52,74,.1)',
                        color: '#E8344A', border: '1px solid rgba(232,52,74,.2)', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                      }}>↺ Retry</button>
                    )}
                    {job.status === 'completed' && (
                      <button onClick={e => { e.stopPropagation(); onSelectJob(job.id) }} style={{
                        padding: '6px 14px', borderRadius: 7, background: 'rgba(10,191,202,.1)',
                        color: '#0ABFCA', border: '1px solid rgba(10,191,202,.2)', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                      }}>View Report →</button>
                    )}
                    {job.error_message && (
                      <div style={{ fontSize: 11, color: '#E8344A', padding: '6px 0' }}>{job.error_message}</div>
                    )}
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

// ── Leakage Tab ───────────────────────────────────────────────────────────────
function LeakageTab({ token, jobs }) {
  const [selectedJobId, setSelectedJobId] = useState(null)
  const [leakageData, setLeakageData]     = useState(null)
  const [jobDetail, setJobDetail]         = useState(null)
  const [loading, setLoading]             = useState(false)
  const [filterType, setFilterType]       = useState('')
  const [filterSev, setFilterSev]         = useState('')
  const [filterStatus, setFilterStatus]   = useState('')
  const [expandedEvent, setExpandedEvent] = useState(null)
  const [patching, setPatching]           = useState(null)

  const completedJobs = jobs.filter(j => j.status === 'completed')

  useEffect(function() {
    if (!selectedJobId) return
    setLoading(true)
    Promise.all([
      api(token, `/recon-engine/jobs/${selectedJobId}`),
      api(token, `/recon-engine/jobs/${selectedJobId}/leakage?limit=200`),
    ]).then(([jd, ld]) => {
      setJobDetail(jd)
      setLeakageData(ld)
    }).finally(() => setLoading(false))
  }, [selectedJobId])

  async function updateStatus(eventId, newStatus) {
    setPatching(eventId)
    await api(token, `/recon-engine/leakage/${eventId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    })
    const ld = await api(token, `/recon-engine/jobs/${selectedJobId}/leakage?limit=200`)
    setLeakageData(ld)
    setPatching(null)
  }

  const filteredEvents = (leakageData?.items || []).filter(e => {
    if (filterType && e.leakage_type !== filterType) return false
    if (filterSev  && e.severity       !== filterSev)  return false
    if (filterStatus && e.status       !== filterStatus) return false
    return true
  })

  const leakageByType = {}
  ;(leakageData?.items || []).forEach(e => {
    leakageByType[e.leakage_type] = (leakageByType[e.leakage_type] || 0) + (e.amount || 0)
  })

  if (completedJobs.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 60, color: '#8FA5BD' }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>📊</div>
        <div style={{ fontSize: 15, fontWeight: 600 }}>No completed jobs yet</div>
        <div style={{ fontSize: 13, marginTop: 4 }}>Create and run a reconciliation job to see leakage analysis</div>
      </div>
    )
  }

  return (
    <div>
      {/* Job selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <label style={{ fontSize: 12, fontWeight: 600, color: '#4B6080' }}>Select Job:</label>
        <select value={selectedJobId || ''} onChange={e => setSelectedJobId(e.target.value || null)} style={{
          padding: '8px 12px', borderRadius: 8, border: '1px solid #D1DDE8',
          fontSize: 13, color: '#0D1F35', background: '#fff', minWidth: 240,
        }}>
          <option value="">-- Select a completed job --</option>
          {completedJobs.map(j => (
            <option key={j.id} value={j.id}>{j.name} ({j.period_start || 'No period'})</option>
          ))}
        </select>
        {loading && <Spinner />}
      </div>

      {!selectedJobId && <div style={{ background: '#fff', borderRadius: 12, padding: 40, textAlign: 'center', border: '1px solid #E8EFF6', color: '#8FA5BD' }}>Select a job above to view leakage analysis</div>}

      {selectedJobId && jobDetail && (
        <>
          {/* Payout summary row */}
          {jobDetail.fact && (
            <div style={{ background: 'linear-gradient(135deg,#0D1F35,#1A3355)', borderRadius: 14, padding: '20px 24px', marginBottom: 20, color: '#fff' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#0ABFCA', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '.06em' }}>
                Payout Reconciliation Summary
              </div>
              <div style={{ display: 'flex', gap: 30, flexWrap: 'wrap' }}>
                {[
                  ['Invoice Value', jobDetail.fact.total_invoice_value, '#fff'],
                  ['Expected Payout', jobDetail.fact.expected_payout, '#0ABFCA'],
                  ['Actual Payout', jobDetail.fact.actual_payout, '#fff'],
                  ['Variance', jobDetail.fact.variance_amount, jobDetail.fact.variance_amount > 0 ? '#E8344A' : '#10B981'],
                  ['Total Leakage', jobDetail.fact.total_leakage, '#E8344A'],
                  ['Disputable', jobDetail.fact.disputable_amount, '#E9930D'],
                ].map(([label, val, color]) => (
                  <div key={label}>
                    <div style={{ fontSize: 11, color: '#4B6080', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color }}>{fmt(val)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Leakage by type breakdown */}
          {Object.keys(leakageByType).length > 0 && (
            <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
              {Object.entries(leakageByType).sort((a, b) => b[1] - a[1]).map(([type, amount]) => {
                const info = LEAKAGE_TYPES[type] || { label: type, color: '#8FA5BD', icon: '⚠️' }
                return (
                  <div key={type} onClick={() => setFilterType(filterType === type ? '' : type)} style={{
                    background: '#fff', borderRadius: 10, padding: '10px 14px',
                    border: `2px solid ${filterType === type ? info.color : '#E8EFF6'}`,
                    cursor: 'pointer', minWidth: 130, transition: 'all .15s',
                  }}>
                    <div style={{ fontSize: 18, marginBottom: 4 }}>{info.icon}</div>
                    <div style={{ fontSize: 11, color: '#8FA5BD', fontWeight: 600 }}>{info.label}</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: info.color }}>{fmt(amount)}</div>
                    <div style={{ fontSize: 10, color: '#8FA5BD' }}>
                      {(leakageData?.items || []).filter(e => e.leakage_type === type).length} events
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Filters */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
            <select value={filterType} onChange={e => setFilterType(e.target.value)} style={{ padding: '7px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 12, color: '#0D1F35' }}>
              <option value="">All Types</option>
              {Object.entries(LEAKAGE_TYPES).map(([v, { label }]) => <option key={v} value={v}>{label}</option>)}
            </select>
            <select value={filterSev} onChange={e => setFilterSev(e.target.value)} style={{ padding: '7px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 12, color: '#0D1F35' }}>
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ padding: '7px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 12, color: '#0D1F35' }}>
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="disputed">Disputed</option>
              <option value="resolved">Resolved</option>
              <option value="waived">Waived</option>
            </select>
            <div style={{ fontSize: 12, color: '#8FA5BD', marginLeft: 'auto' }}>
              {filteredEvents.length} events · {fmt(filteredEvents.reduce((s, e) => s + (e.amount || 0), 0))}
            </div>
          </div>

          {/* Events list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {filteredEvents.length === 0 && (
              <div style={{ background: '#fff', borderRadius: 12, padding: 40, textAlign: 'center', border: '1px solid #E8EFF6', color: '#8FA5BD' }}>
                No leakage events found for current filters
              </div>
            )}
            {filteredEvents.map(ev => {
              const info = LEAKAGE_TYPES[ev.leakage_type] || { label: ev.leakage_type, color: '#8FA5BD', icon: '⚠️' }
              const sc   = SEVERITY_COLORS[ev.severity] || SEVERITY_COLORS.info
              const isOpen = expandedEvent === ev.id

              return (
                <div key={ev.id} style={{
                  background: '#fff', borderRadius: 12, border: `1px solid #E8EFF6`,
                  overflow: 'hidden', transition: 'box-shadow .15s',
                }}>
                  <div onClick={() => setExpandedEvent(isOpen ? null : ev.id)} style={{
                    padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 14,
                  }}>
                    <div style={{ fontSize: 22, flexShrink: 0 }}>{info.icon}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 4, alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: info.color }}>{info.label}</span>
                        <Badge type={ev.severity} label={ev.severity} />
                        <StatusBadge status={ev.status} />
                        {ev.is_disputable && <span style={{ background: 'rgba(16,185,129,.12)', color: '#10B981', borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>Disputable</span>}
                      </div>
                      <div style={{ fontSize: 13, color: '#4B6080', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ev.description}</div>
                      {(ev.po_number || ev.invoice_number || ev.sku) && (
                        <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 2 }}>
                          {ev.po_number && `PO: ${ev.po_number}`}
                          {ev.invoice_number && ` · INV: ${ev.invoice_number}`}
                          {ev.sku && ` · SKU: ${ev.sku}`}
                        </div>
                      )}
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                      <div style={{ fontSize: 18, fontWeight: 800, color: '#E8344A' }}>{fmt(ev.amount)}</div>
                      {ev.recovery_potential && <div style={{ fontSize: 11, color: '#10B981' }}>↑ {fmt(ev.recovery_potential)}</div>}
                    </div>
                    <div style={{ fontSize: 16, color: '#8FA5BD' }}>{isOpen ? '▲' : '▼'}</div>
                  </div>

                  {isOpen && (
                    <div style={{ padding: '0 18px 18px', borderTop: '1px solid #F1F5F9' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, paddingTop: 14 }}>
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', marginBottom: 6, textTransform: 'uppercase' }}>Root Cause</div>
                          <div style={{ fontSize: 13, color: '#0D1F35', lineHeight: 1.5 }}>{ev.root_cause || '—'}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', marginBottom: 6, textTransform: 'uppercase' }}>Recovery Recommendation</div>
                          <div style={{ fontSize: 13, color: '#0D1F35', lineHeight: 1.5 }}>{ev.recovery_recommendation || '—'}</div>
                        </div>
                      </div>

                      {ev.evidence_json && JSON.parse(ev.evidence_json).length > 0 && (
                        <div style={{ marginTop: 14 }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', marginBottom: 6, textTransform: 'uppercase' }}>Required Evidence</div>
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                            {JSON.parse(ev.evidence_json).map((e, i) => (
                              <span key={i} style={{ background: '#F1F5F9', color: '#4B6080', borderRadius: 6, padding: '4px 10px', fontSize: 12 }}>{e}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {['disputed', 'resolved', 'waived'].map(s => (
                          <button key={s} disabled={ev.status === s || patching === ev.id} onClick={() => updateStatus(ev.id, s)} style={{
                            padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 700, cursor: 'pointer', border: 'none',
                            ...STATUS_COLORS[s], opacity: ev.status === s ? 0.5 : 1,
                          }}>
                            {s.charAt(0).toUpperCase() + s.slice(1)}
                          </button>
                        ))}
                        {ev.status !== 'open' && (
                          <button disabled={patching === ev.id} onClick={() => updateStatus(ev.id, 'open')} style={{
                            padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 700, cursor: 'pointer', border: 'none',
                            background: '#F1F5F9', color: '#4B6080',
                          }}>Reopen</button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ── Deduction Codes Tab ───────────────────────────────────────────────────────
function DeductionCodesTab({ token }) {
  const [codes, setCodes] = useState([])
  const [filter, setFilter] = useState('')

  useEffect(function() {
    api(token, '/recon-engine/deduction-codes').then(r => setCodes(r.items || []))
  }, [])

  const CAT_COLORS = {
    fee: '#0ABFCA', penalty: '#E8344A', chargeback: '#E9930D',
    coop: '#8B5CF6', adjustment: '#10B981', tax: '#3B82F6',
    return: '#EC4899', shortage: '#F97316',
  }

  const filtered = codes.filter(c =>
    !filter || c.code.toLowerCase().includes(filter.toLowerCase()) || c.name.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <input
          placeholder="Search codes…"
          value={filter} onChange={e => setFilter(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 13, flex: 1, maxWidth: 300 }}
        />
        <div style={{ fontSize: 12, color: '#8FA5BD' }}>{filtered.length} codes</div>
      </div>

      <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E8EFF6', overflow: 'hidden' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr 100px 90px 80px', gap: 0, background: '#F7FAFC', padding: '10px 16px', borderBottom: '1px solid #E8EFF6' }}>
          {['Code', 'Name', 'Category', 'Severity', 'Dispute?'].map(h => (
            <div key={h} style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase', letterSpacing: '.04em' }}>{h}</div>
          ))}
        </div>
        {filtered.map((c, i) => (
          <div key={c.id} style={{
            display: 'grid', gridTemplateColumns: '90px 1fr 100px 90px 80px',
            padding: '12px 16px', borderBottom: i < filtered.length - 1 ? '1px solid #F1F5F9' : 'none',
            alignItems: 'center',
          }}>
            <div style={{ fontSize: 12, fontWeight: 700, fontFamily: 'monospace', color: '#0D1F35' }}>{c.code}</div>
            <div>
              <div style={{ fontSize: 13, color: '#0D1F35', fontWeight: 500 }}>{c.name}</div>
              <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 2 }}>{c.description}</div>
            </div>
            <div>
              <span style={{
                background: `${CAT_COLORS[c.category] || '#8FA5BD'}20`,
                color: CAT_COLORS[c.category] || '#8FA5BD',
                borderRadius: 6, padding: '3px 8px', fontSize: 11, fontWeight: 700,
              }}>{c.category}</span>
            </div>
            <Badge type={c.severity_level === 'critical' ? 'critical' : c.severity_level === 'warning' ? 'warning' : 'info'} label={c.severity_level} />
            <div>
              <span style={{ fontSize: 12, fontWeight: 700, color: c.is_dispute_allowed ? '#10B981' : '#8FA5BD' }}>
                {c.is_dispute_allowed ? '✓ Yes' : '✗ No'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function ReconEngine() {
  const token   = useAuthStore(s => s.token)
  const [tab, setTab]           = useState('upload')
  const [files, setFiles]       = useState([])
  const [jobs, setJobs]         = useState([])
  const [summary, setSummary]   = useState(null)
  const [loading, setLoading]   = useState(true)

  // Pipeline overlay state
  const [pipelineJob, setPipelineJob] = useState(null)  // { id, name } | null

  const load = useCallback(async function() {
    try {
      const [fl, jl, sm] = await Promise.all([
        api(token, '/recon-engine/files'),
        api(token, '/recon-engine/jobs'),
        api(token, '/recon-engine/summary'),
      ])
      setFiles(fl.items || [])
      setJobs(jl.items || [])
      setSummary(sm)
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(function() { load() }, [load])

  function handleSelectJob() {
    setTab('leakage')
  }

  // Opens the live pipeline overlay — called after POST /run succeeds
  function handleRunJob(jobId, jobName) {
    setPipelineJob({ id: jobId, name: jobName })
  }

  // Dismiss overlay, refresh list, optionally switch to leakage tab
  function handlePipelineClose() {
    setPipelineJob(null)
    load()
  }

  function handlePipelineComplete() {
    load()  // refresh summary + job list in background
  }

  const TABS = [
    { id: 'upload',   label: 'Upload Files',    icon: '📁' },
    { id: 'jobs',     label: 'Jobs',            icon: '⚙️' },
    { id: 'leakage',  label: 'Leakage Report',  icon: '🔍' },
    { id: 'codes',    label: 'Deduction Codes', icon: '📖' },
  ]

  return (
    <div style={{ padding: '24px 28px', minHeight: '100vh', background: '#F1F5F9' }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <div style={{ fontSize: 24 }}>🔬</div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#0D1F35' }}>Reconciliation Engine</h1>
          <span style={{ background: 'rgba(10,191,202,.15)', color: '#0ABFCA', borderRadius: 20, padding: '3px 12px', fontSize: 11, fontWeight: 700 }}>PRODUCTION GRADE</span>
        </div>
        <div style={{ fontSize: 13, color: '#4B6080' }}>
          Multi-file ingestion · ETL pipeline · 10 leakage detectors · Root cause analysis · Expected vs Actual payout
        </div>
      </div>

      {/* Summary stats */}
      {summary && (
        <div style={{ display: 'flex', gap: 14, marginBottom: 24, flexWrap: 'wrap' }}>
          <StatCard label="Total Jobs"        value={summary.total_jobs}    sub={`${summary.completed_jobs} completed`} color="#0ABFCA" />
          <StatCard label="Total Leakage"     value={fmt(summary.total_leakage)}  sub="across all jobs" color="#E8344A" onClick={() => setTab('leakage')} />
          <StatCard label="Disputable Amount" value={fmt(summary.total_disputable)} sub="can be recovered" color="#E9930D" onClick={() => setTab('leakage')} />
          <StatCard label="Open Events"       value={summary.open_events}   sub="require action" color="#F97316" onClick={() => setTab('leakage')} />
          <StatCard label="Files Uploaded"    value={summary.total_files}   sub="across all jobs" color="#8B5CF6" onClick={() => setTab('upload')} />
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 2, marginBottom: 24, background: '#fff', borderRadius: 12, padding: 4, width: 'fit-content', border: '1px solid #E8EFF6' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding: '8px 20px', borderRadius: 9, border: 'none', cursor: 'pointer',
            fontSize: 13, fontWeight: 600,
            background: tab === t.id ? 'linear-gradient(135deg,#0ABFCA,#088F99)' : 'transparent',
            color: tab === t.id ? '#fff' : '#4B6080',
            display: 'flex', alignItems: 'center', gap: 6,
            transition: 'all .15s',
          }}>
            <span>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}><Spinner /></div>
      ) : (
        <>
          {tab === 'upload'  && <UploadTab    token={token} files={files} onRefresh={load} />}
          {tab === 'jobs'    && <JobsTab      token={token} files={files} jobs={jobs} onRefresh={load} onSelectJob={handleSelectJob} onRunJob={handleRunJob} />}
          {tab === 'leakage' && <LeakageTab   token={token} jobs={jobs} />}
          {tab === 'codes'   && <DeductionCodesTab token={token} />}
        </>
      )}

      {/* ── Live pipeline overlay ─────────────────────────────────────────── */}
      <AnimatePresence>
        {pipelineJob && (
          <ReconciliationPipeline
            key={pipelineJob.id}
            jobId={pipelineJob.id}
            jobName={pipelineJob.name}
            token={token}
            onClose={handlePipelineClose}
            onComplete={handlePipelineComplete}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
