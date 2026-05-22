import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import useAuthStore from '../store/authStore'

// ── Constants ─────────────────────────────────────────────────────────────────

const PALETTE = {
  teal:   '#0ABFCA',
  navy:   '#0D1F35',
  green:  '#10B981',
  red:    '#E8344A',
  amber:  '#E9930D',
  purple: '#8B5CF6',
  blue:   '#3B82F6',
  pink:   '#EC4899',
  slate:  '#8FA5BD',
}

const PIE_COLORS = [
  PALETTE.teal, PALETTE.amber, PALETTE.red, PALETTE.purple,
  PALETTE.green, PALETTE.blue, PALETTE.pink, '#F97316', '#14B8A6',
]

const ISSUE_LABELS = {
  missing_settlement: { label: 'Missing Settlement', icon: '🔴', color: PALETTE.red },
  partial_settlement: { label: 'Partial Settlement', icon: '🟠', color: PALETTE.amber },
  mismatch:           { label: 'Mismatch',           icon: '⚠️',  color: PALETTE.amber },
  delayed_payout:     { label: 'Delayed Payout',     icon: '⏰',  color: PALETTE.purple },
  excess_deduction:   { label: 'Excess Deduction',   icon: '📉',  color: PALETTE.red },
}

const SEVERITY_STYLE = {
  critical: { bg: 'rgba(232,52,74,.13)', color: PALETTE.red,   border: 'rgba(232,52,74,.3)' },
  warning:  { bg: 'rgba(233,147,13,.13)', color: PALETTE.amber, border: 'rgba(233,147,13,.3)' },
  info:     { bg: 'rgba(10,191,202,.13)', color: PALETTE.teal,  border: 'rgba(10,191,202,.3)' },
  positive: { bg: 'rgba(16,185,129,.13)', color: PALETTE.green, border: 'rgba(16,185,129,.3)' },
}

// ── Formatters ────────────────────────────────────────────────────────────────

const inr = (v, compact = false) => {
  if (v == null) return '—'
  const n = Number(v)
  if (compact) {
    if (Math.abs(n) >= 1e7)  return `₹${(n / 1e7).toFixed(2)}Cr`
    if (Math.abs(n) >= 1e5)  return `₹${(n / 1e5).toFixed(1)}L`
    if (Math.abs(n) >= 1e3)  return `₹${(n / 1e3).toFixed(1)}K`
  }
  return `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

const pct = (v) => v == null ? '—' : `${Number(v).toFixed(1)}%`
const num = (v) => v == null ? '—' : Number(v).toLocaleString('en-IN')

// ── API helper ────────────────────────────────────────────────────────────────

function api(token, path, opts = {}) {
  return fetch(`/api/flipkart${path}`, {
    ...opts,
    headers: {
      ...(opts.body && !(opts.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      Authorization: `Bearer ${token}`,
      ...(opts.headers || {}),
    },
  }).then(async r => {
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${r.status}`)
    }
    return r.json()
  })
}

// ── Shared mini components ────────────────────────────────────────────────────

function Spinner({ size = 20 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      border: `${Math.max(2, size / 8)}px solid rgba(10,191,202,.2)`,
      borderTop: `${Math.max(2, size / 8)}px solid #0ABFCA`,
      animation: 'fk-spin 1s linear infinite', flexShrink: 0,
    }} />
  )
}

function KpiCard({ label, value, sub, color = PALETTE.teal, icon, delta, onClick }) {
  const [hover, setHover] = useState(false)
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: '#fff',
        borderRadius: 14,
        padding: '18px 20px',
        border: `1px solid ${hover && onClick ? color : '#E8EFF6'}`,
        flex: 1,
        minWidth: 150,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all .15s',
        boxShadow: hover && onClick ? `0 4px 20px ${color}22` : 'none',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{
        position: 'absolute', top: 0, left: 0, width: 4, height: '100%',
        background: `linear-gradient(180deg, ${color}, ${color}88)`,
        borderRadius: '4px 0 0 4px',
      }} />
      <div style={{ paddingLeft: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          {icon && <span style={{ fontSize: 16 }}>{icon}</span>}
          <div style={{ fontSize: 11, color: PALETTE.slate, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em' }}>
            {label}
          </div>
        </div>
        <div style={{ fontSize: 22, fontWeight: 800, color, lineHeight: 1.1 }}>{value}</div>
        {sub && <div style={{ fontSize: 11, color: PALETTE.slate, marginTop: 4 }}>{sub}</div>}
        {delta != null && (
          <div style={{ fontSize: 11, color: delta >= 0 ? PALETTE.green : PALETTE.red, marginTop: 3, fontWeight: 600 }}>
            {delta >= 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}%
          </div>
        )}
      </div>
    </div>
  )
}

function SectionHeader({ title, subtitle }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 15, fontWeight: 800, color: PALETTE.navy }}>{title}</div>
      {subtitle && <div style={{ fontSize: 12, color: PALETTE.slate, marginTop: 2 }}>{subtitle}</div>}
    </div>
  )
}

function EmptyState({ icon, message, sub }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 14, padding: '48px 24px', textAlign: 'center',
      border: '1px solid #E8EFF6', color: PALETTE.slate,
    }}>
      <div style={{ fontSize: 40, marginBottom: 12 }}>{icon || '📭'}</div>
      <div style={{ fontSize: 14, fontWeight: 600, color: '#4B6080' }}>{message}</div>
      {sub && <div style={{ fontSize: 12, marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

// ── Tab: Upload ───────────────────────────────────────────────────────────────

function UploadTab({ token, reports, onRefresh, onSelectReport }) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const inputRef = useRef()

  async function handleUpload(file) {
    if (!file) return
    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      setError('Only .xlsx and .xls files are supported.')
      return
    }
    setUploading(true)
    setError(null)
    const fd = new FormData()
    fd.append('file', file)
    try {
      await fetch('/api/flipkart/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      }).then(async r => {
        if (!r.ok) throw new Error((await r.json()).detail || 'Upload failed')
        return r.json()
      })
      onRefresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id, e) {
    e.stopPropagation()
    if (!window.confirm('Delete this report and all its data?')) return
    setDeleting(id)
    try {
      await fetch(`/api/flipkart/reports/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      onRefresh()
    } finally {
      setDeleting(null)
    }
  }

  // Poll for status changes on processing reports
  useEffect(() => {
    const processing = reports.filter(r => r.status === 'pending' || r.status === 'processing')
    if (!processing.length) return
    const t = setTimeout(onRefresh, 2500)
    return () => clearTimeout(t)
  }, [reports])

  const STATUS_STYLE = {
    done:       { bg: 'rgba(16,185,129,.12)', color: PALETTE.green },
    processing: { bg: 'rgba(233,147,13,.12)', color: PALETTE.amber },
    pending:    { bg: 'rgba(10,191,202,.12)', color: PALETTE.teal },
    failed:     { bg: 'rgba(232,52,74,.12)',  color: PALETTE.red },
  }

  return (
    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
      {/* Upload card */}
      <div style={{ flex: '0 0 340px', background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #E8EFF6' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg,#0ABFCA22,#0ABFCA44)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>📊</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: PALETTE.navy }}>Upload Flipkart Report</div>
            <div style={{ fontSize: 11, color: PALETTE.slate }}>P&L Export from Seller Hub</div>
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); handleUpload(e.dataTransfer.files[0]) }}
          onClick={() => !uploading && inputRef.current?.click()}
          style={{
            border: `2px dashed ${dragging ? PALETTE.teal : '#D1DDE8'}`,
            borderRadius: 12,
            padding: '36px 20px',
            textAlign: 'center',
            cursor: uploading ? 'wait' : 'pointer',
            background: dragging ? 'rgba(10,191,202,.04)' : '#F7FAFC',
            transition: 'all .15s',
            marginBottom: 16,
          }}
        >
          <input ref={inputRef} type="file" accept=".xlsx,.xls" style={{ display: 'none' }}
            onChange={e => handleUpload(e.target.files[0])} />
          {uploading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
              <Spinner size={32} />
              <div style={{ fontSize: 13, color: '#4B6080', fontWeight: 500 }}>Uploading & processing…</div>
            </div>
          ) : (
            <>
              <div style={{ fontSize: 40, marginBottom: 10 }}>📁</div>
              <div style={{ fontSize: 14, color: '#4B6080', fontWeight: 600 }}>
                Drop your Flipkart P&L file here
              </div>
              <div style={{ fontSize: 11, color: PALETTE.slate, marginTop: 6 }}>
                or click to browse · .xlsx, .xls only
              </div>
            </>
          )}
        </div>

        {error && (
          <div style={{ background: 'rgba(232,52,74,.08)', border: '1px solid rgba(232,52,74,.2)', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: PALETTE.red, marginBottom: 12 }}>
            {error}
          </div>
        )}

        {/* How it works */}
        <div style={{ background: '#F7FAFC', borderRadius: 10, padding: '14px 16px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 10 }}>
            What happens after upload
          </div>
          {[
            ['📤', 'Excel parsed — all sheets detected'],
            ['🔄', 'Data normalized into unified schema'],
            ['💡', 'Analytics computed automatically'],
            ['🔍', 'Reconciliation engine runs'],
            ['⚡', 'Dashboard updates instantly'],
          ].map(([icon, text]) => (
            <div key={text} style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'flex-start' }}>
              <span style={{ fontSize: 13, flexShrink: 0 }}>{icon}</span>
              <span style={{ fontSize: 12, color: '#4B6080' }}>{text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Reports list */}
      <div style={{ flex: 1, minWidth: 320 }}>
        <SectionHeader title={`Uploaded Reports (${reports.length})`} subtitle="Click a processed report to view analytics" />
        {reports.length === 0 ? (
          <EmptyState icon="📋" message="No reports uploaded yet" sub="Upload your first Flipkart P&L report to get started" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {reports.map(r => {
              const sc = STATUS_STYLE[r.status] || STATUS_STYLE.pending
              const isReady = r.status === 'done'
              return (
                <div
                  key={r.id}
                  onClick={() => isReady && onSelectReport(r.id)}
                  style={{
                    background: '#fff', borderRadius: 14,
                    padding: '16px 20px', border: '1px solid #E8EFF6',
                    cursor: isReady ? 'pointer' : 'default',
                    transition: 'all .15s',
                  }}
                  onMouseEnter={e => isReady && (e.currentTarget.style.borderColor = PALETTE.teal)}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = '#E8EFF6')}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ fontSize: 28, flexShrink: 0 }}>📊</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: PALETTE.navy, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 260 }}>
                          {r.original_name}
                        </div>
                        <span style={{ ...sc, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700 }}>
                          {r.status === 'processing' ? '⚙️ processing…' : r.status}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: PALETTE.slate }}>
                        {r.file_size_bytes ? `${(r.file_size_bytes / 1024).toFixed(0)} KB` : ''}
                        {r.row_count_sku != null ? ` · ${r.row_count_sku} SKUs` : ''}
                        {r.row_count_orders != null ? ` · ${r.row_count_orders} orders` : ''}
                        {r.sheets_parsed ? ` · ${r.sheets_parsed}` : ''}
                      </div>
                      <div style={{ fontSize: 10, color: PALETTE.slate, marginTop: 2 }}>
                        Uploaded {new Date(r.uploaded_at).toLocaleString('en-IN')}
                        {r.processed_at ? ` · Processed ${new Date(r.processed_at).toLocaleString('en-IN')}` : ''}
                      </div>
                      {r.error_message && (
                        <div style={{ fontSize: 11, color: PALETTE.red, marginTop: 4 }}>{r.error_message}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
                      {isReady && (
                        <button
                          onClick={e => { e.stopPropagation(); onSelectReport(r.id) }}
                          style={{ padding: '5px 12px', borderRadius: 7, background: 'rgba(10,191,202,.1)', color: PALETTE.teal, border: '1px solid rgba(10,191,202,.2)', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}
                        >
                          View →
                        </button>
                      )}
                      <button
                        onClick={e => handleDelete(r.id, e)}
                        disabled={deleting === r.id}
                        style={{ padding: '5px 10px', borderRadius: 7, background: 'rgba(232,52,74,.08)', color: PALETTE.red, border: 'none', fontSize: 12, cursor: 'pointer' }}
                      >
                        {deleting === r.id ? '…' : '✕'}
                      </button>
                    </div>
                  </div>
                  {(r.status === 'pending' || r.status === 'processing') && (
                    <div style={{ marginTop: 10, height: 3, background: '#F1F5F9', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', background: `linear-gradient(90deg, ${PALETTE.teal}, ${PALETTE.teal}88)`, borderRadius: 2, animation: 'fk-progress 2s ease-in-out infinite' }} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tab: Dashboard (KPIs + Charts) ────────────────────────────────────────────

function DashboardTab({ token, reportId }) {
  const [summary, setSummary] = useState(null)
  const [charts, setCharts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pollingCount, setPollingCount] = useState(0)

  const load = useCallback(async () => {
    try {
      const [sum, ch] = await Promise.all([
        api(token, `/reports/${reportId}/summary`),
        api(token, `/reports/${reportId}/charts`).catch(() => null),
      ])
      if (sum.status && sum.status !== 'done') {
        if (pollingCount < 30) {
          setTimeout(() => setPollingCount(p => p + 1), 2000)
        }
      }
      setSummary(sum)
      setCharts(ch)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [token, reportId, pollingCount])

  useEffect(() => { setLoading(true); load() }, [reportId, pollingCount])

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}><Spinner size={40} /></div>
  if (error) return <div style={{ color: PALETTE.red, padding: 24 }}>{error}</div>
  if (!summary) return null

  if (summary.status && summary.status !== 'done') {
    return (
      <div style={{ background: '#fff', borderRadius: 16, padding: 48, textAlign: 'center', border: '1px solid #E8EFF6' }}>
        <Spinner size={40} />
        <div style={{ fontSize: 14, fontWeight: 600, color: '#4B6080', marginTop: 16 }}>
          Report is being processed…
        </div>
        <div style={{ fontSize: 12, color: PALETTE.slate, marginTop: 4 }}>This usually takes under 30 seconds.</div>
      </div>
    )
  }

  const feeBreakdown = charts?.fee_breakdown || []
  const waterfall    = charts?.revenue_waterfall || []

  return (
    <div>
      {/* KPI Cards row 1 */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <KpiCard label="Gross Sales"    value={inr(summary.gross_sales, true)}    icon="💰" color={PALETTE.teal}  sub="Total revenue before deductions" />
        <KpiCard label="Net Sales"      value={inr(summary.net_sales, true)}      icon="📊" color={PALETTE.blue}  sub="After returns & cancellations" />
        <KpiCard label="Net Earnings"   value={inr(summary.net_earnings, true)}   icon="🏆" color={PALETTE.green} sub="After all fees & taxes" />
        <KpiCard label="Total Fees"     value={inr(summary.total_fees, true)}     icon="💳" color={PALETTE.red}   sub="All platform deductions" />
      </div>

      {/* KPI Cards row 2 */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
        <KpiCard label="Amount Settled"  value={inr(summary.amount_settled, true)}  icon="✅" color={PALETTE.green}  sub="Received in bank" />
        <KpiCard label="Amount Pending"  value={inr(summary.amount_pending, true)}  icon="⏳" color={PALETTE.amber}  sub="Awaiting settlement" />
        <KpiCard label="Profit Margin"   value={pct(summary.profit_margin_pct)}     icon="📈" color={summary.profit_margin_pct < 5 ? PALETTE.red : summary.profit_margin_pct > 15 ? PALETTE.green : PALETTE.amber} sub="Net earnings / gross sales" />
        <KpiCard label="Return Rate"     value={pct(summary.return_rate_pct)}       icon="↩️" color={summary.return_rate_pct > 15 ? PALETTE.red : PALETTE.teal} sub="Returned / total orders" />
        <KpiCard label="Cancel Rate"     value={pct(summary.cancellation_rate_pct)} icon="❌" color={summary.cancellation_rate_pct > 10 ? PALETTE.amber : PALETTE.teal} sub="Cancelled / total orders" />
        <KpiCard label="Total Orders"    value={num(summary.total_orders)}           icon="📦" color={PALETTE.teal} sub={`${num(summary.total_returned_orders)} returned`} />
      </div>

      {/* Charts row */}
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 24 }}>
        {/* Fee Breakdown Pie */}
        {feeBreakdown.length > 0 && (
          <div style={{ flex: '1 1 340px', background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #E8EFF6' }}>
            <SectionHeader title="Fee Breakdown" subtitle="Platform deductions by category" />
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <ResponsiveContainer width={180} height={180}>
                <PieChart>
                  <Pie data={feeBreakdown} dataKey="value" cx="50%" cy="50%" outerRadius={80} stroke="none">
                    {feeBreakdown.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={v => inr(v)} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ flex: 1 }}>
                {feeBreakdown.map((item, i) => (
                  <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 3, background: PIE_COLORS[i % PIE_COLORS.length], flexShrink: 0 }} />
                    <div style={{ flex: 1, fontSize: 12, color: '#4B6080' }}>{item.name}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: PALETTE.navy }}>{inr(item.value, true)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Revenue Waterfall */}
        {waterfall.length > 0 && (
          <div style={{ flex: '2 1 440px', background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #E8EFF6' }}>
            <SectionHeader title="Revenue Waterfall" subtitle="Gross Sales → deductions → Net Earnings" />
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={waterfall} margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#8FA5BD' }} angle={-25} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 10, fill: '#8FA5BD' }} tickFormatter={v => inr(v, true)} />
                <Tooltip formatter={v => inr(v)} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {waterfall.map((entry, i) => (
                    <Cell key={i} fill={
                      entry.type === 'total'    ? PALETTE.teal :
                      entry.type === 'subtotal' ? PALETTE.blue :
                      PALETTE.red
                    } />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Summary financials table */}
      <div style={{ background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #E8EFF6' }}>
        <SectionHeader title="Financial Summary" subtitle="Complete P&L breakdown" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 1, background: '#E8EFF6', borderRadius: 8, overflow: 'hidden' }}>
          {[
            ['Gross Sales',            summary.gross_sales,            PALETTE.teal],
            ['Returns',                summary.returns && -Math.abs(summary.returns), PALETTE.red],
            ['Cancellations',          summary.cancellations && -Math.abs(summary.cancellations), PALETTE.red],
            ['Net Sales',              summary.net_sales,              PALETTE.blue],
            ['Commission',             summary.commission && -Math.abs(summary.commission), PALETTE.red],
            ['Shipping Charges',       summary.shipping_charges && -Math.abs(summary.shipping_charges), PALETTE.amber],
            ['Reverse Shipping',       summary.reverse_shipping && -Math.abs(summary.reverse_shipping), PALETTE.amber],
            ['Collection Fees',        summary.collection_fees && -Math.abs(summary.collection_fees), PALETTE.amber],
            ['Fixed Fees',             summary.fixed_fees && -Math.abs(summary.fixed_fees), PALETTE.amber],
            ['GST on Services',        summary.gst_on_fees && -Math.abs(summary.gst_on_fees), PALETTE.purple],
            ['TCS',                    summary.tcs && -Math.abs(summary.tcs), PALETTE.purple],
            ['TDS',                    summary.tds && -Math.abs(summary.tds), PALETTE.purple],
            ['Net Earnings',           summary.net_earnings,           PALETTE.green],
            ['Amount Settled',         summary.amount_settled,         PALETTE.green],
            ['Amount Pending',         summary.amount_pending,         PALETTE.amber],
          ].filter(([, v]) => v != null).map(([label, value, color]) => (
            <div key={label} style={{ background: '#fff', padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, color: '#4B6080' }}>{label}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color }}>{inr(value)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Tab: SKU Analytics ────────────────────────────────────────────────────────

function SKUTab({ token, reportId }) {
  const [data, setData] = useState(null)
  const [charts, setCharts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('net_earnings')
  const [sortDir, setSortDir] = useState('desc')
  const [filterLoss, setFilterLoss] = useState(false)
  const [filterHighReturn, setFilterHighReturn] = useState(false)
  const [page, setPage] = useState(1)
  const [view, setView] = useState('table')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ sort_by: sortBy, sort_dir: sortDir, page, limit: 50 })
      if (filterLoss)       params.set('filter_loss', 'true')
      if (filterHighReturn) params.set('filter_high_return', 'true')
      const [d, ch] = await Promise.all([
        api(token, `/reports/${reportId}/skus?${params}`),
        charts ? Promise.resolve(charts) : api(token, `/reports/${reportId}/charts`).catch(() => null),
      ])
      setData(d)
      if (!charts) setCharts(ch)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [token, reportId, sortBy, sortDir, filterLoss, filterHighReturn, page])

  useEffect(() => { load() }, [load])

  function toggleSort(field) {
    if (sortBy === field) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(field); setSortDir('desc') }
    setPage(1)
  }

  const SortIcon = ({ field }) => (
    <span style={{ fontSize: 10, opacity: sortBy === field ? 1 : 0.3, marginLeft: 4 }}>
      {sortBy === field && sortDir === 'desc' ? '▼' : '▲'}
    </span>
  )

  const skuCharts = charts?.sku_charts || {}
  const catCharts = charts?.category_breakdown || []

  return (
    <div>
      {/* Controls */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', background: '#fff', borderRadius: 10, border: '1px solid #E8EFF6', padding: 3, gap: 2 }}>
          {['table', 'charts'].map(v => (
            <button key={v} onClick={() => setView(v)} style={{
              padding: '6px 14px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
              background: view === v ? 'linear-gradient(135deg,#0ABFCA,#088F99)' : 'transparent',
              color: view === v ? '#fff' : '#4B6080',
            }}>
              {v === 'table' ? '📋 Table' : '📊 Charts'}
            </button>
          ))}
        </div>

        <button
          onClick={() => { setFilterLoss(v => !v); setPage(1) }}
          style={{
            padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer',
            background: filterLoss ? 'rgba(232,52,74,.12)' : '#fff',
            color: filterLoss ? PALETTE.red : '#4B6080',
            border: `1px solid ${filterLoss ? 'rgba(232,52,74,.3)' : '#D1DDE8'}`,
          }}
        >
          🔴 Loss-making only
        </button>

        <button
          onClick={() => { setFilterHighReturn(v => !v); setPage(1) }}
          style={{
            padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer',
            background: filterHighReturn ? 'rgba(233,147,13,.12)' : '#fff',
            color: filterHighReturn ? PALETTE.amber : '#4B6080',
            border: `1px solid ${filterHighReturn ? 'rgba(233,147,13,.3)' : '#D1DDE8'}`,
          }}
        >
          ↩️ High returns only
        </button>

        {data && (
          <div style={{ fontSize: 12, color: PALETTE.slate, marginLeft: 'auto' }}>
            {data.total} SKUs
          </div>
        )}
      </div>

      {view === 'charts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginBottom: 24 }}>
          {/* Top profitable SKUs */}
          {skuCharts.top_profitable?.length > 0 && (
            <div style={{ background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #E8EFF6' }}>
              <SectionHeader title="Top Profitable SKUs" subtitle="Net earnings by SKU" />
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={skuCharts.top_profitable.slice(0, 12)} layout="vertical" margin={{ left: 20, right: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={v => inr(v, true)} />
                  <YAxis type="category" dataKey="title" width={130} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={v => inr(v)} />
                  <Bar dataKey="net_earnings" fill={PALETTE.teal} radius={[0, 4, 4, 0]} name="Net Earnings" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Loss-making SKUs */}
          {skuCharts.top_loss_making?.length > 0 && (
            <div style={{ background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #E8EFF6' }}>
              <SectionHeader title="Loss-Making SKUs" subtitle="SKUs with negative net earnings" />
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={skuCharts.top_loss_making.slice(0, 10)} layout="vertical" margin={{ left: 20, right: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={v => inr(v, true)} />
                  <YAxis type="category" dataKey="title" width={130} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={v => inr(v)} />
                  <ReferenceLine x={0} stroke={PALETTE.red} />
                  <Bar dataKey="net_earnings" fill={PALETTE.red} radius={[0, 4, 4, 0]} name="Net Earnings" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Category breakdown */}
          {catCharts.length > 0 && (
            <div style={{ background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #E8EFF6' }}>
              <SectionHeader title="Category P&L" subtitle="Gross sales vs net earnings by category" />
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={catCharts.slice(0, 10)} margin={{ bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="category" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={50} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={v => inr(v, true)} />
                  <Tooltip formatter={v => inr(v)} />
                  <Legend />
                  <Bar dataKey="gross_sales"  fill={PALETTE.teal}  name="Gross Sales"  radius={[3, 3, 0, 0]} />
                  <Bar dataKey="net_earnings" fill={PALETTE.green} name="Net Earnings" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {view === 'table' && (
        <>
          {loading && !data ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner /></div>
          ) : (
            <>
              <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #E8EFF6', overflow: 'hidden' }}>
                {/* Table header */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '200px 1fr 90px 100px 90px 90px 90px 90px',
                  background: '#F7FAFC', padding: '10px 16px',
                  borderBottom: '1px solid #E8EFF6',
                }}>
                  {[
                    ['SKU Code', 'sku_code'],
                    ['Product', null],
                    ['Orders', 'total_orders'],
                    ['Gross Sales', 'gross_sales'],
                    ['Net Earnings', 'net_earnings'],
                    ['Margin %', 'margin_pct'],
                    ['Return %', 'return_rate_pct'],
                    ['Flags', null],
                  ].map(([h, f]) => (
                    <div
                      key={h}
                      onClick={() => f && toggleSort(f)}
                      style={{
                        fontSize: 10, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase',
                        letterSpacing: '.04em', cursor: f ? 'pointer' : 'default',
                        userSelect: 'none',
                      }}
                    >
                      {h}{f && <SortIcon field={f} />}
                    </div>
                  ))}
                </div>

                {/* Rows */}
                {(data?.items || []).map((r, i) => (
                  <div key={r.id} style={{
                    display: 'grid',
                    gridTemplateColumns: '200px 1fr 90px 100px 90px 90px 90px 90px',
                    padding: '12px 16px',
                    borderBottom: i < (data.items.length - 1) ? '1px solid #F1F5F9' : 'none',
                    background: r.is_loss_making ? 'rgba(232,52,74,.03)' : '#fff',
                    alignItems: 'center',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: PALETTE.navy, fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.sku_code || '—'}
                    </div>
                    <div style={{ fontSize: 12, color: '#4B6080', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 12 }}>
                      {r.product_title || r.category || '—'}
                    </div>
                    <div style={{ fontSize: 12, color: PALETTE.navy }}>{num(r.total_orders)}</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: PALETTE.navy }}>{inr(r.gross_sales, true)}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: r.net_earnings < 0 ? PALETTE.red : PALETTE.green }}>
                      {inr(r.net_earnings, true)}
                    </div>
                    <div style={{ fontSize: 12, color: r.margin_pct < 0 ? PALETTE.red : r.margin_pct < 10 ? PALETTE.amber : PALETTE.green }}>
                      {pct(r.margin_pct)}
                    </div>
                    <div style={{ fontSize: 12, color: r.return_rate_pct > 20 ? PALETTE.red : r.return_rate_pct > 10 ? PALETTE.amber : '#4B6080' }}>
                      {pct(r.return_rate_pct)}
                    </div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {r.is_loss_making   && <span style={{ fontSize: 10, background: 'rgba(232,52,74,.12)', color: PALETTE.red,   borderRadius: 4, padding: '2px 5px', fontWeight: 700 }}>LOSS</span>}
                      {r.high_return_rate && <span style={{ fontSize: 10, background: 'rgba(233,147,13,.12)', color: PALETTE.amber, borderRadius: 4, padding: '2px 5px', fontWeight: 700 }}>HIGH RET</span>}
                    </div>
                  </div>
                ))}

                {data?.items?.length === 0 && (
                  <div style={{ padding: '40px 24px', textAlign: 'center', color: PALETTE.slate, fontSize: 13 }}>
                    No SKUs match current filters
                  </div>
                )}
              </div>

              {/* Pagination */}
              {data && data.pages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    style={{ padding: '7px 14px', borderRadius: 8, border: '1px solid #D1DDE8', background: '#fff', cursor: page === 1 ? 'not-allowed' : 'pointer', fontSize: 12, opacity: page === 1 ? 0.4 : 1 }}
                  >
                    ← Prev
                  </button>
                  <span style={{ padding: '7px 12px', fontSize: 12, color: PALETTE.slate }}>
                    Page {page} of {data.pages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(data.pages, p + 1))}
                    disabled={page >= data.pages}
                    style={{ padding: '7px 14px', borderRadius: 8, border: '1px solid #D1DDE8', background: '#fff', cursor: page >= data.pages ? 'not-allowed' : 'pointer', fontSize: 12, opacity: page >= data.pages ? 0.4 : 1 }}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}

// ── Tab: Orders ───────────────────────────────────────────────────────────────

function OrdersTab({ token, reportId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [settlStatus, setSettlStatus] = useState('')
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page, limit: 100 })
      if (status)      params.set('status', status)
      if (settlStatus) params.set('settlement_status', settlStatus)
      const d = await api(token, `/reports/${reportId}/orders?${params}`)
      setData(d)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [token, reportId, status, settlStatus, page])

  useEffect(() => { load() }, [load])

  const STATUS_COLORS = {
    delivered:  { bg: 'rgba(16,185,129,.1)', color: PALETTE.green },
    returned:   { bg: 'rgba(232,52,74,.1)',  color: PALETTE.red },
    cancelled:  { bg: 'rgba(139,92,246,.1)', color: PALETTE.purple },
  }
  const SETTL_COLORS = {
    settled:    { bg: 'rgba(16,185,129,.1)',  color: PALETTE.green },
    pending:    { bg: 'rgba(233,147,13,.1)',  color: PALETTE.amber },
    unsettled:  { bg: 'rgba(232,52,74,.1)',   color: PALETTE.red },
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 12, background: '#fff' }}>
          <option value="">All Statuses</option>
          <option value="delivered">Delivered</option>
          <option value="returned">Returned</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select value={settlStatus} onChange={e => { setSettlStatus(e.target.value); setPage(1) }}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 12, background: '#fff' }}>
          <option value="">All Settlement Statuses</option>
          <option value="settled">Settled</option>
          <option value="pending">Pending</option>
        </select>
        {data && <div style={{ fontSize: 12, color: PALETTE.slate, marginLeft: 'auto' }}>{data.total} orders</div>}
      </div>

      {loading && !data ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner /></div>
      ) : (
        <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #E8EFF6', overflow: 'hidden' }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '120px 90px 160px 80px 100px 90px 80px 90px 100px',
            background: '#F7FAFC', padding: '10px 16px', borderBottom: '1px solid #E8EFF6',
          }}>
            {['Order ID', 'Date', 'SKU / Product', 'Qty', 'Gross', 'Net Earn', 'Status', 'Settlement', 'Variance'].map(h => (
              <div key={h} style={{ fontSize: 10, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase', letterSpacing: '.04em' }}>{h}</div>
            ))}
          </div>

          {(data?.items || []).map((r, i) => {
            const sc = STATUS_COLORS[r.status] || { bg: '#F7FAFC', color: '#4B6080' }
            const ss = SETTL_COLORS[r.settlement_status] || { bg: '#F7FAFC', color: '#4B6080' }
            const hasVariance = r.settlement_variance != null && Math.abs(r.settlement_variance) > 1

            return (
              <div key={r.id} style={{
                display: 'grid',
                gridTemplateColumns: '120px 90px 160px 80px 100px 90px 80px 90px 100px',
                padding: '10px 16px', borderBottom: i < (data.items.length - 1) ? '1px solid #F1F5F9' : 'none',
                background: hasVariance ? 'rgba(232,52,74,.02)' : '#fff',
                alignItems: 'center',
              }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: PALETTE.navy, fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.order_id || '—'}
                </div>
                <div style={{ fontSize: 11, color: PALETTE.slate }}>{r.order_date || '—'}</div>
                <div style={{ fontSize: 11, color: '#4B6080', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.sku_code || r.product_title || '—'}
                </div>
                <div style={{ fontSize: 11, color: PALETTE.navy }}>{r.quantity || '—'}</div>
                <div style={{ fontSize: 11, fontWeight: 600, color: PALETTE.navy }}>{inr(r.gross_amount, true)}</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: r.net_earnings < 0 ? PALETTE.red : PALETTE.green }}>{inr(r.net_earnings, true)}</div>
                <div>
                  <span style={{ ...sc, borderRadius: 6, padding: '2px 6px', fontSize: 10, fontWeight: 700 }}>
                    {r.status || '—'}
                  </span>
                </div>
                <div>
                  <span style={{ ...ss, borderRadius: 6, padding: '2px 6px', fontSize: 10, fontWeight: 700 }}>
                    {r.settlement_status || '—'}
                  </span>
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: hasVariance ? (r.settlement_variance > 0 ? PALETTE.red : PALETTE.green) : PALETTE.slate }}>
                  {hasVariance ? inr(r.settlement_variance, true) : '—'}
                </div>
              </div>
            )
          })}

          {data?.items?.length === 0 && (
            <div style={{ padding: '40px 24px', textAlign: 'center', color: PALETTE.slate, fontSize: 13 }}>
              No orders match current filters
            </div>
          )}
        </div>
      )}

      {data && data.pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            style={{ padding: '7px 14px', borderRadius: 8, border: '1px solid #D1DDE8', background: '#fff', cursor: 'pointer', fontSize: 12 }}>
            ← Prev
          </button>
          <span style={{ padding: '7px 12px', fontSize: 12, color: PALETTE.slate }}>Page {page} of {data.pages}</span>
          <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page >= data.pages}
            style={{ padding: '7px 14px', borderRadius: 8, border: '1px solid #D1DDE8', background: '#fff', cursor: 'pointer', fontSize: 12 }}>
            Next →
          </button>
        </div>
      )}
    </div>
  )
}

// ── Tab: Reconciliation ───────────────────────────────────────────────────────

function ReconTab({ token, reportId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [filterSev, setFilterSev] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [patching, setPatching] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: 200 })
      if (filterType)   params.set('issue_type', filterType)
      if (filterSev)    params.set('severity', filterSev)
      if (filterStatus) params.set('status', filterStatus)
      const d = await api(token, `/reports/${reportId}/reconciliation?${params}`)
      setData(d)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [token, reportId, filterType, filterSev, filterStatus])

  useEffect(() => { load() }, [load])

  async function updateStatus(issueId, newStatus) {
    setPatching(issueId)
    try {
      await api(token, `/recon-issues/${issueId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      load()
    } finally {
      setPatching(null)
    }
  }

  const summary = data?.summary || {}
  const issues  = data?.items  || []

  return (
    <div>
      {/* Summary */}
      {summary.total_issues > 0 && (
        <div style={{
          background: 'linear-gradient(135deg,#0D1F35,#1A3355)',
          borderRadius: 16, padding: '20px 24px', marginBottom: 24, color: '#fff',
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: PALETTE.teal, marginBottom: 14, textTransform: 'uppercase', letterSpacing: '.06em' }}>
            Reconciliation Summary
          </div>
          <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
            {[
              ['Total Issues',    summary.total_issues,            '#fff'],
              ['Critical',        summary.critical_issues,         PALETTE.red],
              ['Warnings',        summary.warning_issues,          PALETTE.amber],
              ['Open',            summary.open_issues,             PALETTE.amber],
              ['At Risk',         inr(summary.total_variance_amount, true), PALETTE.red],
            ].map(([l, v, c]) => (
              <div key={l}>
                <div style={{ fontSize: 11, color: '#4B6080', marginBottom: 4 }}>{l}</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: c }}>{v}</div>
              </div>
            ))}
          </div>

          {/* Type breakdown */}
          {summary.issues_by_type?.length > 0 && (
            <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
              {summary.issues_by_type.map(({ type, count, amount }) => {
                const info = ISSUE_LABELS[type] || { label: type, icon: '⚠️', color: PALETTE.amber }
                return (
                  <div key={type} onClick={() => setFilterType(filterType === type ? '' : type)}
                    style={{
                      background: 'rgba(255,255,255,.06)', borderRadius: 10, padding: '8px 14px',
                      cursor: 'pointer', border: `2px solid ${filterType === type ? info.color : 'transparent'}`,
                    }}>
                    <div style={{ fontSize: 13 }}>{info.icon}</div>
                    <div style={{ fontSize: 11, color: '#8FA5BD' }}>{info.label}</div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: info.color }}>{inr(amount, true)}</div>
                    <div style={{ fontSize: 10, color: '#4B6080' }}>{count} issue{count !== 1 ? 's' : ''}</div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={filterType} onChange={e => setFilterType(e.target.value)}
          style={{ padding: '7px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 12, background: '#fff' }}>
          <option value="">All Types</option>
          {Object.entries(ISSUE_LABELS).map(([k, v]) => <option key={k} value={k}>{v.icon} {v.label}</option>)}
        </select>
        <select value={filterSev} onChange={e => setFilterSev(e.target.value)}
          style={{ padding: '7px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 12, background: '#fff' }}>
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          style={{ padding: '7px 12px', borderRadius: 8, border: '1px solid #D1DDE8', fontSize: 12, background: '#fff' }}>
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="disputed">Disputed</option>
          <option value="resolved">Resolved</option>
          <option value="waived">Waived</option>
        </select>
        <div style={{ fontSize: 12, color: PALETTE.slate, marginLeft: 'auto' }}>
          {issues.length} issue{issues.length !== 1 ? 's' : ''}
        </div>
      </div>

      {loading && !data ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner /></div>
      ) : issues.length === 0 ? (
        <EmptyState icon="✅" message="No reconciliation issues found" sub="Your Flipkart settlements appear to match expectations" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {issues.map(iss => {
            const info = ISSUE_LABELS[iss.issue_type] || { label: iss.issue_type, icon: '⚠️', color: PALETTE.amber }
            const ss   = SEVERITY_STYLE[iss.severity] || SEVERITY_STYLE.info
            const statusStyle = {
              open:     { bg: 'rgba(232,52,74,.1)', color: PALETTE.red },
              resolved: { bg: 'rgba(16,185,129,.1)', color: PALETTE.green },
              disputed: { bg: 'rgba(233,147,13,.1)', color: PALETTE.amber },
              waived:   { bg: 'rgba(139,92,246,.1)', color: PALETTE.purple },
            }[iss.status] || {}

            return (
              <div key={iss.id} style={{
                background: '#fff', borderRadius: 14, border: '1px solid #E8EFF6',
                padding: '14px 18px',
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{ fontSize: 24, flexShrink: 0 }}>{info.icon}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 6, alignItems: 'center' }}>
                      <span style={{ fontSize: 13, fontWeight: 700, color: info.color }}>{info.label}</span>
                      <span style={{ ...ss, borderRadius: 6, padding: '2px 8px', fontSize: 10, fontWeight: 700, border: `1px solid ${ss.border}` }}>
                        {iss.severity}
                      </span>
                      <span style={{ ...statusStyle, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700 }}>
                        {iss.status}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: '#4B6080', lineHeight: 1.5 }}>{iss.description}</div>
                    {(iss.order_id || iss.sku_code) && (
                      <div style={{ fontSize: 11, color: PALETTE.slate, marginTop: 4 }}>
                        {iss.order_id && `Order: ${iss.order_id}`}
                        {iss.sku_code && ` · SKU: ${iss.sku_code}`}
                      </div>
                    )}
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    {iss.expected_amount != null && (
                      <div style={{ marginBottom: 4 }}>
                        <div style={{ fontSize: 10, color: PALETTE.slate }}>Expected</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: PALETTE.navy }}>{inr(iss.expected_amount)}</div>
                      </div>
                    )}
                    {iss.variance != null && Math.abs(iss.variance) > 0.01 && (
                      <div>
                        <div style={{ fontSize: 10, color: PALETTE.slate }}>Variance</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: PALETTE.red }}>{inr(Math.abs(iss.variance))}</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
                  {['disputed', 'resolved', 'waived'].map(s => (
                    <button key={s} disabled={iss.status === s || patching === iss.id}
                      onClick={() => updateStatus(iss.id, s)}
                      style={{
                        padding: '5px 12px', borderRadius: 7, fontSize: 11, fontWeight: 700, cursor: 'pointer', border: 'none',
                        background: statusStyle.bg || 'rgba(16,185,129,.1)', color: statusStyle.color || PALETTE.green,
                        opacity: iss.status === s ? 0.5 : 1,
                        ...(s === 'disputed' ? { background: 'rgba(233,147,13,.1)', color: PALETTE.amber } : {}),
                        ...(s === 'resolved' ? { background: 'rgba(16,185,129,.1)', color: PALETTE.green } : {}),
                        ...(s === 'waived'   ? { background: 'rgba(139,92,246,.1)', color: PALETTE.purple } : {}),
                      }}
                    >
                      {patching === iss.id ? '…' : s.charAt(0).toUpperCase() + s.slice(1)}
                    </button>
                  ))}
                  {iss.status !== 'open' && (
                    <button onClick={() => updateStatus(iss.id, 'open')} disabled={patching === iss.id}
                      style={{ padding: '5px 12px', borderRadius: 7, fontSize: 11, fontWeight: 700, cursor: 'pointer', border: '1px solid #E8EFF6', background: '#F7FAFC', color: '#4B6080' }}>
                      Reopen
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Tab: Insights ─────────────────────────────────────────────────────────────

function InsightsTab({ token, reportId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api(token, `/reports/${reportId}/insights`)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [token, reportId])

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}><Spinner /></div>

  const insights = data?.insights || []
  if (insights.length === 0) {
    return <EmptyState icon="💡" message="No insights available yet" sub="Insights are generated after full report processing" />
  }

  const TypeIcon = { critical: '🚨', warning: '⚠️', info: 'ℹ️', positive: '✅' }

  return (
    <div>
      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ fontSize: 15, fontWeight: 800, color: PALETTE.navy }}>Automated Insights</div>
        <span style={{ background: 'rgba(10,191,202,.15)', color: PALETTE.teal, borderRadius: 20, padding: '3px 12px', fontSize: 11, fontWeight: 700 }}>
          {insights.length} detected
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {insights.map((ins, i) => {
          const ss = SEVERITY_STYLE[ins.type] || SEVERITY_STYLE.info
          return (
            <div key={i} style={{
              background: '#fff', borderRadius: 14,
              border: `1px solid ${ss.border || '#E8EFF6'}`,
              padding: '16px 20px',
              display: 'flex', gap: 16, alignItems: 'flex-start',
            }}>
              <div style={{
                width: 40, height: 40, borderRadius: 12,
                background: ss.bg, display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: 20, flexShrink: 0,
              }}>
                {ins.icon || TypeIcon[ins.type] || '💡'}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ ...ss, borderRadius: 6, padding: '2px 8px', fontSize: 10, fontWeight: 700, border: `1px solid ${ss.border || 'transparent'}` }}>
                    {ins.type.toUpperCase()}
                  </span>
                  <span style={{ fontSize: 11, color: PALETTE.slate, textTransform: 'uppercase', letterSpacing: '.04em' }}>
                    {ins.category?.replace(/_/g, ' ')}
                  </span>
                </div>
                <div style={{ fontSize: 14, color: '#0D1F35', lineHeight: 1.6, fontWeight: 500 }}>
                  {ins.message}
                </div>
                {ins.data?.length > 0 && (
                  <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                    {ins.data.map((d, j) => (
                      <span key={j} style={{ background: '#F1F5F9', color: '#4B6080', borderRadius: 6, padding: '3px 8px', fontSize: 11, fontFamily: 'monospace' }}>
                        {d}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function FlipkartReports() {
  const token = useAuthStore(s => s.token)
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('upload')
  const [selectedReportId, setSelectedReportId] = useState(null)
  const [companySummary, setCompanySummary] = useState(null)

  const loadReports = useCallback(async () => {
    try {
      const [r, cs] = await Promise.all([
        api(token, '/reports'),
        api(token, '/summary').catch(() => null),
      ])
      setReports(r.items || [])
      setCompanySummary(cs)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { loadReports() }, [loadReports])

  function handleSelectReport(id) {
    setSelectedReportId(id)
    setTab('dashboard')
  }

  const TABS = [
    { id: 'upload',       label: 'Reports',        icon: '📋' },
    { id: 'dashboard',    label: 'Dashboard',      icon: '⚡', requiresReport: true },
    { id: 'skus',         label: 'SKU Analytics',  icon: '🏷️', requiresReport: true },
    { id: 'orders',       label: 'Orders',         icon: '📦', requiresReport: true },
    { id: 'reconciliation', label: 'Reconciliation', icon: '🔍', requiresReport: true },
    { id: 'insights',     label: 'Insights',       icon: '💡', requiresReport: true },
  ]

  return (
    <div style={{ padding: '24px 28px', minHeight: '100vh', background: '#F1F5F9' }}>
      <style>{`
        @keyframes fk-spin     { to { transform: rotate(360deg) } }
        @keyframes fk-progress { 0%,100% { transform: translateX(-100%) } 50% { transform: translateX(100%) } }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: 'linear-gradient(135deg,#FF6B35,#F7931E)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>
            🛒
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: PALETTE.navy }}>
              Flipkart Intelligence
            </h1>
            <div style={{ fontSize: 12, color: PALETTE.slate, marginTop: 1 }}>
              P&L report ingestion · SKU analytics · Settlement reconciliation · Automated insights
            </div>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <span style={{ background: 'rgba(255,107,53,.12)', color: '#FF6B35', borderRadius: 20, padding: '4px 12px', fontSize: 11, fontWeight: 700 }}>
              FLIPKART
            </span>
            <span style={{ background: 'rgba(10,191,202,.12)', color: PALETTE.teal, borderRadius: 20, padding: '4px 12px', fontSize: 11, fontWeight: 700 }}>
              LIVE ANALYTICS
            </span>
          </div>
        </div>
      </div>

      {/* Company-level stats */}
      {companySummary && companySummary.total_reports > 0 && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          <KpiCard label="Total Reports"    value={companySummary.total_reports}                       color={PALETTE.teal}  icon="📊" />
          <KpiCard label="Total Gross Sales" value={inr(companySummary.total_gross_sales, true)}       color={PALETTE.blue}  icon="💰" />
          <KpiCard label="Total Earnings"   value={inr(companySummary.total_earnings, true)}          color={PALETTE.green} icon="🏆" />
          <KpiCard label="Total Orders"     value={num(companySummary.total_orders)}                   color={PALETTE.teal}  icon="📦" />
          {companySummary.open_recon_issues > 0 && (
            <KpiCard label="Open Recon Issues" value={companySummary.open_recon_issues} color={PALETTE.red} icon="⚠️"
              onClick={() => { if (selectedReportId) { setTab('reconciliation') } }} />
          )}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 2, marginBottom: 24, background: '#fff', borderRadius: 12, padding: 4, width: 'fit-content', border: '1px solid #E8EFF6', flexWrap: 'wrap' }}>
        {TABS.map(t => {
          const disabled = t.requiresReport && !selectedReportId
          return (
            <button
              key={t.id}
              onClick={() => !disabled && setTab(t.id)}
              title={disabled ? 'Select a processed report first' : ''}
              style={{
                padding: '8px 18px', borderRadius: 9, border: 'none',
                cursor: disabled ? 'not-allowed' : 'pointer',
                fontSize: 13, fontWeight: 600,
                background: tab === t.id ? 'linear-gradient(135deg,#FF6B35,#F7931E)' : 'transparent',
                color: tab === t.id ? '#fff' : disabled ? '#C5D2DF' : '#4B6080',
                display: 'flex', alignItems: 'center', gap: 6,
                transition: 'all .15s',
                opacity: disabled ? 0.5 : 1,
              }}
            >
              <span>{t.icon}</span> {t.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}><Spinner size={40} /></div>
      ) : (
        <>
          {tab === 'upload' && (
            <UploadTab
              token={token}
              reports={reports}
              onRefresh={loadReports}
              onSelectReport={handleSelectReport}
            />
          )}
          {tab === 'dashboard' && selectedReportId && (
            <DashboardTab token={token} reportId={selectedReportId} />
          )}
          {tab === 'skus' && selectedReportId && (
            <SKUTab token={token} reportId={selectedReportId} />
          )}
          {tab === 'orders' && selectedReportId && (
            <OrdersTab token={token} reportId={selectedReportId} />
          )}
          {tab === 'reconciliation' && selectedReportId && (
            <ReconTab token={token} reportId={selectedReportId} />
          )}
          {tab === 'insights' && selectedReportId && (
            <InsightsTab token={token} reportId={selectedReportId} />
          )}
        </>
      )}
    </div>
  )
}
