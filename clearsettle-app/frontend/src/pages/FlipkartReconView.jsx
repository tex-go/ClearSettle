import React, { useState, useRef } from 'react'
import axios from 'axios'

// Calls the Flipkart reconciliation microservice directly (CORS is open)
const MICRO = 'http://127.0.0.1:8003'

// ── Status colour map ──────────────────────────────────────────────────────────
const SC = {
  MATCHED:            { rowBg: '#F0FDF4', border: '#BBF7D0', badge: '#10B981', badgeBg: 'rgba(16,185,129,.15)', text: 'Matched' },
  SHORT_PAID:         { rowBg: '#FFF1F2', border: '#FECDD3', badge: '#E8344A', badgeBg: 'rgba(232,52,74,.12)',  text: 'Short Paid' },
  OVER_PAID:          { rowBg: '#FFFBEB', border: '#FDE68A', badge: '#D97706', badgeBg: 'rgba(217,119,6,.12)',  text: 'Over Paid' },
  RETURN_RECOVERY:    { rowBg: '#EFF6FF', border: '#BFDBFE', badge: '#2563EB', badgeBg: 'rgba(37,99,235,.12)', text: 'Return' },
  MISSING_SETTLEMENT: { rowBg: '#FFF7ED', border: '#FED7AA', badge: '#F97316', badgeBg: 'rgba(249,115,22,.12)', text: 'No Settlement' },
  MISSING_ORDER:      { rowBg: '#F8FAFC', border: '#E2E8F0', badge: '#6B7280', badgeBg: 'rgba(107,114,128,.1)', text: 'No Order' },
  MISSING_FEE_RECORD: { rowBg: '#FEFCE8', border: '#FEF08A', badge: '#CA8A04', badgeBg: 'rgba(202,138,4,.12)',  text: 'No Fee Record' },
}

const RECON_DOCS = [
  {
    key: 'orders',
    label: 'Fulfilment Orders Report',
    icon: '📦',
    accent: '#0ABFCA',
    filename: 'FulfilmentReports_Orders.xlsx',
    description: 'Order-level details including status, dispatch and delivery dates.',
    steps: [
      'Log in to Flipkart Seller Hub',
      'Go to Reports → Fulfilment Reports → Orders',
      'Select your month date range (e.g. April 1–30)',
      'Click Download → Excel format',
      'Upload the downloaded .xlsx file here',
    ],
  },
  {
    key: 'fees',
    label: 'Commission Invoice',
    icon: '🧾',
    accent: '#8B5CF6',
    filename: 'Invoices_CommissionInvoiceTransactionDetails.xlsx',
    description: 'All fee deductions per order — commission, fixed fee, tax amounts.',
    steps: [
      'Log in to Flipkart Seller Hub',
      'Go to Payments → Invoices → Commission Invoice Transaction Details',
      'Select the same date range as the orders report',
      'Click Download → Excel format',
      'Upload the downloaded .xlsx file here',
    ],
  },
  {
    key: 'settlements',
    label: 'Settlement Report',
    icon: '🏦',
    accent: '#3B82F6',
    filename: 'PaymentReports_SettledTransactions.xlsx',
    description: 'Actual bank credits from Flipkart. Use current + next month for full coverage.',
    steps: [
      'Log in to Flipkart Seller Hub',
      'Go to Payments → Payment Reports → Settled Transactions',
      'Download both the target month AND the following month (orders settle with a delay)',
      'Upload both files one after the other here',
    ],
  },
]

function inr(n) {
  const num = Number(n) || 0
  return '₹' + Math.abs(num).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

// ── Spinner ────────────────────────────────────────────────────────────────────
function Spin({ size = 16 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      border: '2.5px solid rgba(10,191,202,.2)', borderTopColor: '#0ABFCA',
      animation: 'spin 0.8s linear infinite', flexShrink: 0,
    }} />
  )
}

// ── FlipkartReconGate ─────────────────────────────────────────────────────────
export function FlipkartReconGate({ onBack, onResults }) {
  const INIT = { status: 'idle', filename: null, error: null }
  const [uploads, setUploads] = useState({ orders: INIT, fees: INIT, settlements: INIT })
  const [running, setRunning]   = useState(false)
  const [runError, setRunError] = useState('')
  const [expanded, setExpanded] = useState({})
  const fileRefs = useRef({})

  const doneCount = RECON_DOCS.filter(d => uploads[d.key].status === 'done').length
  const allDone   = doneCount === 3

  async function handleFile(key, file) {
    if (!file) return
    setUploads(p => ({ ...p, [key]: { status: 'uploading', filename: null, error: null } }))
    const form = new FormData()
    form.append('file', file)
    try {
      await axios.post(`${MICRO}/ingest/${key}`, form)
      setUploads(p => ({ ...p, [key]: { status: 'done', filename: file.name, error: null } }))
    } catch (err) {
      setUploads(p => ({
        ...p,
        [key]: { status: 'error', filename: null, error: err.response?.data?.detail || 'Upload failed' },
      }))
    }
  }

  async function runReconciliation() {
    setRunning(true)
    setRunError('')
    try {
      const [runRes, itemsRes] = await Promise.all([
        axios.post(`${MICRO}/reconciliation/run-all`),
        axios.get(`${MICRO}/reconciliation/results`),
      ])
      onResults(runRes.data, itemsRes.data)
    } catch (err) {
      setRunError(err.response?.data?.detail || 'Reconciliation failed — is the server running?')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ padding: '8px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <button onClick={onBack} style={{ background: '#F3F4F6', border: 'none', borderRadius: 8, padding: '6px 12px', fontSize: 13, color: '#6B7280', cursor: 'pointer' }}>← Back</button>
        <span style={{ fontSize: 20 }}>🛒</span>
        <div>
          <div style={{ fontSize: 17, fontWeight: 800, color: '#0D1F35' }}>Flipkart — Upload Reports</div>
          <div style={{ fontSize: 12, color: '#6B7280' }}>Upload all 3 report files to run the reconciliation engine</div>
        </div>
        <div style={{ marginLeft: 'auto', background: allDone ? 'rgba(16,185,129,.12)' : 'rgba(233,147,13,.1)', color: allDone ? '#10B981' : '#E9930D', borderRadius: 20, padding: '4px 14px', fontSize: 12, fontWeight: 700 }}>
          {doneCount} / 3 uploaded
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 4, background: '#E5E7EB', borderRadius: 99, marginBottom: 28, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${(doneCount / 3) * 100}%`, background: 'linear-gradient(90deg,#0ABFCA,#10B981)', borderRadius: 99, transition: 'width .5s ease' }} />
      </div>

      {/* Doc cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {RECON_DOCS.map(doc => {
          const up       = uploads[doc.key]
          const isDone   = up.status === 'done'
          const isLoading = up.status === 'uploading'
          const isErr    = up.status === 'error'

          return (
            <div key={doc.key} style={{ background: '#fff', border: `1.5px solid ${isDone ? doc.accent + '50' : '#E8EFF6'}`, borderRadius: 14, overflow: 'hidden', transition: 'border-color .2s' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 20px' }}>
                <div style={{ width: 44, height: 44, borderRadius: 12, flexShrink: 0, background: isDone ? doc.accent + '18' : '#F3F4F6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>
                  {isDone ? '✅' : doc.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#0D1F35' }}>{doc.label}</div>
                  <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{doc.description}</div>
                  <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 3, fontFamily: 'monospace' }}>{doc.filename}</div>
                  {isDone   && <div style={{ fontSize: 11, color: '#10B981', marginTop: 4, fontWeight: 600 }}>✓ {up.filename}</div>}
                  {isErr    && <div style={{ fontSize: 11, color: '#E8344A', marginTop: 4 }}>{up.error}</div>}
                </div>
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <button onClick={() => setExpanded(p => ({ ...p, [doc.key]: !p[doc.key] }))} style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #E5E7EB', background: '#fff', color: '#6B7280', fontSize: 12, cursor: 'pointer' }}>
                    {expanded[doc.key] ? 'Hide' : 'How to get it?'}
                  </button>
                  <input ref={el => (fileRefs.current[doc.key] = el)} type="file" accept=".xlsx,.xls" style={{ display: 'none' }} onChange={e => { handleFile(doc.key, e.target.files[0]); e.target.value = '' }} />
                  <button onClick={() => fileRefs.current[doc.key]?.click()} disabled={isLoading} style={{ padding: '7px 18px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 700, cursor: isLoading ? 'not-allowed' : 'pointer', opacity: isLoading ? 0.65 : 1, background: isDone ? '#F3F4F6' : `linear-gradient(135deg,${doc.accent},${doc.accent}cc)`, color: isDone ? '#6B7280' : '#fff', display: 'flex', alignItems: 'center', gap: 6 }}>
                    {isLoading ? <><Spin /> Uploading…</> : isDone ? '↺ Replace' : '↑ Upload'}
                  </button>
                </div>
              </div>

              {expanded[doc.key] && (
                <div style={{ borderTop: '1px solid #F3F4F6', padding: '16px 20px', background: '#F9FBFC' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 12 }}>Step-by-step</div>
                  {doc.steps.map((step, i) => (
                    <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 10 }}>
                      <div style={{ width: 24, height: 24, borderRadius: '50%', flexShrink: 0, background: doc.accent + '18', color: doc.accent, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 800 }}>{i + 1}</div>
                      <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.5, paddingTop: 3 }}>{step}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Run button */}
      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end', gap: 12, alignItems: 'center' }}>
        {runError && <span style={{ fontSize: 12, color: '#E8344A' }}>{runError}</span>}
        {doneCount > 0 && !allDone && <span style={{ fontSize: 12, color: '#9CA3AF' }}>{3 - doneCount} file{3 - doneCount > 1 ? 's' : ''} still pending</span>}
        <button
          onClick={runReconciliation}
          disabled={!allDone || running}
          style={{ padding: '12px 32px', borderRadius: 10, border: 'none', fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, background: allDone && !running ? 'linear-gradient(135deg,#0ABFCA,#088F99)' : '#E5E7EB', color: allDone && !running ? '#fff' : '#9CA3AF', cursor: allDone && !running ? 'pointer' : 'not-allowed', transition: 'all .2s' }}
        >
          {running ? <><Spin /> Running reconciliation…</> : allDone ? '🔬 Run Reconciliation →' : 'Upload all 3 files to continue'}
        </button>
      </div>
    </div>
  )
}

// ── FlipkartReconTable ────────────────────────────────────────────────────────
const COLS = [
  { key: 'order_item_id',      label: 'Order Item ID',  w: 185, mono: true },
  { key: 'order_id',           label: 'Order ID',       w: 185, mono: true },
  { key: 'sku',                label: 'SKU',            w: 150 },
  { key: 'sale_amount',        label: 'Sale (₹)',       w: 95,  num: true },
  { key: 'invoice_fee_total',  label: 'Inv Fee (₹)',    w: 95,  num: true },
  { key: 'invoice_gst_total',  label: 'Inv GST (₹)',    w: 85,  num: true },
  { key: 'tcs',                label: 'TCS (₹)',        w: 75,  num: true },
  { key: 'tds',                label: 'TDS (₹)',        w: 75,  num: true },
  { key: 'expected_settlement',label: 'Expected (₹)',   w: 115, num: true },
  { key: 'settlement_amount',  label: 'Actual (₹)',     w: 105, num: true },
  { key: 'difference',         label: 'Diff (₹)',       w: 90,  num: true },
  { key: 'reconciliation_status', label: 'Status',      w: 140 },
]

export function FlipkartReconTable({ summary, items, onBack, onNewUpload }) {
  const [filterStatus, setFilterStatus] = useState('ALL')
  const [search,       setSearch]       = useState('')
  const [sort,         setSort]         = useState({ col: 'reconciliation_status', dir: 'asc' })
  const [page,         setPage]         = useState(1)
  const PAGE_SIZE = 100

  const filtered = items
    .filter(r => filterStatus === 'ALL' || r.reconciliation_status === filterStatus)
    .filter(r => {
      if (!search) return true
      const q = search.toLowerCase()
      return (r.order_item_id || '').toLowerCase().includes(q)
          || (r.order_id      || '').toLowerCase().includes(q)
          || (r.sku           || '').toLowerCase().includes(q)
    })
    .sort((a, b) => {
      const va = a[sort.col] ?? '', vb = b[sort.col] ?? ''
      const c  = String(va).localeCompare(String(vb), undefined, { numeric: true })
      return sort.dir === 'asc' ? c : -c
    })

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const visible    = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  function toggleSort(col) {
    setSort(p => ({ col, dir: p.col === col && p.dir === 'asc' ? 'desc' : 'asc' }))
    setPage(1)
  }

  // Summary KPIs
  const shortTotal = items.filter(r => r.reconciliation_status === 'SHORT_PAID').reduce((s, r) => s + Math.abs(Number(r.difference) || 0), 0)
  const overTotal  = items.filter(r => r.reconciliation_status === 'OVER_PAID').reduce((s,  r) => s + Math.abs(Number(r.difference) || 0), 0)
  const netLeak    = shortTotal - overTotal

  const TABS = [
    { key: 'ALL',               label: 'All',          count: items.length,                    color: '#0D1F35' },
    { key: 'SHORT_PAID',        label: 'Short Paid',   count: summary?.short_paid        ?? 0, color: '#E8344A' },
    { key: 'OVER_PAID',         label: 'Over Paid',    count: summary?.over_paid         ?? 0, color: '#D97706' },
    { key: 'MATCHED',           label: 'Matched',      count: summary?.matched           ?? 0, color: '#10B981' },
    { key: 'RETURN_RECOVERY',   label: 'Returns',      count: summary?.return_recovery   ?? 0, color: '#2563EB' },
    { key: 'MISSING_SETTLEMENT',label: 'No Settlement',count: summary?.missing_settlement ?? 0, color: '#F97316' },
    { key: 'MISSING_FEE_RECORD',label: 'No Fee Record',count: summary?.missing_fee_record ?? 0, color: '#CA8A04' },
  ]

  const KPI_CARDS = [
    { label: 'Short Paid',       value: inr(shortTotal), sub: `${summary?.short_paid ?? 0} orders`,         color: '#E8344A', bg: '#FFF1F2' },
    { label: 'Over Paid',        value: inr(overTotal),  sub: `${summary?.over_paid ?? 0} orders`,          color: '#D97706', bg: '#FFFBEB' },
    { label: 'Net Underpayment', value: inr(netLeak),    sub: netLeak > 0 ? 'Flipkart owes you'  : 'You owe Flipkart', color: netLeak > 0 ? '#E8344A' : '#10B981', bg: netLeak > 0 ? '#FFF1F2' : '#F0FDF4' },
    { label: 'Returns',           value: String(summary?.return_recovery ?? 0), sub: 'return/refund orders', color: '#2563EB', bg: '#EFF6FF' },
  ]

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button onClick={onBack} style={{ background: '#F3F4F6', border: 'none', borderRadius: 8, padding: '6px 12px', fontSize: 13, color: '#6B7280', cursor: 'pointer' }}>← Back</button>
        <div>
          <div style={{ fontSize: 17, fontWeight: 800, color: '#0D1F35' }}>Flipkart Reconciliation Results</div>
          <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{items.length} order items analysed</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button
            onClick={onNewUpload}
            style={{ padding: '7px 16px', borderRadius: 8, border: '1.5px solid #E5E7EB', background: '#fff', color: '#6B7280', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          >
            ↑ Upload New Files
          </button>
          <button
            onClick={() => window.open(`${MICRO}/reconciliation/export?period=April+2026`, '_blank')}
            style={{ padding: '7px 16px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
          >
            ↓ Export Excel
          </button>
        </div>
      </div>

      {/* KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 }}>
        {KPI_CARDS.map(c => (
          <div key={c.label} style={{ background: c.bg, borderRadius: 12, padding: '14px 18px', border: `1px solid ${c.color}25` }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: c.color, textTransform: 'uppercase', letterSpacing: '.07em' }}>{c.label}</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: c.color, marginTop: 4 }}>{c.value}</div>
            <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{c.sub}</div>
          </div>
        ))}
      </div>

      {/* Filter tabs + search */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        {TABS.map(t => {
          const active = filterStatus === t.key
          return (
            <button key={t.key} onClick={() => { setFilterStatus(t.key); setPage(1) }} style={{ padding: '5px 13px', borderRadius: 20, border: `1.5px solid ${active ? t.color : '#E5E7EB'}`, background: active ? t.color + '18' : '#fff', color: active ? t.color : '#6B7280', fontSize: 12, fontWeight: active ? 700 : 500, cursor: 'pointer', transition: 'all .15s', whiteSpace: 'nowrap' }}>
              {t.label} <span style={{ opacity: .7 }}>({t.count})</span>
            </button>
          )
        })}
        <input
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          placeholder="Search Order ID or SKU…"
          style={{ marginLeft: 'auto', padding: '7px 14px', borderRadius: 8, border: '1.5px solid #E5E7EB', fontSize: 13, outline: 'none', width: 230 }}
        />
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto', borderRadius: 12, border: '1.5px solid #E8EFF6', boxShadow: '0 2px 12px rgba(0,0,0,.05)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {COLS.map(c => (
                <th
                  key={c.key}
                  onClick={() => toggleSort(c.key)}
                  style={{ padding: '11px 12px', textAlign: c.num ? 'right' : 'left', background: '#0D1F35', color: '#CBD5E1', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap', minWidth: c.w, borderRight: '1px solid rgba(255,255,255,.07)' }}
                >
                  {c.label}{sort.col === c.key ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr><td colSpan={COLS.length} style={{ textAlign: 'center', padding: '48px', color: '#9CA3AF', fontSize: 14 }}>No records match your filter</td></tr>
            ) : visible.map((r, i) => {
              const s    = SC[r.reconciliation_status] || SC.MISSING_ORDER
              const diff = Number(r.difference) || 0
              const rowBg = i % 2 === 0 ? s.rowBg : s.rowBg + 'bb'

              return (
                <tr key={r.order_item_id + i} style={{ background: rowBg, borderBottom: `1px solid ${s.border}` }}>
                  {COLS.map(c => {
                    const val = r[c.key]
                    const base = { padding: '8px 12px', textAlign: c.num ? 'right' : 'left', whiteSpace: 'nowrap', color: '#1E293B' }

                    if (c.key === 'reconciliation_status') {
                      return (
                        <td key={c.key} style={base}>
                          <span style={{ background: s.badgeBg, color: s.badge, borderRadius: 6, padding: '3px 9px', fontSize: 11, fontWeight: 700 }}>{s.text}</span>
                        </td>
                      )
                    }

                    if (c.key === 'difference') {
                      const color = diff < -0.5 ? '#E8344A' : diff > 0.5 ? '#10B981' : '#6B7280'
                      const sign  = diff > 0.5 ? '+' : ''
                      return (
                        <td key={c.key} style={{ ...base, color, fontWeight: 700, background: diff < -0.5 ? 'rgba(232,52,74,.08)' : diff > 0.5 ? 'rgba(16,185,129,.08)' : 'transparent' }}>
                          {val != null ? sign + Number(val).toFixed(2) : '—'}
                        </td>
                      )
                    }

                    if (c.num && val != null && val !== '') {
                      return <td key={c.key} style={base}>₹{Number(val).toFixed(2)}</td>
                    }

                    if (c.mono) {
                      return <td key={c.key} style={{ ...base, fontFamily: 'monospace', fontSize: 11, fontWeight: 600, color: '#0D1F35' }}>{val || '—'}</td>
                    }

                    return <td key={c.key} style={{ ...base, maxWidth: c.w, overflow: 'hidden', textOverflow: 'ellipsis' }}>{val || '—'}</td>
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination + count */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
        <div style={{ fontSize: 12, color: '#9CA3AF' }}>
          Showing {Math.min((page - 1) * PAGE_SIZE + 1, filtered.length)}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} records
        </div>
        {totalPages > 1 && (
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ padding: '5px 12px', borderRadius: 7, border: '1px solid #E5E7EB', background: '#fff', cursor: page === 1 ? 'not-allowed' : 'pointer', color: page === 1 ? '#CBD5E1' : '#374151', fontSize: 12 }}>‹ Prev</button>
            <span style={{ padding: '5px 12px', fontSize: 12, color: '#6B7280' }}>Page {page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} style={{ padding: '5px 12px', borderRadius: 7, border: '1px solid #E5E7EB', background: '#fff', cursor: page === totalPages ? 'not-allowed' : 'pointer', color: page === totalPages ? '#CBD5E1' : '#374151', fontSize: 12 }}>Next ›</button>
          </div>
        )}
      </div>

      <div style={{ marginTop: 16, fontSize: 11, color: '#9CA3AF', lineHeight: 1.6 }}>
        All figures represent <em>estimated potential discrepancies</em> based on uploaded data. Verify independently before raising disputes with Flipkart.
      </div>
    </div>
  )
}
