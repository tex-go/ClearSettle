import React, { useState, useEffect, useRef, useCallback } from 'react'
import api from '../utils/api'

// ── Palette ────────────────────────────────────────────────────────────────────
const P = {
  teal: '#0ABFCA', navy: '#0D1F35', green: '#10B981',
  red: '#E8344A', amber: '#E9930D', blue: '#3B82F6',
  purple: '#8B5CF6', bg: '#F1F5F9',
}

const PLATFORM_META = {
  flipkart: { label: 'Flipkart', icon: '🛒', color: '#FF6B35' },
  amazon:   { label: 'Amazon',   icon: '📦', color: '#FF9900' },
  meesho:   { label: 'Meesho',   icon: '🧵', color: '#7B2D8B' },
  unknown:  { label: 'Unknown',  icon: '❓', color: '#9CA3AF' },
}

const STATUS_MAP = {
  uploaded:       { label: 'Queued',         color: P.blue,  bg: 'rgba(59,130,246,.12)' },
  detecting:      { label: 'Detecting…',     color: P.amber, bg: 'rgba(233,147,13,.12)', spin: true },
  detected:       { label: 'Detected',       color: P.teal,  bg: 'rgba(10,191,202,.12)' },
  processing:     { label: 'Processing…',    color: P.amber, bg: 'rgba(233,147,13,.12)', spin: true },
  done:           { label: 'Done',           color: P.green, bg: 'rgba(16,185,129,.12)' },
  failed:         { label: 'Failed',         color: P.red,   bg: 'rgba(232,52,74,.12)' },
  needs_review:   { label: 'Needs Review',   color: '#E9930D', bg: 'rgba(233,147,13,.15)' },
}

const PIPELINE_STAGES = [
  { icon: '🔬', label: 'Fingerprinting file',         key: 'fingerprint' },
  { icon: '🔍', label: 'Detecting platform',           key: 'detect_platform' },
  { icon: '📋', label: 'Identifying report type',      key: 'detect_type' },
  { icon: '🗂️', label: 'Matching schema version',     key: 'detect_schema' },
  { icon: '⚙️', label: 'Parsing & normalising records', key: 'parse' },
  { icon: '🔄', label: 'Running reconciliation',       key: 'reconcile' },
]

const REPORT_TYPE_LABELS = {
  pl_report:          'P&L Report',
  payment_report:     'Payment Report',
  settlement_report:  'Settlement Report',
  tax_report:         'Tax / GST Report',
  returns_report:     'Returns Report',
  commission_invoice: 'Commission Invoice',
  fba_inventory:      'FBA Inventory',
  order_report:       'Order Report',
  safe_t_report:      'SAFE-T Claim',
  unknown:            'Unknown',
}

// ── Mini components ────────────────────────────────────────────────────────────
function Spinner({ size = 16 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      border: `2px solid rgba(10,191,202,.25)`, borderTopColor: P.teal,
      animation: 'spin 0.7s linear infinite', flexShrink: 0,
      display: 'inline-block',
    }} />
  )
}

function StatusChip({ status }) {
  const s = STATUS_MAP[status] || STATUS_MAP.uploaded
  return (
    <span style={{
      background: s.bg, color: s.color,
      borderRadius: 8, padding: '3px 9px',
      fontSize: 11, fontWeight: 700,
      display: 'inline-flex', alignItems: 'center', gap: 5,
      whiteSpace: 'nowrap',
    }}>
      {s.spin && <Spinner size={10} />}
      {s.label}
    </span>
  )
}

function PlatformChip({ platform }) {
  const m = PLATFORM_META[platform] || PLATFORM_META.unknown
  return (
    <span style={{
      background: m.color + '18', color: m.color,
      borderRadius: 8, padding: '3px 9px',
      fontSize: 11, fontWeight: 700,
      display: 'inline-flex', alignItems: 'center', gap: 5,
    }}>
      {m.icon} {m.label}
    </span>
  )
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100)
  const color = value >= 0.85 ? P.green : value >= 0.55 ? P.amber : P.red
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 120 }}>
      <div style={{ flex: 1, height: 6, background: '#E5E7EB', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: pct + '%', background: color, borderRadius: 99, transition: 'width .4s ease' }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color, minWidth: 28 }}>{pct}%</span>
    </div>
  )
}

function fmtBytes(n) {
  if (!n) return '—'
  if (n < 1024) return n + ' B'
  if (n < 1048576) return (n / 1024).toFixed(0) + ' KB'
  return (n / 1048576).toFixed(1) + ' MB'
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function inr(v) {
  const n = Number(v) || 0
  return '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

// ── Upload Zone ────────────────────────────────────────────────────────────────
function UploadZone({ onUpload }) {
  const [dragging, setDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  function onDragOver(e) { e.preventDefault(); setDragging(true) }
  function onDragLeave()  { setDragging(false) }
  function onDrop(e) {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) { setSelectedFile(f); setError('') }
  }
  function onFileChange(e) {
    const f = e.target.files[0]
    if (f) { setSelectedFile(f); setError('') }
    e.target.value = ''
  }

  async function handleUpload() {
    if (!selectedFile) return
    setUploading(true); setError('')
    try {
      const fd = new FormData()
      fd.append('file', selectedFile)
      const res = await api.post('/ingestion/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setSelectedFile(null)
      onUpload(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed — please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ marginBottom: 28 }}>
      <div
        onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
        onClick={() => !selectedFile && inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? P.teal : selectedFile ? P.green : '#CBD5E1'}`,
          borderRadius: 18,
          padding: '40px 32px',
          textAlign: 'center',
          background: dragging ? 'rgba(10,191,202,.05)' : selectedFile ? 'rgba(16,185,129,.04)' : '#fff',
          cursor: selectedFile ? 'default' : 'pointer',
          transition: 'all .2s',
        }}
      >
        <input
          ref={inputRef} type="file"
          accept=".xlsx,.xls,.csv,.txt,.tsv"
          style={{ display: 'none' }}
          onChange={onFileChange}
        />
        {!selectedFile ? (
          <>
            <div style={{ fontSize: 48, marginBottom: 14 }}>📂</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: P.navy, marginBottom: 8 }}>
              Drop any marketplace report file here
            </div>
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 16, lineHeight: 1.6 }}>
              Flipkart P&L, Payment Report, Amazon Settlement, Meesho Payment — any format.<br />
              The engine will automatically detect the platform and report type.
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
              {['.xlsx', '.xls', '.csv', '.txt', '.tsv'].map(ext => (
                <span key={ext} style={{ background: '#F1F5F9', color: '#64748B', fontSize: 11, fontWeight: 700, borderRadius: 6, padding: '3px 8px' }}>{ext}</span>
              ))}
            </div>
            <button
              onClick={e => { e.stopPropagation(); inputRef.current?.click() }}
              style={{
                background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff',
                border: 'none', borderRadius: 10, padding: '10px 28px',
                fontSize: 14, fontWeight: 700, cursor: 'pointer',
              }}
            >
              Browse Files
            </button>
          </>
        ) : (
          <>
            <div style={{ fontSize: 40, marginBottom: 12 }}>📄</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: P.navy, marginBottom: 4 }}>{selectedFile.name}</div>
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 20 }}>{fmtBytes(selectedFile.size)}</div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 10 }}>
              <button
                onClick={() => setSelectedFile(null)}
                style={{ padding: '9px 22px', borderRadius: 9, border: '1px solid #E5E7EB', background: '#fff', color: '#6B7280', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
              >
                Remove
              </button>
              <button
                onClick={handleUpload} disabled={uploading}
                style={{
                  padding: '9px 28px', borderRadius: 9, border: 'none',
                  background: uploading ? '#9CA3AF' : 'linear-gradient(135deg,#0ABFCA,#088F99)',
                  color: '#fff', fontSize: 13, fontWeight: 700,
                  cursor: uploading ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}
              >
                {uploading && <Spinner size={14} />}
                {uploading ? 'Uploading…' : 'Upload & Analyse'}
              </button>
            </div>
          </>
        )}
      </div>
      {error && (
        <div style={{ marginTop: 10, padding: '10px 14px', background: 'rgba(232,52,74,.08)', borderRadius: 10, fontSize: 13, color: P.red, fontWeight: 600 }}>
          {error}
        </div>
      )}
    </div>
  )
}

// ── Pipeline Tracker (shown while a file is processing) ────────────────────────
function PipelineTracker({ file, detection, onViewLedger, onManualReview }) {
  const [stageIdx, setStageIdx] = useState(0)
  const timerRef = useRef(null)

  const status = file?.upload_status || 'uploaded'
  const isDone = status === 'done' || status === 'failed' || status === 'needs_review'
  const isActive = !isDone

  // Animate through stages every 1.2s while processing
  useEffect(() => {
    if (isActive) {
      timerRef.current = setInterval(() => {
        setStageIdx(prev => (prev < PIPELINE_STAGES.length - 1 ? prev + 1 : prev))
      }, 1200)
    } else {
      setStageIdx(PIPELINE_STAGES.length)
    }
    return () => clearInterval(timerRef.current)
  }, [isActive])

  if (!file) return null

  const platform = detection?.detected_platform || 'unknown'
  const pm = PLATFORM_META[platform] || PLATFORM_META.unknown

  return (
    <div style={{
      background: '#fff', borderRadius: 18,
      border: `1.5px solid ${isDone ? (status === 'done' ? P.green + '40' : status === 'needs_review' ? P.amber + '40' : P.red + '40') : P.teal + '40'}`,
      padding: '24px 28px', marginBottom: 28,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20, gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 800, color: P.navy, marginBottom: 4 }}>
            {isActive ? 'Analysing file…' : status === 'done' ? 'Analysis complete' : status === 'needs_review' ? 'Manual review required' : 'Analysis failed'}
          </div>
          <div style={{ fontSize: 13, color: '#6B7280', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600 }}>{file.original_file_name}</span>
            <span>·</span>
            <span>{fmtBytes(file.file_size_bytes)}</span>
            <span>·</span>
            <StatusChip status={status} />
          </div>
        </div>
        {isDone && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {status === 'done' && (
              <button onClick={onViewLedger} style={{ padding: '7px 16px', borderRadius: 9, background: 'linear-gradient(135deg,#0ABFCA,#088F99)', border: 'none', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                View Ledger
              </button>
            )}
            {status === 'needs_review' && (
              <button onClick={onManualReview} style={{ padding: '7px 16px', borderRadius: 9, background: P.amber, border: 'none', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                Override Detection
              </button>
            )}
          </div>
        )}
      </div>

      {/* Pipeline stages */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: isDone && detection ? 20 : 0 }}>
        {PIPELINE_STAGES.map((stage, i) => {
          const done = i < stageIdx
          const active = i === stageIdx && isActive
          const failed = isDone && status === 'failed' && i === stageIdx
          return (
            <div key={stage.key} style={{
              display: 'flex', alignItems: 'center', gap: 12, opacity: (!done && !active && !isDone) ? 0.35 : 1,
              transition: 'opacity .3s',
            }}>
              <div style={{
                width: 32, height: 32, borderRadius: 10, flexShrink: 0,
                background: done ? 'rgba(16,185,129,.12)' : active ? 'rgba(10,191,202,.12)' : failed ? 'rgba(232,52,74,.1)' : '#F3F4F6',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
              }}>
                {done ? '✅' : failed ? '❌' : active ? <Spinner size={14} /> : stage.icon}
              </div>
              <span style={{ fontSize: 13, fontWeight: done ? 600 : 500, color: done ? P.navy : active ? P.teal : '#9CA3AF' }}>
                {stage.label}
              </span>
              {done && i === PIPELINE_STAGES.length - 1 && detection && (
                <span style={{ marginLeft: 'auto', fontSize: 12, color: '#6B7280' }}>
                  {detection.ledger_records_count} records · {detection.recon_issue_count} issues
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Detection result (shown when done) */}
      {isDone && detection && (
        <div style={{
          marginTop: 16, padding: '16px 20px',
          background: status === 'needs_review' ? 'rgba(233,147,13,.06)' : 'rgba(16,185,129,.05)',
          borderRadius: 12, border: `1px solid ${status === 'needs_review' ? P.amber + '30' : P.green + '30'}`,
        }}>
          {status === 'needs_review' && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 14, padding: '10px 14px', background: 'rgba(233,147,13,.1)', borderRadius: 10 }}>
              <span style={{ fontSize: 18, flexShrink: 0 }}>⚠️</span>
              <div style={{ fontSize: 13, color: '#92400E', lineHeight: 1.5 }}>
                <strong>Low confidence ({Math.round((detection.confidence_score || 0) * 100)}%)</strong> — The engine could not confidently identify this file's platform or report type.
                Use "Override Detection" to set it manually and reprocess.
              </div>
            </div>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20 }}>
            <ResultField label="Platform">
              <PlatformChip platform={detection.detected_platform} />
            </ResultField>
            <ResultField label="Report Type">
              <span style={{ fontSize: 13, fontWeight: 700, color: P.navy }}>
                {REPORT_TYPE_LABELS[detection.detected_report_type] || detection.detected_report_type || '—'}
              </span>
            </ResultField>
            <ResultField label="Confidence">
              <div style={{ width: 150 }}>
                <ConfidenceBar value={detection.confidence_score} />
              </div>
            </ResultField>
            <ResultField label="Schema Version">
              <span style={{ fontSize: 13, fontWeight: 600, color: '#6B7280' }}>{detection.schema_version || '—'}</span>
            </ResultField>
            <ResultField label="Ledger Records">
              <span style={{ fontSize: 15, fontWeight: 800, color: P.teal }}>{(detection.ledger_records_count || 0).toLocaleString()}</span>
            </ResultField>
            <ResultField label="Recon Issues">
              <span style={{ fontSize: 15, fontWeight: 800, color: detection.recon_issue_count > 0 ? P.red : P.green }}>
                {detection.recon_issue_count || 0}
              </span>
            </ResultField>
          </div>
          {detection.drift_alert && (
            <div style={{ marginTop: 14, padding: '10px 14px', background: 'rgba(232,52,74,.06)', borderRadius: 10, border: '1px solid rgba(232,52,74,.2)' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: P.red, marginBottom: 4 }}>Schema Drift Detected</div>
              <div style={{ fontSize: 12, color: '#6B7280', lineHeight: 1.5 }}>
                {detection.drift_alert.message || 'The file schema does not exactly match the known version.'}
                {detection.drift_alert.missing_columns?.length > 0 && (
                  <span> Missing: <em>{detection.drift_alert.missing_columns.slice(0, 5).join(', ')}</em></span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ResultField({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 4 }}>{label}</div>
      {children}
    </div>
  )
}

// ── File History Table ─────────────────────────────────────────────────────────
function FileHistory({ files, loading, onView, onLedger, onManualReview, onDelete, onReprocess }) {
  if (loading) return (
    <div style={{ textAlign: 'center', padding: '48px 0', color: '#9CA3AF', fontSize: 14 }}>
      <Spinner size={28} /><br />Loading file history…
    </div>
  )
  if (!files || files.length === 0) return (
    <div style={{ textAlign: 'center', padding: '48px 0' }}>
      <div style={{ fontSize: 40, marginBottom: 12 }}>📭</div>
      <div style={{ fontSize: 15, fontWeight: 700, color: '#9CA3AF' }}>No files uploaded yet</div>
      <div style={{ fontSize: 13, color: '#CBD5E1', marginTop: 6 }}>Upload your first report to begin analysis</div>
    </div>
  )

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #F1F5F9' }}>
            {['File', 'Uploaded', 'Platform', 'Report Type', 'Confidence', 'Records', 'Status', 'Actions'].map(h => (
              <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '.06em', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {files.map((f, i) => {
            const det = f.detection
            return (
              <tr key={f.id} style={{ borderBottom: '1px solid #F1F5F9', transition: 'background .12s' }}
                onMouseEnter={e => e.currentTarget.style.background = '#F8FAFC'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <td style={{ padding: '12px', maxWidth: 200 }}>
                  <div style={{ fontWeight: 600, color: P.navy, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={f.original_file_name}>
                    {f.original_file_name}
                  </div>
                  <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 2 }}>{fmtBytes(f.file_size_bytes)}</div>
                </td>
                <td style={{ padding: '12px', whiteSpace: 'nowrap', color: '#6B7280' }}>{fmtDate(f.uploaded_at)}</td>
                <td style={{ padding: '12px' }}>
                  {det ? <PlatformChip platform={det.detected_platform} /> : <span style={{ color: '#CBD5E1' }}>—</span>}
                </td>
                <td style={{ padding: '12px', color: '#6B7280' }}>
                  {det ? (REPORT_TYPE_LABELS[det.detected_report_type] || det.detected_report_type || '—') : '—'}
                </td>
                <td style={{ padding: '12px', minWidth: 140 }}>
                  {det ? <ConfidenceBar value={det.confidence_score} /> : <span style={{ color: '#CBD5E1' }}>—</span>}
                </td>
                <td style={{ padding: '12px', fontWeight: 700, color: P.teal }}>
                  {det?.ledger_records_count != null ? det.ledger_records_count.toLocaleString() : '—'}
                </td>
                <td style={{ padding: '12px' }}>
                  <StatusChip status={f.upload_status} />
                </td>
                <td style={{ padding: '12px' }}>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'nowrap' }}>
                    {f.upload_status === 'done' && (
                      <ActionBtn label="Ledger" color={P.teal} onClick={() => onLedger(f)} />
                    )}
                    {f.upload_status === 'needs_review' && (
                      <ActionBtn label="Review" color={P.amber} onClick={() => onManualReview(f)} />
                    )}
                    {(f.upload_status === 'done' || f.upload_status === 'failed' || f.upload_status === 'needs_review') && (
                      <ActionBtn label="Reprocess" color='#6B7280' onClick={() => onReprocess(f.id)} />
                    )}
                    <ActionBtn label="Delete" color={P.red} onClick={() => onDelete(f.id)} />
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function ActionBtn({ label, color, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '4px 10px', borderRadius: 7, fontSize: 11, fontWeight: 700,
        background: color + '14', color: color,
        border: `1px solid ${color}30`, cursor: 'pointer',
        whiteSpace: 'nowrap', transition: 'background .12s',
      }}
      onMouseEnter={e => e.currentTarget.style.background = color + '28'}
      onMouseLeave={e => e.currentTarget.style.background = color + '14'}
    >
      {label}
    </button>
  )
}

// ── Ledger Modal ───────────────────────────────────────────────────────────────
function LedgerModal({ file, onClose }) {
  const [records, setRecords]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [page, setPage]         = useState(1)
  const [total, setTotal]       = useState(0)
  const [filter, setFilter]     = useState({ tx_type: '', platform: '' })
  const perPage = 50

  const fetch = useCallback(async (p, f) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: p, per_page: perPage })
      if (f.tx_type) params.set('transaction_type', f.tx_type)
      if (f.platform) params.set('platform', f.platform)
      const res = await api.get(`/ingestion/files/${file.id}/ledger?${params}`)
      setRecords(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch {
      setRecords([])
    } finally {
      setLoading(false)
    }
  }, [file.id])

  useEffect(() => { fetch(1, filter) }, [fetch, filter])

  function goPage(p) { setPage(p); fetch(p, filter) }

  const totalPages = Math.ceil(total / perPage)

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 1000,
      display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{
        width: '100%', maxWidth: 1100, maxHeight: '88vh',
        background: '#fff', borderRadius: '20px 20px 0 0',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{ padding: '20px 28px 16px', borderBottom: '1px solid #F1F5F9', display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 17, fontWeight: 800, color: P.navy }}>Ingestion Ledger</div>
            <div style={{ fontSize: 13, color: '#6B7280', marginTop: 2 }}>
              {file.original_file_name} · {total.toLocaleString()} records
            </div>
          </div>
          {/* Filters */}
          <select value={filter.tx_type} onChange={e => { setFilter(f => ({ ...f, tx_type: e.target.value })); setPage(1) }}
            style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid #E5E7EB', fontSize: 12, color: '#374151', background: '#fff' }}>
            <option value="">All transaction types</option>
            <option value="sale">Sale</option>
            <option value="return">Return</option>
            <option value="fee">Fee</option>
            <option value="tax">Tax</option>
          </select>
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: 8, background: '#F3F4F6', border: 'none', fontSize: 18, cursor: 'pointer', color: '#6B7280' }}>×</button>
        </div>

        {/* Table */}
        <div style={{ flex: 1, overflowY: 'auto', overflowX: 'auto' }}>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}><Spinner size={32} /></div>
          ) : records.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#9CA3AF' }}>No ledger records found.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead style={{ position: 'sticky', top: 0, background: '#F8FAFC', zIndex: 1 }}>
                <tr>
                  {['#', 'Order ID', 'SKU', 'Platform', 'Type', 'Fee Type', 'Amount', 'Tax', 'Currency', 'Date', 'Source Row'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 700, color: '#9CA3AF', fontSize: 10, textTransform: 'uppercase', letterSpacing: '.06em', whiteSpace: 'nowrap', borderBottom: '2px solid #F1F5F9' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r, i) => (
                  <tr key={r.id || i} style={{ borderBottom: '1px solid #F8FAFC' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F8FAFC'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '8px 12px', color: '#9CA3AF' }}>{(page - 1) * perPage + i + 1}</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 11, color: P.navy, maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.order_id || '—'}</td>
                    <td style={{ padding: '8px 12px', maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#374151' }}>{r.sku || '—'}</td>
                    <td style={{ padding: '8px 12px' }}><PlatformChip platform={r.platform} /></td>
                    <td style={{ padding: '8px 12px', color: '#6B7280' }}>{r.transaction_type || '—'}</td>
                    <td style={{ padding: '8px 12px', color: '#6B7280' }}>{r.fee_type || '—'}</td>
                    <td style={{ padding: '8px 12px', fontWeight: 700, color: Number(r.amount) < 0 ? P.red : P.green }}>{r.amount != null ? inr(r.amount) : '—'}</td>
                    <td style={{ padding: '8px 12px', color: '#6B7280' }}>{r.tax_amount != null ? inr(r.tax_amount) : '—'}</td>
                    <td style={{ padding: '8px 12px', color: '#9CA3AF' }}>{r.currency || 'INR'}</td>
                    <td style={{ padding: '8px 12px', color: '#9CA3AF', whiteSpace: 'nowrap' }}>{r.transaction_date || '—'}</td>
                    <td style={{ padding: '8px 12px', color: '#CBD5E1' }}>{r.source_row_number || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ padding: '12px 28px', borderTop: '1px solid #F1F5F9', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, color: '#9CA3AF', flex: 1 }}>
              Page {page} of {totalPages} ({total.toLocaleString()} records)
            </span>
            <button disabled={page <= 1} onClick={() => goPage(page - 1)} style={{ padding: '5px 12px', borderRadius: 7, border: '1px solid #E5E7EB', background: '#fff', cursor: page > 1 ? 'pointer' : 'not-allowed', opacity: page <= 1 ? 0.4 : 1, fontSize: 12 }}>← Prev</button>
            {[...Array(Math.min(5, totalPages))].map((_, j) => {
              const pg = Math.max(1, page - 2) + j
              if (pg > totalPages) return null
              return (
                <button key={pg} onClick={() => goPage(pg)} style={{ width: 30, height: 30, borderRadius: 7, border: `1px solid ${pg === page ? P.teal : '#E5E7EB'}`, background: pg === page ? P.teal : '#fff', color: pg === page ? '#fff' : '#374151', fontSize: 12, fontWeight: pg === page ? 700 : 400, cursor: 'pointer' }}>{pg}</button>
              )
            })}
            <button disabled={page >= totalPages} onClick={() => goPage(page + 1)} style={{ padding: '5px 12px', borderRadius: 7, border: '1px solid #E5E7EB', background: '#fff', cursor: page < totalPages ? 'pointer' : 'not-allowed', opacity: page >= totalPages ? 0.4 : 1, fontSize: 12 }}>Next →</button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Manual Review Panel ────────────────────────────────────────────────────────
function ManualReviewPanel({ file, onClose, onDone }) {
  const [platform, setPlatform]     = useState(file.detection?.detected_platform || '')
  const [reportType, setReportType] = useState(file.detection?.detected_report_type || '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]           = useState('')

  const PLATFORMS_LIST = ['flipkart', 'amazon', 'meesho']
  const REPORT_TYPES = [
    'pl_report', 'payment_report', 'settlement_report',
    'tax_report', 'returns_report', 'commission_invoice',
    'order_report', 'fba_inventory',
  ]

  async function submit() {
    if (!platform || !reportType) { setError('Select both platform and report type.'); return }
    setSubmitting(true); setError('')
    try {
      await api.post(`/ingestion/files/${file.id}/manual-review`, {
        platform, report_type: reportType,
      })
      onDone()
    } catch (err) {
      setError(err.response?.data?.detail || 'Override failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ width: '100%', maxWidth: 480, background: '#fff', borderRadius: 20, overflow: 'hidden' }}>
        <div style={{ padding: '24px 28px 0', borderBottom: '1px solid #F1F5F9', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: P.navy }}>Override Detection</div>
            <button onClick={onClose} style={{ width: 30, height: 30, borderRadius: 8, background: '#F3F4F6', border: 'none', fontSize: 18, cursor: 'pointer', color: '#6B7280' }}>×</button>
          </div>
          <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 16, lineHeight: 1.5 }}>
            The engine was not confident about <strong>{file.original_file_name}</strong>. Manually set the platform and report type to reprocess.
          </div>
          {file.detection && (
            <div style={{ marginBottom: 16, padding: '10px 14px', background: '#F8FAFC', borderRadius: 10, fontSize: 12, color: '#6B7280' }}>
              Auto-detected: <strong>{file.detection.detected_platform || 'unknown'}</strong> / <strong>{file.detection.detected_report_type || 'unknown'}</strong> · Confidence: <strong>{Math.round((file.detection.confidence_score || 0) * 100)}%</strong>
            </div>
          )}
        </div>

        <div style={{ padding: '0 28px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', display: 'block', marginBottom: 6 }}>Platform</label>
            <select value={platform} onChange={e => setPlatform(e.target.value)}
              style={{ width: '100%', padding: '9px 12px', borderRadius: 9, border: '1.5px solid #E5E7EB', fontSize: 13, color: '#374151', background: '#fff' }}>
              <option value="">— Select platform —</option>
              {PLATFORMS_LIST.map(p => (
                <option key={p} value={p}>{PLATFORM_META[p]?.icon} {PLATFORM_META[p]?.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', display: 'block', marginBottom: 6 }}>Report Type</label>
            <select value={reportType} onChange={e => setReportType(e.target.value)}
              style={{ width: '100%', padding: '9px 12px', borderRadius: 9, border: '1.5px solid #E5E7EB', fontSize: 13, color: '#374151', background: '#fff' }}>
              <option value="">— Select report type —</option>
              {REPORT_TYPES.map(rt => (
                <option key={rt} value={rt}>{REPORT_TYPE_LABELS[rt] || rt}</option>
              ))}
            </select>
          </div>
          {error && <div style={{ padding: '10px 14px', background: 'rgba(232,52,74,.08)', borderRadius: 9, fontSize: 13, color: P.red }}>{error}</div>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', paddingTop: 4 }}>
            <button onClick={onClose} style={{ padding: '9px 20px', borderRadius: 9, border: '1px solid #E5E7EB', background: '#fff', color: '#6B7280', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Cancel</button>
            <button onClick={submit} disabled={submitting} style={{ padding: '9px 24px', borderRadius: 9, background: submitting ? '#9CA3AF' : P.amber, border: 'none', color: '#fff', fontSize: 13, fontWeight: 700, cursor: submitting ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              {submitting && <Spinner size={13} />}
              {submitting ? 'Reprocessing…' : 'Override & Reprocess'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function Ingestion() {
  const [files, setFiles]               = useState([])
  const [filesLoading, setFilesLoading] = useState(true)
  const [activeFileId, setActiveFileId] = useState(null)
  const [activeFileData, setActiveFileData] = useState(null)
  const [detection, setDetection]       = useState(null)
  const [ledgerFile, setLedgerFile]     = useState(null)
  const [reviewFile, setReviewFile]     = useState(null)
  const [toast, setToast]               = useState(null)
  const pollRef = useRef(null)
  const pollCount = useRef(0)

  function showToast(msg, kind = 'success') {
    setToast({ msg, kind })
    setTimeout(() => setToast(null), 3500)
  }

  // Load file history
  const loadFiles = useCallback(async () => {
    try {
      const res = await api.get('/ingestion/files?per_page=50')
      setFiles(res.data.items || [])
    } catch {
      setFiles([])
    } finally {
      setFilesLoading(false)
    }
  }, [])

  useEffect(() => { loadFiles() }, [loadFiles])

  // Polling for active file
  const startPolling = useCallback((fileId) => {
    clearInterval(pollRef.current)
    pollCount.current = 0
    pollRef.current = setInterval(async () => {
      pollCount.current++
      if (pollCount.current > 60) { clearInterval(pollRef.current); return }
      try {
        const res = await api.get(`/ingestion/files/${fileId}`)
        const f = res.data
        setActiveFileData(f)
        const done = ['done', 'failed', 'needs_review'].includes(f.upload_status)
        if (done) {
          clearInterval(pollRef.current)
          if (f.upload_status === 'done' || f.upload_status === 'needs_review') {
            try {
              const dr = await api.get(`/ingestion/files/${fileId}/detection`)
              setDetection(dr.data)
            } catch { /* detection may not exist yet */ }
          }
          loadFiles()
        }
      } catch { /* ignore poll errors */ }
    }, 2500)
  }, [loadFiles])

  useEffect(() => () => clearInterval(pollRef.current), [])

  function onUpload(data) {
    showToast('File uploaded — analysis started…', 'info')
    setActiveFileId(data.id || data.file_id)
    setActiveFileData(data)
    setDetection(null)
    startPolling(data.id || data.file_id)
  }

  async function handleDelete(fileId) {
    if (!window.confirm('Delete this file and all its analysis data?')) return
    try {
      await api.delete(`/ingestion/files/${fileId}`)
      showToast('File deleted.')
      if (activeFileId === fileId) { setActiveFileId(null); setActiveFileData(null); setDetection(null) }
      loadFiles()
    } catch { showToast('Delete failed.', 'error') }
  }

  async function handleReprocess(fileId) {
    try {
      await api.post(`/ingestion/files/${fileId}/reprocess`)
      showToast('Reprocessing started…', 'info')
      setActiveFileId(fileId)
      setActiveFileData(null); setDetection(null)
      startPolling(fileId)
      loadFiles()
    } catch { showToast('Reprocess failed.', 'error') }
  }

  function handleViewFromHistory(f) {
    setActiveFileId(f.id)
    setActiveFileData(f)
    setDetection(f.detection || null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleReviewDone() {
    const fid = reviewFile?.id
    setReviewFile(null)
    showToast('Override applied — reprocessing…', 'info')
    if (fid) {
      setActiveFileId(fid); setActiveFileData(null); setDetection(null)
      startPolling(fid)
    }
    loadFiles()
  }

  // Stats from file list
  const stats = {
    total: files.length,
    done: files.filter(f => f.upload_status === 'done').length,
    needsReview: files.filter(f => f.upload_status === 'needs_review').length,
    failed: files.filter(f => f.upload_status === 'failed').length,
  }

  return (
    <div className="page page-anim">
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 24, zIndex: 2000,
          padding: '12px 20px', borderRadius: 12, fontSize: 13, fontWeight: 600,
          background: toast.kind === 'error' ? P.red : toast.kind === 'info' ? P.teal : P.green,
          color: '#fff', boxShadow: '0 4px 24px rgba(0,0,0,.18)',
          animation: 'slideInRight .25s ease',
        }}>
          {toast.msg}
        </div>
      )}

      {/* Page header */}
      <div className="page-hd">
        <div>
          <div className="page-title">Report Ingestion Engine</div>
          <div className="page-sub">Upload any Flipkart, Amazon or Meesho report — auto-detect, parse and normalise</div>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 24, flexWrap: 'wrap' }}>
        {[
          { icon: '📂', label: 'Total Files',     value: stats.total,       color: P.teal },
          { icon: '✅', label: 'Processed',        value: stats.done,        color: P.green },
          { icon: '⚠️', label: 'Needs Review',     value: stats.needsReview, color: P.amber },
          { icon: '❌', label: 'Failed',            value: stats.failed,      color: P.red },
        ].map(s => (
          <div key={s.label} style={{
            flex: 1, minWidth: 120, background: '#fff', borderRadius: 14,
            border: '1px solid #E8EFF6', borderLeft: `4px solid ${s.color}`,
            padding: '16px 18px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <span style={{ fontSize: 16 }}>{s.icon}</span>
              <span style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '.07em' }}>{s.label}</span>
            </div>
            <div style={{ fontSize: 26, fontWeight: 800, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Upload zone */}
      <UploadZone onUpload={onUpload} />

      {/* Active file tracker */}
      {activeFileData && (
        <PipelineTracker
          file={activeFileData}
          detection={detection}
          onViewLedger={() => setLedgerFile({ ...activeFileData, id: activeFileId })}
          onManualReview={() => setReviewFile({ ...activeFileData, id: activeFileId, detection })}
        />
      )}

      {/* How it works — info box */}
      <div style={{
        background: 'linear-gradient(135deg,rgba(10,191,202,.06),rgba(59,130,246,.04))',
        border: '1px solid rgba(10,191,202,.2)',
        borderRadius: 14, padding: '16px 22px', marginBottom: 28,
        display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: 28, flexShrink: 0 }}>🤖</span>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: P.navy, marginBottom: 8 }}>How auto-detection works</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {[
              { icon: '🔬', text: 'Fingerprints sheet names & column headers' },
              { icon: '📡', text: 'Scores 40+ platform signals (Flipkart/Amazon/Meesho)' },
              { icon: '🗂️', text: 'Matches schema against known versions (Jaccard similarity)' },
              { icon: '⚙️', text: 'Routes to correct parser automatically' },
              { icon: '📊', text: 'Normalises all records into a unified ledger' },
            ].map(item => (
              <div key={item.text} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#6B7280', background: '#fff', borderRadius: 8, padding: '5px 10px', border: '1px solid #E5E7EB' }}>
                <span>{item.icon}</span> {item.text}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* File history */}
      <div style={{ background: '#fff', borderRadius: 18, border: '1px solid #E8EFF6', overflow: 'hidden' }}>
        <div style={{ padding: '20px 24px 14px', borderBottom: '1px solid #F1F5F9', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: P.navy }}>Upload History</div>
            <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>{files.length} file{files.length !== 1 ? 's' : ''} in your account</div>
          </div>
          <button onClick={loadFiles} style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid #E5E7EB', background: '#fff', fontSize: 12, fontWeight: 600, color: '#6B7280', cursor: 'pointer' }}>
            ↻ Refresh
          </button>
        </div>
        <div style={{ padding: '8px 0' }}>
          <FileHistory
            files={files}
            loading={filesLoading}
            onView={handleViewFromHistory}
            onLedger={setLedgerFile}
            onManualReview={f => setReviewFile(f)}
            onDelete={handleDelete}
            onReprocess={handleReprocess}
          />
        </div>
      </div>

      {/* Ledger modal */}
      {ledgerFile && <LedgerModal file={ledgerFile} onClose={() => setLedgerFile(null)} />}

      {/* Manual review modal */}
      {reviewFile && <ManualReviewPanel file={reviewFile} onClose={() => setReviewFile(null)} onDone={handleReviewDone} />}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg) } }
        @keyframes slideInRight { from { transform: translateX(24px); opacity: 0 } to { transform: translateX(0); opacity: 1 } }
      `}</style>
    </div>
  )
}
