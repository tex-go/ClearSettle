import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import api from '../utils/api'

// ── Palette ────────────────────────────────────────────────────────────────────
const P = {
  teal: '#0ABFCA', navy: '#0D1F35', green: '#10B981',
  red: '#E8344A', amber: '#E9930D', purple: '#8B5CF6',
  blue: '#3B82F6', bg: '#F1F5F9',
}
const PIE_COLORS = [P.teal, P.amber, P.red, P.purple, P.blue, P.green, '#F97316', '#EC4899']

// ── Formatters ─────────────────────────────────────────────────────────────────
function inr(n, compact) {
  const num = Number(n) || 0
  if (compact) {
    if (num >= 1e7) return '₹' + (num / 1e7).toFixed(1) + ' Cr'
    if (num >= 1e5) return '₹' + (num / 1e5).toFixed(1) + 'L'
    if (num >= 1e3) return '₹' + (num / 1e3).toFixed(1) + 'K'
    return '₹' + num.toFixed(0)
  }
  return '₹' + num.toLocaleString('en-IN', { maximumFractionDigits: 0 })
}
function pct(n) { return n == null ? '—' : Number(n).toFixed(1) + '%' }
function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

// ── Platforms config ───────────────────────────────────────────────────────────
const PLATFORMS = [
  { id: 'flipkart', label: 'Flipkart', icon: '🛒', live: true,  color: '#FF6B35',
    desc: 'Upload P&L, Settlement Statement and Returns Report from Flipkart Seller Hub' },
  { id: 'amazon',   label: 'Amazon',   icon: '📦', live: false, color: '#FF9900', desc: 'SP-API integration — coming soon' },
  { id: 'meesho',   label: 'Meesho',   icon: '🧵', live: false, color: '#7B2D8B', desc: 'Report upload — coming soon' },
  { id: 'myntra',   label: 'Myntra',   icon: '👗', live: false, color: '#FF3F6C', desc: 'Coming soon' },
  { id: 'ajio',     label: 'Ajio',     icon: '🎽', live: false, color: '#F26522', desc: 'Coming soon' },
  { id: 'nykaa',    label: 'Nykaa',    icon: '💄', live: false, color: '#FC2779', desc: 'Coming soon' },
]

// ── Required docs definition ───────────────────────────────────────────────────
const REQUIRED_DOCS = [
  {
    key: 'pl_report',
    label: 'P&L Report',
    icon: '📊',
    accent: P.teal,
    description: 'Profit & Loss breakdown by SKU and order. Core report for fee analysis.',
    accept: '.xlsx,.xls',
    steps: [
      'Log in to Flipkart Seller Hub',
      'Go to Reports → P&L Report',
      'Select the date range (monthly recommended)',
      'Click Download → Choose Excel format',
      'Upload the downloaded .xlsx file here',
    ],
    analysisComing: false,
  },
  {
    key: 'settlement_statement',
    label: 'Settlement Statement',
    icon: '🏦',
    accent: P.blue,
    description: 'Actual bank transfer amounts. Used to verify credits against expected payouts.',
    accept: '.xlsx,.xls,.csv',
    steps: [
      'Log in to Flipkart Seller Hub',
      'Go to Payments → Settlement Reports',
      'Select the settlement cycle matching your P&L period',
      'Click Download → Excel or CSV format',
      'Upload the downloaded file here',
    ],
    analysisComing: true,
  },
  {
    key: 'returns_report',
    label: 'Returns Report',
    icon: '↩️',
    accent: P.amber,
    description: 'Per-order return reasons and refund amounts. Essential for return rate analysis.',
    accept: '.xlsx,.xls,.csv',
    steps: [
      'Log in to Flipkart Seller Hub',
      'Go to Reports → Returns Report',
      'Select the date range matching your P&L period',
      'Click Download → Excel or CSV format',
      'Upload the downloaded file here',
    ],
    analysisComing: true,
  },
]

// ── Processing animation stages ────────────────────────────────────────────────
const STAGES = [
  { icon: '📤', label: 'Reading document structure...' },
  { icon: '🔍', label: 'Parsing order & SKU data...' },
  { icon: '💰', label: 'Calculating Profit & Loss...' },
  { icon: '🔬', label: 'Running reconciliation engine...' },
  { icon: '💡', label: 'Generating insights...' },
]

// ── Mini UI components ─────────────────────────────────────────────────────────
function Spinner({ size = 20 }) {
  return <div style={{ width: size, height: size, borderRadius: '50%', border: '3px solid rgba(10,191,202,.2)', borderTopColor: P.teal, animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
}

function Badge({ label, color }) {
  const c = { green: { bg: 'rgba(16,185,129,.12)', fg: '#10B981' }, red: { bg: 'rgba(232,52,74,.12)', fg: '#E8344A' }, amber: { bg: 'rgba(233,147,13,.12)', fg: '#E9930D' }, teal: { bg: 'rgba(10,191,202,.12)', fg: '#0ABFCA' }, gray: { bg: '#F3F4F6', fg: '#6B7280' }, blue: { bg: 'rgba(59,130,246,.12)', fg: '#3B82F6' } }
  const s = c[color || 'teal']
  return <span style={{ background: s.bg, color: s.fg, borderRadius: 8, padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>{label}</span>
}

function statusBadge(status) {
  const map = { done: 'green', failed: 'red', processing: 'amber', pending: 'amber', awaiting_confirmation: 'teal', uploaded: 'blue', default: 'gray' }
  return <Badge label={status?.replace('_', ' ') || '—'} color={map[status] || map.default} />
}

// ── Hero KPI card ──────────────────────────────────────────────────────────────
function HeroCard({ icon, label, value, sub, accent, note, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: '#fff', border: '1px solid #E8EFF6',
      borderRadius: 16, padding: '20px 22px',
      borderLeft: `4px solid ${accent}`,
      flex: 1, minWidth: 0,
      cursor: onClick ? 'pointer' : 'default',
      transition: 'box-shadow .15s',
    }}
    onMouseEnter={e => onClick && (e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,.08)')}
    onMouseLeave={e => (e.currentTarget.style.boxShadow = 'none')}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 20 }}>{icon}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#8FA5BD', textTransform: 'uppercase', letterSpacing: '.07em' }}>{label}</span>
      </div>
      <div style={{ fontSize: 26, fontWeight: 800, color: accent, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 13, color: '#6B7280', marginTop: 6 }}>{sub}</div>}
      {note && <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 8, lineHeight: 1.4 }}>{note}</div>}
    </div>
  )
}

// ── Platform Select View ───────────────────────────────────────────────────────
function PlatformSelect({ onSelect }) {
  return (
    <div style={{ minHeight: '70vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px' }}>
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <div style={{ fontSize: 28, fontWeight: 800, color: P.navy, marginBottom: 10 }}>Settlement Intelligence</div>
        <div style={{ fontSize: 15, color: '#6B7280', maxWidth: 480, lineHeight: 1.6 }}>
          Select your marketplace. We'll analyse your reports to detect potential payout anomalies and money leakage.
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, width: '100%', maxWidth: 600 }}>
        {PLATFORMS.map(function(p) {
          return (
            <button
              key={p.id}
              onClick={function() { p.live && onSelect(p) }}
              title={!p.live ? 'Coming soon' : ''}
              style={{
                padding: '24px 16px', borderRadius: 14,
                background: p.live ? '#fff' : '#F9FAFB',
                border: p.live ? '1.5px solid #E8EFF6' : '1.5px solid #F3F4F6',
                cursor: p.live ? 'pointer' : 'not-allowed',
                opacity: p.live ? 1 : 0.55, transition: 'all .18s',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
              }}
              onMouseEnter={e => p.live && (e.currentTarget.style.boxShadow = '0 6px 24px rgba(0,0,0,.1)')}
              onMouseLeave={e => (e.currentTarget.style.boxShadow = 'none')}
            >
              <span style={{ fontSize: 30 }}>{p.icon}</span>
              <span style={{ fontSize: 14, fontWeight: 700, color: p.live ? P.navy : '#9CA3AF' }}>{p.label}</span>
              {!p.live && <span style={{ fontSize: 10, color: '#9CA3AF', fontWeight: 600 }}>COMING SOON</span>}
            </button>
          )
        })}
      </div>
      <div style={{ marginTop: 32, fontSize: 11, color: '#9CA3AF', textAlign: 'center', maxWidth: 420, lineHeight: 1.6 }}>
        All figures shown are <em>estimated potential discrepancies</em> based on your uploaded data.
        Verify before raising disputes. ClearSettle does not guarantee recovery.
      </div>
    </div>
  )
}

// ── Docs Gate ─────────────────────────────────────────────────────────────────
function DocsGate({ platform, onAllUploaded, onPlFileUploaded, onBack, preventAutoProceed }) {
  const [docsStatus, setDocsStatus]   = useState(null)
  const [loading, setLoading]         = useState(true)
  const [uploadingKey, setUploadingKey] = useState(null)
  const [uploadErrors, setUploadErrors] = useState({})
  const [expanded, setExpanded]       = useState({})
  const fileRefs = useRef({})

  const fetchStatus = useCallback(function() {
    api.get('/flipkart/docs-status')
      .then(function(r) { setDocsStatus(r.data) })
      .catch(function() { setDocsStatus(null) })
      .finally(function() { setLoading(false) })
  }, [])

  useEffect(function() { fetchStatus() }, [fetchStatus])

  // Auto-proceed when all 3 are uploaded (skip if user came here to manage docs)
  useEffect(function() {
    if (!docsStatus || preventAutoProceed) return
    const allDone = REQUIRED_DOCS.every(function(d) { return docsStatus[d.key]?.uploaded })
    if (allDone) onAllUploaded()
  }, [docsStatus, onAllUploaded, preventAutoProceed])

  async function handleFile(docKey, file) {
    if (!file) return
    const doc = REQUIRED_DOCS.find(function(d) { return d.key === docKey })
    const validExts = doc.accept.split(',')
    const fname = file.name.toLowerCase()
    if (!validExts.some(function(ext) { return fname.endsWith(ext.trim()) })) {
      setUploadErrors(function(prev) { return { ...prev, [docKey]: `Unsupported file type. Allowed: ${doc.accept}` } })
      return
    }
    setUploadErrors(function(prev) { return { ...prev, [docKey]: '' } })
    setUploadingKey(docKey)
    const form = new FormData()
    form.append('file', file)
    form.append('report_type', docKey)
    try {
      const res = await api.post('/flipkart/upload', form)
      // P&L uploads trigger the preview modal so the user can review before confirming
      if (docKey === 'pl_report' && onPlFileUploaded) {
        onPlFileUploaded(res.data, file)
      }
      await fetchStatus()
    } catch (err) {
      setUploadErrors(function(prev) {
        return { ...prev, [docKey]: err.response?.data?.detail || 'Upload failed. Please try again.' }
      })
    } finally {
      setUploadingKey(null)
    }
  }

  function toggleExpand(key) {
    setExpanded(function(prev) { return { ...prev, [key]: !prev[key] } })
  }

  const uploadedCount = docsStatus ? REQUIRED_DOCS.filter(function(d) { return docsStatus[d.key]?.uploaded }).length : 0

  return (
    <div style={{ padding: '8px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <button onClick={onBack} style={{ background: '#F3F4F6', border: 'none', borderRadius: 8, padding: '6px 12px', fontSize: 13, color: '#6B7280', cursor: 'pointer' }}>← Back</button>
        <span style={{ fontSize: 20 }}>{platform.icon}</span>
        <div>
          <div style={{ fontSize: 17, fontWeight: 800, color: P.navy }}>{platform.label} — Required Documents</div>
          <div style={{ fontSize: 12, color: '#6B7280' }}>Upload all 3 documents to unlock Settlement Intelligence</div>
        </div>
        <div style={{ marginLeft: 'auto', background: uploadedCount === 3 ? 'rgba(16,185,129,.12)' : 'rgba(233,147,13,.1)', color: uploadedCount === 3 ? P.green : P.amber, borderRadius: 20, padding: '4px 14px', fontSize: 12, fontWeight: 700 }}>
          {uploadedCount} / 3 uploaded
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 4, background: '#E5E7EB', borderRadius: 99, marginBottom: 28, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${(uploadedCount / 3) * 100}%`, background: 'linear-gradient(90deg,#0ABFCA,#10B981)', borderRadius: 99, transition: 'width .5s ease' }} />
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '48px 0' }}><Spinner size={32} /></div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {REQUIRED_DOCS.map(function(doc) {
            const status = docsStatus?.[doc.key]
            const isUploaded = status?.uploaded
            const isUploading = uploadingKey === doc.key
            const isOpen = expanded[doc.key]
            const err = uploadErrors[doc.key]

            return (
              <div key={doc.key} style={{
                background: '#fff',
                border: `1.5px solid ${isUploaded ? doc.accent + '40' : '#E8EFF6'}`,
                borderRadius: 14,
                overflow: 'hidden',
                transition: 'border-color .2s',
              }}>
                {/* Card header row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 20px' }}>
                  {/* Status dot */}
                  <div style={{
                    width: 40, height: 40, borderRadius: 12, flexShrink: 0,
                    background: isUploaded ? doc.accent + '18' : '#F3F4F6',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 20,
                  }}>
                    {isUploaded ? '✅' : doc.icon}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: P.navy }}>{doc.label}</span>
                      {doc.analysisComing && (
                        <span style={{ fontSize: 10, fontWeight: 700, background: 'rgba(59,130,246,.1)', color: P.blue, borderRadius: 6, padding: '2px 7px' }}>
                          ANALYSIS COMING
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{doc.description}</div>
                    {isUploaded && (
                      <div style={{ fontSize: 11, color: P.green, marginTop: 4, fontWeight: 600 }}>
                        ✓ {status.filename} — uploaded {fmtDate(status.uploaded_at)}
                      </div>
                    )}
                    {err && <div style={{ fontSize: 11, color: P.red, marginTop: 4 }}>{err}</div>}
                  </div>

                  <div style={{ display: 'flex', gap: 8, flexShrink: 0, alignItems: 'center' }}>
                    {/* How to get it toggle */}
                    <button
                      onClick={function() { toggleExpand(doc.key) }}
                      style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #E5E7EB', background: '#fff', color: '#6B7280', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                    >
                      {isOpen ? 'Hide steps' : 'How to get it?'}
                    </button>

                    {/* Upload / Re-upload button */}
                    <input
                      ref={function(el) { fileRefs.current[doc.key] = el }}
                      type="file"
                      accept={doc.accept}
                      style={{ display: 'none' }}
                      onChange={function(e) { handleFile(doc.key, e.target.files[0]); e.target.value = '' }}
                    />
                    <button
                      onClick={function() { fileRefs.current[doc.key]?.click() }}
                      disabled={isUploading}
                      style={{
                        padding: '7px 16px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 700,
                        cursor: isUploading ? 'not-allowed' : 'pointer',
                        background: isUploaded
                          ? '#F3F4F6'
                          : `linear-gradient(135deg,${doc.accent},${doc.accent}cc)`,
                        color: isUploaded ? '#6B7280' : '#fff',
                        display: 'flex', alignItems: 'center', gap: 6,
                        transition: 'opacity .15s',
                        opacity: isUploading ? 0.6 : 1,
                      }}
                    >
                      {isUploading ? <><Spinner size={14} /> Uploading...</> : isUploaded ? '↺ Replace' : '↑ Upload'}
                    </button>
                  </div>
                </div>

                {/* Step-by-step instructions accordion */}
                {isOpen && (
                  <div style={{ borderTop: '1px solid #F3F4F6', padding: '16px 20px', background: '#F9FBFC' }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 12 }}>
                      Step-by-step instructions
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {doc.steps.map(function(step, i) {
                        return (
                          <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                            <div style={{
                              width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                              background: doc.accent + '18', color: doc.accent,
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 11, fontWeight: 800,
                            }}>
                              {i + 1}
                            </div>
                            <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.5, paddingTop: 3 }}>{step}</div>
                          </div>
                        )
                      })}
                    </div>
                    {doc.analysisComing && (
                      <div style={{ marginTop: 14, background: 'rgba(59,130,246,.06)', border: '1px solid rgba(59,130,246,.15)', borderRadius: 8, padding: '8px 12px', fontSize: 11, color: P.blue, lineHeight: 1.5 }}>
                        <strong>Note:</strong> We will add full analysis for this document in the next update. Upload it now so you're ready.
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Proceed button */}
      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={onAllUploaded}
          disabled={uploadedCount < 3}
          style={{
            padding: '12px 28px', borderRadius: 10, border: 'none', fontSize: 14, fontWeight: 700,
            background: uploadedCount === 3
              ? 'linear-gradient(135deg,#0ABFCA,#088F99)'
              : '#E5E7EB',
            color: uploadedCount === 3 ? '#fff' : '#9CA3AF',
            cursor: uploadedCount === 3 ? 'pointer' : 'not-allowed',
            transition: 'all .2s',
          }}
        >
          {uploadedCount === 3 ? 'Proceed to Analysis →' : `Upload ${3 - uploadedCount} more document${3 - uploadedCount > 1 ? 's' : ''} to continue`}
        </button>
      </div>
    </div>
  )
}

// ── Preview Modal ──────────────────────────────────────────────────────────────
function PreviewModal({ file, preview, onConfirm, onCancel, confirming }) {
  const sheets = preview?.sheets_found || []
  const orders = preview?.estimated_orders || 0
  const skus   = preview?.estimated_skus   || 0
  const errors = preview?.parse_errors     || []

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 200, background: 'rgba(13,31,53,.7)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ background: '#fff', borderRadius: 20, width: '100%', maxWidth: 480, padding: '32px 28px', boxShadow: '0 24px 80px rgba(0,0,0,.22)' }}>
        <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(10,191,202,.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, flexShrink: 0 }}>📊</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: P.navy }}>Document Preview</div>
            <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>Review before analysis begins</div>
          </div>
        </div>

        {/* File info */}
        <div style={{ background: '#F9FAFB', borderRadius: 10, padding: '12px 14px', marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: P.navy, marginBottom: 4 }}>{file?.name}</div>
          <div style={{ fontSize: 12, color: '#6B7280' }}>
            {file ? (file.size / 1024).toFixed(0) + ' KB' : ''}
          </div>
        </div>

        {/* What we found */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 10 }}>What we found</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sheets.length > 0 && sheets.map(function(sheet) {
              return (
                <div key={sheet} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: P.green, fontSize: 14 }}>✓</span>
                  <span style={{ fontSize: 13, color: '#374151' }}>{sheet} sheet detected</span>
                </div>
              )
            })}
            {orders > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: P.green, fontSize: 14 }}>✓</span>
                <span style={{ fontSize: 13, color: '#374151' }}><strong>{orders.toLocaleString()}</strong> orders found</span>
              </div>
            )}
            {skus > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: P.green, fontSize: 14 }}>✓</span>
                <span style={{ fontSize: 13, color: '#374151' }}><strong>{skus}</strong> SKUs detected</span>
              </div>
            )}
            {errors.length > 0 && errors.map(function(err, i) {
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <span style={{ color: P.amber, fontSize: 14 }}>⚠</span>
                  <span style={{ fontSize: 12, color: P.amber }}>{err}</span>
                </div>
              )
            })}
            {!sheets.length && !orders && !skus && !errors.length && (
              <div style={{ fontSize: 13, color: '#6B7280' }}>File uploaded successfully. Ready to analyse.</div>
            )}
          </div>
        </div>

        {/* Disclaimer */}
        <div style={{ background: 'rgba(10,191,202,.06)', border: '1px solid rgba(10,191,202,.15)', borderRadius: 10, padding: '10px 12px', marginBottom: 20, fontSize: 11, color: '#6B7280', lineHeight: 1.6 }}>
          <span style={{ color: P.teal, fontWeight: 700 }}>Note: </span>
          All figures generated are <em>estimated potential discrepancies</em>. Verify before raising disputes with Flipkart.
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={onCancel} disabled={confirming} style={{ flex: 1, padding: '11px', borderRadius: 10, border: '1px solid #E5E7EB', background: '#fff', color: '#6B7280', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>
            Cancel
          </button>
          <button onClick={onConfirm} disabled={confirming} style={{ flex: 2, padding: '11px', borderRadius: 10, border: 'none', background: confirming ? 'rgba(10,191,202,.4)' : 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', fontSize: 14, fontWeight: 700, cursor: confirming ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            {confirming ? <><Spinner size={16} /> Starting...</> : 'Proceed with Analysis →'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Processing Animation ───────────────────────────────────────────────────────
function ProcessingView({ filename }) {
  const [stage, setStage] = useState(0)
  const [progress, setProgress] = useState(8)

  useEffect(function() {
    const timings = [700, 1100, 900, 1100, 800]
    let idx = 0
    function advance() {
      if (idx >= STAGES.length) return
      idx++
      setStage(idx)
      setProgress(Math.round((idx / STAGES.length) * 85))
      if (idx < STAGES.length) {
        setTimeout(advance, timings[idx] || 900)
      }
    }
    const t = setTimeout(advance, timings[0])
    return function() { clearTimeout(t) }
  }, [])

  return (
    <div style={{ minHeight: '70vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px' }}>
      <div style={{ width: '100%', maxWidth: 440, textAlign: 'center' }}>
        <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'rgba(10,191,202,.1)', border: '3px solid rgba(10,191,202,.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32, margin: '0 auto 24px', animation: 'pulse 2s ease-in-out infinite' }}>
          🔬
        </div>
        <div style={{ fontSize: 20, fontWeight: 800, color: P.navy, marginBottom: 6 }}>Analysing your report</div>
        <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 28 }}>{filename}</div>
        <div style={{ height: 6, background: '#E5E7EB', borderRadius: 99, overflow: 'hidden', marginBottom: 28 }}>
          <div style={{ height: '100%', width: progress + '%', background: 'linear-gradient(90deg,#0ABFCA,#088F99)', borderRadius: 99, transition: 'width .6s ease' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, textAlign: 'left' }}>
          {STAGES.map(function(s, i) {
            const done    = i < stage
            const active  = i === stage
            const pending = i > stage
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, opacity: pending ? 0.35 : 1, transition: 'opacity .3s' }}>
                <div style={{ width: 28, height: 28, borderRadius: '50%', flexShrink: 0, background: done ? 'rgba(16,185,129,.12)' : active ? 'rgba(10,191,202,.12)' : '#F3F4F6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13 }}>
                  {done ? '✓' : active ? <Spinner size={14} /> : s.icon}
                </div>
                <span style={{ fontSize: 13, fontWeight: active ? 600 : 400, color: done ? P.green : active ? P.navy : '#9CA3AF' }}>
                  {s.label}
                </span>
              </div>
            )
          })}
        </div>
        <div style={{ marginTop: 28, fontSize: 12, color: '#9CA3AF' }}>This usually takes 3–5 seconds</div>
      </div>
    </div>
  )
}

// ── Upload View (P&L re-upload) ────────────────────────────────────────────────
function UploadView({ platform, reports, onFileUploaded, onSelectReport, onBack, uploading, setUploading }) {
  const fileRef = useRef()
  const [dragging, setDragging] = useState(false)
  const [uploadError, setUploadError] = useState('')

  async function handleFile(file) {
    if (!file) return
    if (!file.name.toLowerCase().match(/\.(xlsx|xls)$/)) {
      setUploadError('Only .xlsx and .xls files are supported for the P&L report')
      return
    }
    setUploadError('')
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    form.append('report_type', 'pl_report')
    try {
      const res = await api.post('/flipkart/upload', form)
      onFileUploaded(res.data, file)
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Upload failed. Please try again.')
      setUploading(false)
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const plReports = reports.filter(function(r) { return r.report_type === 'pl_report' || !r.report_type })

  return (
    <div style={{ padding: '24px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button onClick={onBack} style={{ background: '#F3F4F6', border: 'none', borderRadius: 8, padding: '6px 12px', fontSize: 13, color: '#6B7280', cursor: 'pointer' }}>← Back</button>
        <span style={{ fontSize: 20 }}>{platform.icon}</span>
        <div>
          <div style={{ fontSize: 17, fontWeight: 800, color: P.navy }}>Upload New P&L Report</div>
          <div style={{ fontSize: 12, color: '#6B7280' }}>Seller Hub → Reports → P&L Report → Download Excel</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 10 }}>Upload P&L Report</div>
          <div
            onDragOver={function(e) { e.preventDefault(); setDragging(true) }}
            onDragLeave={function() { setDragging(false) }}
            onDrop={onDrop}
            onClick={function() { !uploading && fileRef.current?.click() }}
            style={{
              border: `2px dashed ${dragging ? P.teal : '#D1D5DB'}`,
              borderRadius: 14, padding: '36px 24px',
              textAlign: 'center',
              background: dragging ? 'rgba(10,191,202,.05)' : '#FAFAFA',
              cursor: uploading ? 'not-allowed' : 'pointer',
              transition: 'all .15s',
            }}
          >
            <input ref={fileRef} type="file" accept=".xlsx,.xls" style={{ display: 'none' }} onChange={function(e) { handleFile(e.target.files[0]) }} />
            {uploading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                <Spinner size={32} />
                <div style={{ fontSize: 13, color: P.teal, fontWeight: 600 }}>Uploading & reading file...</div>
              </div>
            ) : (
              <>
                <div style={{ fontSize: 36, marginBottom: 10 }}>📊</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: P.navy, marginBottom: 4 }}>Drop your Flipkart P&L report here</div>
                <div style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 12 }}>or click to browse — .xlsx / .xls</div>
                <div style={{ display: 'inline-block', padding: '7px 16px', borderRadius: 8, background: P.navy, color: '#fff', fontSize: 12, fontWeight: 600 }}>Choose File</div>
              </>
            )}
          </div>
          {uploadError && <div style={{ marginTop: 8, fontSize: 12, color: P.red }}>{uploadError}</div>}
          <div style={{ marginTop: 14, background: '#F0F9FF', border: '1px solid #BAE6FD', borderRadius: 10, padding: '10px 12px' }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#0369A1', marginBottom: 4 }}>Where to download?</div>
            <div style={{ fontSize: 11, color: '#0369A1', lineHeight: 1.6 }}>
              Seller Hub → Reports → P&L Report → Select date range → Download Excel
            </div>
          </div>
        </div>

        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 10 }}>
            Previous P&L Reports ({plReports.length})
          </div>
          {plReports.length === 0 ? (
            <div style={{ background: '#F9FAFB', borderRadius: 12, padding: '32px 24px', textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
              No P&L reports uploaded yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {plReports.map(function(r) {
                return (
                  <div
                    key={r.id}
                    onClick={function() { r.status === 'done' && onSelectReport(r) }}
                    style={{
                      background: '#fff', border: '1px solid #E8EFF6',
                      borderRadius: 12, padding: '12px 14px',
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      cursor: r.status === 'done' ? 'pointer' : 'default',
                      transition: 'box-shadow .15s',
                    }}
                    onMouseEnter={e => r.status === 'done' && (e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,.08)')}
                    onMouseLeave={e => (e.currentTarget.style.boxShadow = 'none')}
                  >
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: P.navy }}>{r.original_name}</div>
                      <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>
                        {r.report_period || '—'} · {r.row_count_orders || 0} orders · {fmtDate(r.uploaded_at)}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {statusBadge(r.status)}
                      {r.status === 'done' && <span style={{ fontSize: 13, color: P.teal }}>→</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Analytics: Dashboard Tab ───────────────────────────────────────────────────
function DashboardTab({ summary, charts, reconData }) {
  if (!summary) return <div style={{ padding: '48px 0', textAlign: 'center', color: '#9CA3AF' }}>No summary data available.</div>

  const moneyLeak = reconData?.items
    ? reconData.items.reduce(function(acc, iss) { return acc + Math.abs(Math.min(0, Number(iss.variance) || 0)) }, 0)
    : 0

  const netEarnings = summary.net_earnings || 0
  const totalFees   = summary.total_fees   || 0
  const margin      = summary.profit_margin_pct

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
        <HeroCard
          icon="💰" label="Profit / Loss" accent={netEarnings >= 0 ? P.green : P.red}
          value={inr(netEarnings, true)}
          sub={margin != null ? `Margin: ${pct(margin)} of gross sales` : 'Margin not available'}
          note="Net earnings after all platform deductions"
        />
        <HeroCard
          icon="💸" label="Total Charges" accent={P.amber}
          value={inr(totalFees, true)}
          sub={summary.gross_sales ? `${pct((totalFees / summary.gross_sales) * 100)} of gross sales` : 'Platform fees + taxes'}
          note="Commission + shipping + reverse shipping + GST + TCS/TDS"
        />
        <HeroCard
          icon="🚨" label="Potential Money Leak" accent={P.red}
          value={moneyLeak > 0 ? inr(moneyLeak, true) : '₹0'}
          sub={reconData?.summary ? `${reconData.summary.total_issues || 0} anomalies detected` : 'Settlement anomalies'}
          note="Estimated unrecovered settlement gaps — verify before disputing"
          onClick={function() {}}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'Gross Sales',     value: inr(summary.gross_sales, true),     color: P.teal },
          { label: 'Net Sales',       value: inr(summary.net_sales, true),        color: P.blue },
          { label: 'Amount Settled',  value: inr(summary.amount_settled, true),   color: P.green },
          { label: 'Amount Pending',  value: inr(summary.amount_pending, true),   color: P.amber },
          { label: 'Total Orders',    value: summary.total_orders?.toLocaleString() || '0', color: P.navy },
        ].map(function(k) {
          return (
            <div key={k.label} style={{ background: '#fff', border: '1px solid #E8EFF6', borderRadius: 12, padding: '14px 16px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 6 }}>{k.label}</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: k.color }}>{k.value}</div>
            </div>
          )
        })}
      </div>

      {charts && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {charts.fee_breakdown && charts.fee_breakdown.length > 0 && (
            <div style={{ background: '#fff', border: '1px solid #E8EFF6', borderRadius: 14, padding: '18px 20px' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: P.navy, marginBottom: 4 }}>Fee Breakdown</div>
              <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 14 }}>Platform deductions by category</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie data={charts.fee_breakdown} cx="50%" cy="50%" innerRadius={45} outerRadius={75} dataKey="value" paddingAngle={2}>
                      {charts.fee_breakdown.map(function(_, i) { return <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} /> })}
                    </Pie>
                    <Tooltip formatter={function(v) { return inr(v) }} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ flex: 1 }}>
                  {charts.fee_breakdown.slice(0, 6).map(function(f, i) {
                    return (
                      <div key={f.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: PIE_COLORS[i % PIE_COLORS.length], flexShrink: 0 }} />
                          <span style={{ fontSize: 11, color: '#374151' }}>{f.name}</span>
                        </div>
                        <span style={{ fontSize: 11, fontWeight: 600, color: P.navy }}>{inr(f.value, true)}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {charts.revenue_waterfall && charts.revenue_waterfall.length > 0 && (
            <div style={{ background: '#fff', border: '1px solid #E8EFF6', borderRadius: 14, padding: '18px 20px' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: P.navy, marginBottom: 4 }}>Revenue Waterfall</div>
              <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 14 }}>Gross Sales → deductions → Net Earnings</div>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={charts.revenue_waterfall} margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                  <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#9CA3AF' }} tickLine={false} />
                  <YAxis hide />
                  <Tooltip formatter={function(v) { return inr(v) }} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {charts.revenue_waterfall.map(function(entry, i) {
                      return <Cell key={i} fill={entry.type === 'negative' ? P.red : entry.type === 'subtotal' ? P.blue : P.teal} />
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Analytics: SKU Tab ─────────────────────────────────────────────────────────
function SKUTab({ reportId }) {
  const [skus, setSkus] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('net_earnings')
  const [sortDir, setSortDir] = useState('desc')
  const [filterLoss, setFilterLoss] = useState(false)
  const [filterReturn, setFilterReturn] = useState(false)

  useEffect(function() {
    if (!reportId) return
    setLoading(true)
    api.get(`/flipkart/reports/${reportId}/skus?sort_by=${sortBy}&sort_dir=${sortDir}&limit=50${filterLoss ? '&filter_loss=true' : ''}${filterReturn ? '&filter_high_return=true' : ''}`)
      .then(function(r) { setSkus(r.data.items || []) })
      .finally(function() { setLoading(false) })
  }, [reportId, sortBy, sortDir, filterLoss, filterReturn])

  const cols = [
    { key: 'sku_code', label: 'SKU' },
    { key: 'gross_sales', label: 'Gross Sales', fmt: function(v) { return inr(v, true) } },
    { key: 'net_sales', label: 'Net Sales', fmt: function(v) { return inr(v, true) } },
    { key: 'net_earnings', label: 'Net Earnings', fmt: function(v) { return inr(v, true) }, color: function(v) { return v < 0 ? P.red : P.green } },
    { key: 'margin_pct', label: 'Margin', fmt: pct, color: function(v) { return v < 0 ? P.red : v < 5 ? P.amber : P.green } },
    { key: 'total_fees', label: 'Total Fees', fmt: function(v) { return inr(v, true) } },
    { key: 'return_rate_pct', label: 'Return %', fmt: pct, color: function(v) { return v > 30 ? P.red : v > 15 ? P.amber : '#374151' } },
    { key: 'total_orders', label: 'Orders' },
  ]

  if (loading) return <div style={{ padding: '48px 0', display: 'flex', justifyContent: 'center' }}><Spinner size={32} /></div>

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        <button onClick={function() { setFilterLoss(!filterLoss) }} style={{ padding: '6px 12px', borderRadius: 8, background: filterLoss ? 'rgba(232,52,74,.12)' : '#F3F4F6', border: filterLoss ? '1px solid rgba(232,52,74,.3)' : '1px solid transparent', color: filterLoss ? P.red : '#6B7280', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
          Loss-making SKUs only
        </button>
        <button onClick={function() { setFilterReturn(!filterReturn) }} style={{ padding: '6px 12px', borderRadius: 8, background: filterReturn ? 'rgba(233,147,13,.12)' : '#F3F4F6', border: filterReturn ? '1px solid rgba(233,147,13,.3)' : '1px solid transparent', color: filterReturn ? P.amber : '#6B7280', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
          High return rate only
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#6B7280' }}>
          {skus.length} SKUs
        </div>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#F9FAFB' }}>
              {cols.map(function(c) {
                return (
                  <th key={c.key} onClick={function() { if (sortBy === c.key) setSortDir(d => d === 'asc' ? 'desc' : 'asc'); else { setSortBy(c.key); setSortDir('desc') } }} style={{ padding: '10px 12px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '.05em', cursor: 'pointer', whiteSpace: 'nowrap', background: sortBy === c.key ? '#F0F9FF' : '#F9FAFB' }}>
                    {c.label} {sortBy === c.key ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {skus.map(function(row, i) {
              return (
                <tr key={row.id || i} style={{ borderBottom: '1px solid #F3F4F6', background: i % 2 === 0 ? '#fff' : '#FAFAFA' }}>
                  {cols.map(function(c) {
                    const val = row[c.key]
                    const display = c.fmt ? c.fmt(val) : (val ?? '—')
                    const color = c.color ? c.color(val) : '#374151'
                    return <td key={c.key} style={{ padding: '9px 12px', color, fontWeight: c.key === 'sku_code' ? 600 : 400, whiteSpace: 'nowrap', maxWidth: c.key === 'sku_code' ? 160 : 'none', overflow: 'hidden', textOverflow: 'ellipsis' }}>{display}</td>
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Analytics: Reconciliation Tab ──────────────────────────────────────────────
function ReconTab({ reportId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState('')

  useEffect(function() {
    if (!reportId) return
    setLoading(true)
    api.get(`/flipkart/reports/${reportId}/reconciliation`)
      .then(function(r) { setData(r.data) })
      .finally(function() { setLoading(false) })
  }, [reportId])

  if (loading) return <div style={{ padding: '48px 0', display: 'flex', justifyContent: 'center' }}><Spinner size={32} /></div>
  if (!data || !data.items?.length) return <div style={{ padding: '32px 0', textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>No reconciliation issues detected — your settlements look clean!</div>

  const severityColor = { critical: P.red, warning: P.amber, info: P.teal }
  const types = [...new Set(data.items.map(function(i) { return i.issue_type }))]
  const filtered = typeFilter ? data.items.filter(function(i) { return i.issue_type === typeFilter }) : data.items

  return (
    <div>
      {data.summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
          {[
            { label: 'Total Issues',   value: data.summary.total_issues,               color: '#374151' },
            { label: 'Critical',       value: data.summary.critical_issues,             color: P.red },
            { label: 'Warning',        value: data.summary.warning_issues,              color: P.amber },
            { label: 'Est. Impact',    value: inr(data.summary.total_variance_amount, true), color: P.red },
          ].map(function(s) {
            return (
              <div key={s.label} style={{ background: '#fff', border: '1px solid #E8EFF6', borderRadius: 10, padding: '12px 14px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '.07em' }}>{s.label}</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: s.color, marginTop: 4 }}>{s.value ?? '—'}</div>
              </div>
            )
          })}
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        <button onClick={function() { setTypeFilter('') }} style={{ padding: '4px 12px', borderRadius: 8, background: !typeFilter ? P.navy : '#F3F4F6', color: !typeFilter ? '#fff' : '#6B7280', fontSize: 11, fontWeight: 600, border: 'none', cursor: 'pointer' }}>All</button>
        {types.map(function(t) {
          return <button key={t} onClick={function() { setTypeFilter(t) }} style={{ padding: '4px 12px', borderRadius: 8, background: typeFilter === t ? P.navy : '#F3F4F6', color: typeFilter === t ? '#fff' : '#6B7280', fontSize: 11, fontWeight: 600, border: 'none', cursor: 'pointer' }}>{t.replace(/_/g, ' ')}</button>
        })}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {filtered.slice(0, 50).map(function(iss) {
          const sc = severityColor[iss.severity] || P.teal
          return (
            <div key={iss.id} style={{ background: '#fff', border: '1px solid #E8EFF6', borderRadius: 12, padding: '12px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: sc, background: sc + '18', padding: '2px 8px', borderRadius: 6, textTransform: 'uppercase' }}>{iss.severity}</span>
                  <span style={{ fontSize: 11, color: '#6B7280' }}>{iss.issue_type?.replace(/_/g, ' ')}</span>
                  {iss.order_id && <span style={{ fontSize: 11, color: '#9CA3AF', fontFamily: 'monospace' }}>{iss.order_id}</span>}
                </div>
                <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.5 }}>{iss.description}</div>
              </div>
              {iss.variance != null && (
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: iss.variance < 0 ? P.red : P.green }}>{inr(Math.abs(iss.variance), true)}</div>
                  <div style={{ fontSize: 10, color: '#9CA3AF' }}>potential gap</div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Analytics: Insights Tab ────────────────────────────────────────────────────
function InsightsTab({ reportId }) {
  const [insights, setInsights] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(function() {
    if (!reportId) return
    api.get(`/flipkart/reports/${reportId}/insights`)
      .then(function(r) { setInsights(r.data.insights || []) })
      .finally(function() { setLoading(false) })
  }, [reportId])

  if (loading) return <div style={{ padding: '48px 0', display: 'flex', justifyContent: 'center' }}><Spinner size={32} /></div>
  if (!insights.length) return <div style={{ padding: '32px 0', textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>No insights generated yet.</div>

  const iconMap = { critical: '🚨', warning: '⚠️', info: 'ℹ️', positive: '✅' }
  const colorMap = { critical: P.red, warning: P.amber, info: P.teal, positive: P.green }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {insights.map(function(ins, i) {
        const c = colorMap[ins.type] || P.teal
        return (
          <div key={i} style={{ background: '#fff', border: '1px solid #E8EFF6', borderLeft: `4px solid ${c}`, borderRadius: 12, padding: '14px 16px', display: 'flex', gap: 12 }}>
            <span style={{ fontSize: 20, flexShrink: 0 }}>{iconMap[ins.type] || ins.icon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#374151', lineHeight: 1.5 }}>{ins.message}</div>
              {ins.data && (
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  {Object.entries(ins.data).map(function([k, v]) {
                    return <span key={k} style={{ background: '#F3F4F6', borderRadius: 6, padding: '2px 8px', fontSize: 11, color: '#6B7280' }}>{k}: {String(v)}</span>
                  })}
                </div>
              )}
            </div>
            <div style={{ fontSize: 10, fontWeight: 700, color: c, background: c + '15', padding: '3px 8px', borderRadius: 6, alignSelf: 'flex-start', whiteSpace: 'nowrap' }}>
              {ins.type?.toUpperCase()}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Analytics View (full tabbed dashboard) ─────────────────────────────────────
function AnalyticsView({ platform, reports, selectedReport, onSelectReport, onNewUpload, onManageDocs }) {
  const [tab, setTab] = useState('dashboard')
  const [summary, setSummary] = useState(null)
  const [charts, setCharts] = useState(null)
  const [reconData, setReconData] = useState(null)
  const [loadingData, setLoadingData] = useState(false)

  useEffect(function() {
    if (!selectedReport?.id) return
    setLoadingData(true)
    setSummary(null); setCharts(null); setReconData(null)
    Promise.all([
      api.get(`/flipkart/reports/${selectedReport.id}/summary`),
      api.get(`/flipkart/reports/${selectedReport.id}/charts`),
      api.get(`/flipkart/reports/${selectedReport.id}/reconciliation`),
    ])
      .then(function([sRes, cRes, rRes]) {
        setSummary(sRes.data)
        setCharts(cRes.data)
        setReconData(rRes.data)
      })
      .finally(function() { setLoadingData(false) })
  }, [selectedReport?.id])

  const TABS = [
    { id: 'dashboard', label: 'Dashboard',       icon: '⚡' },
    { id: 'skus',      label: 'SKU Analysis',    icon: '📦' },
    { id: 'recon',     label: 'Reconciliation',  icon: '🔬' },
    { id: 'insights',  label: 'Insights',        icon: '💡' },
  ]

  // Only show P&L reports in the dropdown
  const plReports = reports.filter(function(r) { return r.report_type === 'pl_report' || !r.report_type })

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 18 }}>{platform.icon}</span>
        <div style={{ fontSize: 16, fontWeight: 800, color: P.navy }}>{platform.label} Intelligence</div>

        <select
          value={selectedReport?.id || ''}
          onChange={function(e) {
            const r = plReports.find(function(r) { return r.id === e.target.value })
            if (r) onSelectReport(r)
          }}
          style={{ marginLeft: 8, padding: '6px 12px', borderRadius: 8, border: '1px solid #E5E7EB', fontSize: 12, color: P.navy, background: '#fff' }}
        >
          {plReports.filter(function(r) { return r.status === 'done' }).map(function(r) {
            return <option key={r.id} value={r.id}>{r.original_name} — {r.report_period || fmtDate(r.uploaded_at)}</option>
          })}
        </select>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button onClick={function() { onManageDocs(true) }} style={{ padding: '7px 14px', borderRadius: 8, background: '#F0F9FF', border: '1px solid #BAE6FD', color: '#0369A1', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
            📂 Manage Documents
          </button>
          <button onClick={onNewUpload} style={{ padding: '7px 14px', borderRadius: 8, background: '#F3F4F6', border: 'none', color: '#6B7280', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
            + Upload New Report
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 4, borderBottom: '2px solid #E8EFF6', marginBottom: 20 }}>
        {TABS.map(function(t) {
          return (
            <button key={t.id} onClick={function() { setTab(t.id) }} style={{ padding: '8px 16px', borderRadius: '8px 8px 0 0', border: 'none', background: tab === t.id ? '#fff' : 'transparent', color: tab === t.id ? P.navy : '#6B7280', fontSize: 13, fontWeight: tab === t.id ? 700 : 400, cursor: 'pointer', borderBottom: tab === t.id ? '2px solid ' + P.teal : '2px solid transparent', marginBottom: -2, display: 'flex', alignItems: 'center', gap: 6 }}>
              {t.icon} {t.label}
            </button>
          )
        })}
      </div>

      {loadingData ? (
        <div style={{ padding: '48px 0', display: 'flex', justifyContent: 'center' }}><Spinner size={32} /></div>
      ) : (
        <>
          {tab === 'dashboard'  && <DashboardTab summary={summary} charts={charts} reconData={reconData} />}
          {tab === 'skus'       && <SKUTab reportId={selectedReport?.id} />}
          {tab === 'recon'      && <ReconTab reportId={selectedReport?.id} />}
          {tab === 'insights'   && <InsightsTab reportId={selectedReport?.id} />}
        </>
      )}
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────
function ReconEngine() {
  const [platform, setPlatform]   = useState(null)
  // views: platform_select | docs_gate | upload | processing | analytics
  const [view, setView]           = useState('platform_select')
  const [reports, setReports]     = useState([])
  const [selectedReport, setSelectedReport] = useState(null)

  const [uploading, setUploading]         = useState(false)
  const [pendingReport, setPendingReport] = useState(null)
  const [confirming, setConfirming]       = useState(false)
  const [processingId, setProcessingId]   = useState(null)
  const [processingFilename, setProcessingFilename] = useState('')
  const [managingDocs, setManagingDocs]   = useState(false)

  const pollRef = useRef(null)

  const fetchReports = useCallback(function() {
    if (!platform) return
    if (platform.id === 'flipkart') {
      api.get('/flipkart/reports').then(function(r) {
        const list = r.data.items || []
        setReports(list)
        const plDone = list.find(function(r) { return r.status === 'done' && (r.report_type === 'pl_report' || !r.report_type) })
        if (plDone && !selectedReport) {
          setSelectedReport(plDone)
        }
      })
    }
  }, [platform])

  useEffect(function() { fetchReports() }, [fetchReports])

  // Poll processing status
  useEffect(function() {
    if (!processingId) return
    pollRef.current = setInterval(function() {
      api.get('/flipkart/reports/' + processingId).then(function(r) {
        const status = r.data.status
        if (status === 'done') {
          clearInterval(pollRef.current)
          fetchReports()
          setTimeout(function() {
            setSelectedReport(r.data)
            setProcessingId(null)
            setView('analytics')
          }, 1200)
        } else if (status === 'failed') {
          clearInterval(pollRef.current)
          setProcessingId(null)
          setView('upload')
          fetchReports()
        }
      })
    }, 2000)
    return function() { clearInterval(pollRef.current) }
  }, [processingId, fetchReports])

  function handlePlatformSelect(p) {
    setPlatform(p)
    setReports([])
    setSelectedReport(null)
    setManagingDocs(false)
    setView('docs_gate')
  }

  function handleAllDocsUploaded() {
    // Check if we have a processed P&L report to show
    const plDone = reports.find(function(r) { return r.status === 'done' && (r.report_type === 'pl_report' || !r.report_type) })
    if (plDone) {
      setSelectedReport(plDone)
      setView('analytics')
    } else {
      setView('upload')
    }
  }

  function handleFileUploaded(response, file) {
    setUploading(false)
    setPendingReport({ id: response.id, file, preview: response.preview })
    fetchReports()
  }

  async function handleConfirm() {
    if (!pendingReport) return
    const reportId = pendingReport.id
    setProcessingFilename(pendingReport.file?.name || 'your report')
    setConfirming(true)
    try {
      await api.post('/flipkart/reports/' + reportId + '/confirm')
      setPendingReport(null)
      setConfirming(false)
      setProcessingId(reportId)
      setView('processing')
    } catch (e) {
      setConfirming(false)
    }
  }

  function handleCancelPreview() {
    setPendingReport(null)
    fetchReports()
  }

  return (
    <div style={{ padding: '24px 32px', minHeight: '100vh', background: P.bg }}>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 22, fontWeight: 800, color: P.navy }}>Settlement Intelligence</div>
        <div style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>
          Upload your marketplace reports · Detect payout anomalies · Identify potential money leakage
        </div>
      </div>

      <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #E8EFF6', padding: '24px 28px' }}>
        {view === 'platform_select' && (
          <PlatformSelect onSelect={handlePlatformSelect} />
        )}

        {view === 'docs_gate' && platform && (
          <DocsGate
            platform={platform}
            onAllUploaded={handleAllDocsUploaded}
            onPlFileUploaded={handleFileUploaded}
            onBack={function() { setPlatform(null); setView('platform_select') }}
            preventAutoProceed={managingDocs}
          />
        )}

        {view === 'upload' && platform && (
          <UploadView
            platform={platform}
            reports={reports}
            uploading={uploading}
            setUploading={setUploading}
            onFileUploaded={handleFileUploaded}
            onSelectReport={function(r) { setSelectedReport(r); setView('analytics') }}
            onBack={function() { setManagingDocs(true); setView('docs_gate') }}
          />
        )}

        {view === 'processing' && platform && (
          <ProcessingView filename={processingFilename || 'your report'} />
        )}

        {view === 'analytics' && platform && selectedReport && (
          <AnalyticsView
            platform={platform}
            reports={reports}
            selectedReport={selectedReport}
            onSelectReport={function(r) { setSelectedReport(r) }}
            onNewUpload={function() { setView('upload') }}
            onManageDocs={function(manage) { setManagingDocs(!!manage); setView('docs_gate') }}
          />
        )}
      </div>

      {pendingReport && (
        <PreviewModal
          file={pendingReport.file}
          preview={pendingReport.preview}
          onConfirm={handleConfirm}
          onCancel={handleCancelPreview}
          confirming={confirming}
        />
      )}

      <div style={{ marginTop: 16, fontSize: 11, color: '#9CA3AF', lineHeight: 1.6 }}>
        All settlement analysis figures represent <em>potential discrepancies</em> derived from your uploaded data.
        ClearSettle does not guarantee recovery. Verify all anomalies independently before raising disputes with marketplaces.
      </div>
    </div>
  )
}

export default ReconEngine
