import React, { useState, useRef, useCallback, useEffect } from 'react'
import axios from 'axios'

const MICRO = 'http://127.0.0.1:8003'

// ── Status config ──────────────────────────────────────────────────────────────
const SC = {
  MATCHED:            { rowBg: '#F0FDF4', border: '#BBF7D0', badge: '#10B981', badgeBg: 'rgba(16,185,129,.15)',  text: 'Matched' },
  SHORT_PAID:         { rowBg: '#FFF1F2', border: '#FECDD3', badge: '#E8344A', badgeBg: 'rgba(232,52,74,.12)',   text: 'Short Paid' },
  OVER_PAID:          { rowBg: '#FFFBEB', border: '#FDE68A', badge: '#D97706', badgeBg: 'rgba(217,119,6,.12)',   text: 'Over Paid' },
  RETURN_RECOVERY:    { rowBg: '#EFF6FF', border: '#BFDBFE', badge: '#2563EB', badgeBg: 'rgba(37,99,235,.12)',   text: 'Return' },
  MISSING_SETTLEMENT: { rowBg: '#FFF7ED', border: '#FED7AA', badge: '#F97316', badgeBg: 'rgba(249,115,22,.12)',  text: 'No Settlement' },
  MISSING_ORDER:      { rowBg: '#F8FAFC', border: '#E2E8F0', badge: '#6B7280', badgeBg: 'rgba(107,114,128,.1)', text: 'No Order' },
  MISSING_FEE_RECORD: { rowBg: '#FEFCE8', border: '#FEF08A', badge: '#CA8A04', badgeBg: 'rgba(202,138,4,.12)',  text: 'No Fee Record' },
}

const RECON_DOCS = [
  {
    key: 'orders', label: 'Fulfilment Orders Report', icon: '📦', accent: '#0ABFCA',
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
    key: 'fees', label: 'Commission Invoice', icon: '🧾', accent: '#8B5CF6',
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
    key: 'settlements', label: 'Settlement Report', icon: '🏦', accent: '#3B82F6',
    filename: 'PaymentReports_SettledTransactions.xlsx',
    description: 'Actual bank credits from Flipkart. Use current + next month for full coverage.',
    steps: [
      'Log in to Flipkart Seller Hub',
      'Go to Payments → Payment Reports → Settled Transactions',
      'Download both the target month AND the following month',
      'Upload both files one after the other here',
    ],
  },
]

function inr(n) {
  const num = Number(n) || 0
  return '₹' + Math.abs(num).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}
function inr2(n) {
  const num = Number(n) || 0
  return (num < 0 ? '-₹' : '₹') + Math.abs(num).toFixed(2)
}
function fmtDate(s) {
  if (!s) return '—'
  const d = new Date(s)
  return isNaN(d) ? s : d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

function Spin({ size = 16 }) {
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', border: '2.5px solid rgba(10,191,202,.2)', borderTopColor: '#0ABFCA', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
  )
}

// ── FlipkartReconGate ─────────────────────────────────────────────────────────
export function FlipkartReconGate({ onBack, onResults }) {
  const INIT = { status: 'idle', filename: null, error: null }
  const [uploads, setUploads] = useState({ orders: INIT, fees: INIT, settlements: INIT })
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState('')
  const [expanded, setExpanded] = useState({})
  const fileRefs = useRef({})

  const doneCount = RECON_DOCS.filter(d => uploads[d.key].status === 'done').length
  const allDone = doneCount === 3

  async function handleFile(key, file) {
    if (!file) return
    setUploads(p => ({ ...p, [key]: { status: 'uploading', filename: null, error: null } }))
    const form = new FormData()
    form.append('file', file)
    try {
      await axios.post(`${MICRO}/ingest/${key}`, form)
      setUploads(p => ({ ...p, [key]: { status: 'done', filename: file.name, error: null } }))
    } catch (err) {
      setUploads(p => ({ ...p, [key]: { status: 'error', filename: null, error: err.response?.data?.detail || 'Upload failed' } }))
    }
  }

  async function runReconciliation() {
    setRunning(true); setRunError('')
    try {
      const [runRes, itemsRes] = await Promise.all([
        axios.post(`${MICRO}/reconciliation/run-all`),
        axios.get(`${MICRO}/reconciliation/results`),
      ])
      onResults(runRes.data, itemsRes.data)
    } catch (err) {
      setRunError(err.response?.data?.detail || 'Reconciliation failed — is the server running?')
    } finally { setRunning(false) }
  }

  return (
    <div style={{ padding: '8px 0' }}>
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

      <div style={{ height: 4, background: '#E5E7EB', borderRadius: 99, marginBottom: 28, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${(doneCount / 3) * 100}%`, background: 'linear-gradient(90deg,#0ABFCA,#10B981)', borderRadius: 99, transition: 'width .5s ease' }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {RECON_DOCS.map(doc => {
          const up = uploads[doc.key]
          const isDone = up.status === 'done'; const isLoading = up.status === 'uploading'; const isErr = up.status === 'error'
          return (
            <div key={doc.key} style={{ background: '#fff', border: `1.5px solid ${isDone ? doc.accent + '50' : '#E8EFF6'}`, borderRadius: 14, overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 20px' }}>
                <div style={{ width: 44, height: 44, borderRadius: 12, flexShrink: 0, background: isDone ? doc.accent + '18' : '#F3F4F6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>
                  {isDone ? '✅' : doc.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#0D1F35' }}>{doc.label}</div>
                  <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{doc.description}</div>
                  <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 3, fontFamily: 'monospace' }}>{doc.filename}</div>
                  {isDone && <div style={{ fontSize: 11, color: '#10B981', marginTop: 4, fontWeight: 600 }}>✓ {up.filename}</div>}
                  {isErr && <div style={{ fontSize: 11, color: '#E8344A', marginTop: 4 }}>{up.error}</div>}
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

      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end', gap: 12, alignItems: 'center' }}>
        {runError && <span style={{ fontSize: 12, color: '#E8344A' }}>{runError}</span>}
        {doneCount > 0 && !allDone && <span style={{ fontSize: 12, color: '#9CA3AF' }}>{3 - doneCount} file{3 - doneCount > 1 ? 's' : ''} still pending</span>}
        <button onClick={runReconciliation} disabled={!allDone || running} style={{ padding: '12px 32px', borderRadius: 10, border: 'none', fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, background: allDone && !running ? 'linear-gradient(135deg,#0ABFCA,#088F99)' : '#E5E7EB', color: allDone && !running ? '#fff' : '#9CA3AF', cursor: allDone && !running ? 'pointer' : 'not-allowed' }}>
          {running ? <><Spin /> Running reconciliation…</> : allDone ? '🔬 Run Reconciliation →' : 'Upload all 3 files to continue'}
        </button>
      </div>
    </div>
  )
}

// ── LifecyclePanel ────────────────────────────────────────────────────────────
function LifecyclePanel({ orderItemId, items, onClose, width, onWidthChange }) {
  const [minimized, setMinimized] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startW = useRef(0)

  useEffect(() => {
    setLoading(true); setError(null); setData(null)
    axios.get(`${MICRO}/order-item/${orderItemId}/lifecycle`)
      .then(r => { setData(r.data); setLoading(false) })
      .catch(() => { setError('Failed to load lifecycle data'); setLoading(false) })
  }, [orderItemId])

  const onDragStart = useCallback((e) => {
    dragging.current = true
    startX.current = e.clientX
    startW.current = width
    e.preventDefault()

    function onMove(ev) {
      if (!dragging.current) return
      const delta = startX.current - ev.clientX
      onWidthChange(Math.max(300, Math.min(780, startW.current + delta)))
    }
    function onUp() {
      dragging.current = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [width, onWidthChange])

  const summary = items?.find(r => r.order_item_id === orderItemId)
  const order = data?.order
  const fees = data?.fees || []
  const settlement = data?.settlement

  // Build timeline steps
  const steps = [
    {
      key: 'placed',
      label: 'Order Placed',
      date: order?.order_date || summary?.order_date,
      detail: order ? `Qty: ${order.quantity || 1}` : null,
      done: !!(order?.order_date || summary?.order_date),
      color: '#0ABFCA',
    },
    {
      key: 'processing',
      label: 'Processing',
      date: null,
      detail: order?.order_item_status ? `Status: ${order.order_item_status}` : 'Awaiting dispatch',
      done: !!(order?.dispatch_date),
      color: '#8B5CF6',
    },
    {
      key: 'dispatched',
      label: 'Dispatched',
      date: order?.dispatch_date,
      detail: null,
      done: !!(order?.dispatch_date),
      color: '#F97316',
    },
    {
      key: 'delivered',
      label: order?.order_item_status === 'Cancelled' ? 'Cancelled' : 'Delivered',
      date: order?.delivery_date || summary?.delivery_date,
      detail: order?.order_item_status || null,
      done: !!(order?.delivery_date || summary?.delivery_date),
      color: order?.order_item_status === 'Cancelled' ? '#E8344A' : '#10B981',
    },
    {
      key: 'settled',
      label: 'Settled by Flipkart',
      date: settlement?.settlement_date || summary?.settlement_date,
      detail: settlement?.neft_id ? `NEFT: ${settlement.neft_id}` : (summary?.neft_id ? `NEFT: ${summary.neft_id}` : null),
      done: !!(settlement?.settlement_date || summary?.settlement_date),
      color: '#2563EB',
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'row', flexShrink: 0, position: 'relative' }}>
      {/* Drag handle */}
      <div
        onMouseDown={onDragStart}
        style={{ width: 6, cursor: 'col-resize', background: 'transparent', flexShrink: 0, transition: 'background .15s' }}
        onMouseEnter={e => e.currentTarget.style.background = '#0ABFCA40'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        <div style={{ width: 2, height: '100%', background: '#E2E8F0', margin: '0 2px' }} />
      </div>

      {/* Panel body */}
      <div style={{ width: minimized ? 40 : width, minWidth: minimized ? 40 : 300, background: '#fff', borderLeft: '1.5px solid #E8EFF6', display: 'flex', flexDirection: 'column', transition: minimized ? 'width .2s ease' : 'none', overflow: 'hidden' }}>
        {minimized ? (
          // Minimized tab
          <button
            onClick={() => setMinimized(false)}
            style={{ flex: 1, border: 'none', background: '#F8FAFC', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '12px 0' }}
          >
            <span style={{ fontSize: 16 }}>⏱</span>
            <span style={{ fontSize: 10, fontWeight: 700, color: '#6B7280', writingMode: 'vertical-rl', textOrientation: 'mixed', letterSpacing: '.06em', textTransform: 'uppercase' }}>Timeline</span>
          </button>
        ) : (
          <>
            {/* Header */}
            <div style={{ padding: '14px 16px 12px', borderBottom: '1px solid #F1F5F9', display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: '#0D1F35' }}>Order Timeline</div>
                <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2, fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {orderItemId}
                </div>
                {(order?.product_title || summary?.product_title) && (
                  <div style={{ fontSize: 11, color: '#374151', marginTop: 4, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {order?.product_title || summary?.product_title}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <button onClick={() => setMinimized(true)} title="Minimise" style={{ width: 26, height: 26, border: '1px solid #E5E7EB', borderRadius: 6, background: '#fff', cursor: 'pointer', fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6B7280' }}>−</button>
                <button onClick={onClose} title="Close" style={{ width: 26, height: 26, border: '1px solid #E5E7EB', borderRadius: 6, background: '#fff', cursor: 'pointer', fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6B7280' }}>✕</button>
              </div>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
              {loading && <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#9CA3AF', fontSize: 13 }}><Spin />Loading…</div>}
              {error && <div style={{ color: '#E8344A', fontSize: 12 }}>{error}</div>}

              {!loading && !error && (
                <>
                  {/* Timeline */}
                  <div style={{ marginBottom: 20 }}>
                    {steps.map((step, i) => (
                      <div key={step.key} style={{ display: 'flex', gap: 12, marginBottom: i < steps.length - 1 ? 0 : 0 }}>
                        {/* Dot + line */}
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                          <div style={{ width: 28, height: 28, borderRadius: '50%', background: step.done ? step.color : '#F1F5F9', border: `2px solid ${step.done ? step.color : '#E2E8F0'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, flexShrink: 0 }}>
                            {step.done ? '✓' : '·'}
                          </div>
                          {i < steps.length - 1 && (
                            <div style={{ width: 2, flex: 1, minHeight: 24, background: step.done ? step.color + '40' : '#F1F5F9', margin: '2px 0' }} />
                          )}
                        </div>
                        {/* Content */}
                        <div style={{ paddingBottom: i < steps.length - 1 ? 16 : 0, paddingTop: 3, minWidth: 0 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: step.done ? '#0D1F35' : '#9CA3AF' }}>{step.label}</div>
                          {step.date && <div style={{ fontSize: 11, color: step.color, fontWeight: 600, marginTop: 2 }}>{fmtDate(step.date)}</div>}
                          {step.detail && <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{step.detail}</div>}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Settlement summary */}
                  {(settlement || summary?.settlement_amount != null) && (
                    <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 10, padding: '12px 14px', marginBottom: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#10B981', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 8 }}>Settlement Summary</div>
                      {[
                        ['Sale Amount', settlement?.sale_amount ?? summary?.sale_amount],
                        ['Marketplace Fee', settlement?.marketplace_fee ?? summary?.marketplace_fee],
                        ['TCS', settlement?.tcs ?? summary?.tcs],
                        ['TDS', settlement?.tds ?? summary?.tds],
                        ['Settlement Amount', settlement?.settlement_amount ?? summary?.settlement_amount],
                      ].map(([label, val]) => (
                        val != null && (
                          <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                            <span style={{ color: '#6B7280' }}>{label}</span>
                            <span style={{ fontWeight: 600, color: '#0D1F35' }}>{inr2(val)}</span>
                          </div>
                        )
                      ))}
                    </div>
                  )}

                  {/* Fees */}
                  {fees.length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 8 }}>Commission Invoice ({fees.length} lines)</div>
                      {fees.map((f, i) => (
                        <div key={i} style={{ background: '#FAFAFA', border: '1px solid #F1F5F9', borderRadius: 8, padding: '8px 10px', marginBottom: 6 }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: '#374151', marginBottom: 4 }}>{f.fee_name || 'Fee'}</div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                            <span style={{ color: '#9CA3AF' }}>Fee</span>
                            <span style={{ fontWeight: 600 }}>{inr2(f.fee_amount)}</span>
                          </div>
                          {Number(f.fee_waiver_amount) !== 0 && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#9CA3AF' }}>Waiver</span>
                              <span style={{ fontWeight: 600, color: '#10B981' }}>−{inr2(f.fee_waiver_amount)}</span>
                            </div>
                          )}
                          {Number(f.tax_amount) !== 0 && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#9CA3AF' }}>GST</span>
                              <span style={{ fontWeight: 600 }}>{inr2(f.tax_amount)}</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── FlipkartOrderDetail ───────────────────────────────────────────────────────
function FlipkartOrderDetail({ item, onBack, onOpenLifecycle }) {
  const s = SC[item.status] || SC.MISSING_ORDER
  const diff = Number(item.difference) || 0

  const FINANCIAL_ROWS = [
    { label: 'Sale Amount',        val: item.sale_amount,          color: '#10B981' },
    { label: 'Total Offer Amount', val: item.total_offer_amount,   color: '#6B7280' },
    { label: 'My Share (Discount)',val: item.my_share,             color: '#6B7280' },
    { label: 'Marketplace Fee',    val: item.marketplace_fee,      color: '#E8344A' },
    { label: 'TCS',                val: item.tcs,                  color: '#E8344A' },
    { label: 'TDS',                val: item.tds,                  color: '#E8344A' },
    { label: 'GST on MP Fees',     val: item.gst_on_mp_fees,       color: '#E8344A' },
    { label: 'Refund / Return',    val: item.refund,               color: '#E8344A' },
  ]

  return (
    <div>
      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
        <button onClick={onBack} style={{ background: '#F3F4F6', border: 'none', borderRadius: 8, padding: '6px 12px', fontSize: 13, color: '#6B7280', cursor: 'pointer' }}>← Back</button>
        <span style={{ color: '#CBD5E1', fontSize: 13 }}>Results</span>
        <span style={{ color: '#CBD5E1', fontSize: 13 }}>›</span>
        <span style={{ fontSize: 13, color: '#0D1F35', fontWeight: 600, fontFamily: 'monospace' }}>{item.order_item_id}</span>
        <span style={{ marginLeft: 'auto' }}>
          <span style={{ background: s.badgeBg, color: s.badge, borderRadius: 6, padding: '3px 10px', fontSize: 12, fontWeight: 700 }}>{s.text}</span>
        </span>
      </div>

      {/* Product info */}
      {(item.product_title || item.sku) && (
        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 10, padding: '12px 16px', marginBottom: 16 }}>
          {item.product_title && <div style={{ fontSize: 14, fontWeight: 700, color: '#0D1F35', marginBottom: 6 }}>{item.product_title}</div>}
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            {item.sku && <span style={{ fontSize: 12, color: '#6B7280' }}>SKU: <strong>{item.sku}</strong></span>}
            {item.fsn && <span style={{ fontSize: 12, color: '#6B7280' }}>FSN: <strong>{item.fsn}</strong></span>}
            {item.order_date && <span style={{ fontSize: 12, color: '#6B7280' }}>Order Date: <strong>{fmtDate(item.order_date)}</strong></span>}
            {item.delivery_date && <span style={{ fontSize: 12, color: '#6B7280' }}>Delivery: <strong>{fmtDate(item.delivery_date)}</strong></span>}
            {item.settlement_date && <span style={{ fontSize: 12, color: '#6B7280' }}>Settled: <strong>{fmtDate(item.settlement_date)}</strong></span>}
          </div>
        </div>
      )}

      {/* IDs row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
        {[
          { label: 'Order Item ID', val: item.order_item_id },
          { label: 'Order ID',      val: item.order_id, clickable: true },
          { label: 'NEFT ID',       val: item.neft_id },
          { label: 'NEFT Type',     val: item.neft_type },
        ].map(({ label, val, clickable }) => val ? (
          <div key={label} style={{ background: '#fff', border: '1px solid #E8EFF6', borderRadius: 8, padding: '10px 14px' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 4 }}>{label}</div>
            {clickable ? (
              <button
                onClick={() => onOpenLifecycle(item.order_item_id)}
                style={{ background: 'none', border: 'none', padding: 0, fontSize: 13, fontFamily: 'monospace', fontWeight: 700, color: '#0ABFCA', cursor: 'pointer', textDecoration: 'underline' }}
              >
                {val}
              </button>
            ) : (
              <div style={{ fontSize: 13, fontFamily: 'monospace', fontWeight: 600, color: '#0D1F35' }}>{val}</div>
            )}
          </div>
        ) : null)}
      </div>

      {/* KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'Sale Amount',     val: item.sale_amount,         color: '#10B981', bg: '#F0FDF4' },
          { label: 'Total Fees',      val: -(Number(item.invoice_fee_total) + Number(item.invoice_gst_total)), color: '#E8344A', bg: '#FFF1F2' },
          { label: 'Expected',        val: item.expected_settlement,  color: '#2563EB', bg: '#EFF6FF' },
          { label: 'Actual',          val: item.settlement_amount,    color: '#0ABFCA', bg: '#F0FDFA' },
        ].map(c => (
          <div key={c.label} style={{ background: c.bg, borderRadius: 10, padding: '12px 14px', border: `1px solid ${c.color}25` }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: c.color, textTransform: 'uppercase', letterSpacing: '.06em' }}>{c.label}</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: c.color, marginTop: 4 }}>{c.val != null ? inr2(c.val) : '—'}</div>
          </div>
        ))}
      </div>

      {/* Difference banner */}
      {item.difference != null && (
        <div style={{ background: Math.abs(diff) <= 2 ? '#F0FDF4' : diff < 0 ? '#FFF1F2' : '#FFFBEB', border: `1px solid ${Math.abs(diff) <= 2 ? '#BBF7D0' : diff < 0 ? '#FECDD3' : '#FDE68A'}`, borderRadius: 10, padding: '10px 16px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 20, fontWeight: 900, color: Math.abs(diff) <= 2 ? '#10B981' : diff < 0 ? '#E8344A' : '#D97706' }}>
            {diff > 0 ? '+' : ''}{inr2(diff)}
          </div>
          <div style={{ fontSize: 12, color: '#6B7280' }}>
            {Math.abs(diff) <= 2 ? 'Within Rs.2 tolerance — MATCHED' : diff < 0 ? 'Flipkart paid less than expected' : 'Flipkart paid more than expected (fee waiver / rebate)'}
          </div>
        </div>
      )}

      {/* Settlement components */}
      <div style={{ background: '#fff', border: '1.5px solid #E8EFF6', borderRadius: 12, overflow: 'hidden', marginBottom: 16 }}>
        <div style={{ padding: '12px 16px', background: '#F8FAFC', borderBottom: '1px solid #E8EFF6', fontSize: 12, fontWeight: 700, color: '#374151' }}>
          Settlement Components
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <tbody>
            {FINANCIAL_ROWS.map(row => Number(row.val) !== 0 && row.val != null ? (
              <tr key={row.label} style={{ borderBottom: '1px solid #F8FAFC' }}>
                <td style={{ padding: '8px 16px', color: '#6B7280' }}>{row.label}</td>
                <td style={{ padding: '8px 16px', textAlign: 'right', fontWeight: 700, color: row.color, fontFamily: 'monospace' }}>{inr2(row.val)}</td>
              </tr>
            ) : null)}
            <tr style={{ background: '#F8FAFC' }}>
              <td style={{ padding: '10px 16px', fontWeight: 700, color: '#0D1F35' }}>Invoice Fee Total</td>
              <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 800, color: '#E8344A', fontFamily: 'monospace' }}>{inr2(item.invoice_fee_total)}</td>
            </tr>
            <tr style={{ background: '#F8FAFC' }}>
              <td style={{ padding: '10px 16px', fontWeight: 700, color: '#0D1F35' }}>Invoice GST Total</td>
              <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 800, color: '#E8344A', fontFamily: 'monospace' }}>{inr2(item.invoice_gst_total)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* View timeline button */}
      <button
        onClick={() => onOpenLifecycle(item.order_item_id)}
        style={{ padding: '10px 22px', borderRadius: 9, border: 'none', background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7 }}
      >
        ⏱ View Order Timeline
      </button>
    </div>
  )
}

// ── Table columns ──────────────────────────────────────────────────────────────
const COLS = [
  { key: 'order_item_id',      label: 'Order Item ID',  w: 185, mono: true },
  { key: 'order_id',           label: 'Order ID',       w: 185, mono: true, clickable: true },
  { key: 'sku',                label: 'SKU',            w: 150 },
  { key: 'sale_amount',        label: 'Sale (₹)',       w: 95,  num: true },
  { key: 'invoice_fee_total',  label: 'Inv Fee (₹)',    w: 95,  num: true },
  { key: 'invoice_gst_total',  label: 'Inv GST (₹)',    w: 85,  num: true },
  { key: 'tcs',                label: 'TCS (₹)',        w: 75,  num: true },
  { key: 'tds',                label: 'TDS (₹)',        w: 75,  num: true },
  { key: 'expected_settlement',label: 'Expected (₹)',   w: 115, num: true },
  { key: 'settlement_amount',  label: 'Actual (₹)',     w: 105, num: true },
  { key: 'difference',         label: 'Diff (₹)',       w: 90,  num: true },
  { key: 'status',             label: 'Status',         w: 140 },
]

// ── FlipkartReconTable ────────────────────────────────────────────────────────
export function FlipkartReconTable({ summary, items, onBack, onNewUpload }) {
  const [filterStatus, setFilterStatus] = useState('ALL')
  const [search, setSearch]             = useState('')
  const [sort, setSort]                 = useState({ col: 'status', dir: 'asc' })
  const [page, setPage]                 = useState(1)
  const [detailItem, setDetailItem]     = useState(null)   // null = table, set = detail view
  const [lifecycle, setLifecycle]       = useState(null)   // null = closed
  const [panelWidth, setPanelWidth]     = useState(420)
  const PAGE_SIZE = 100

  function openLifecycle(orderItemId) {
    setLifecycle({ orderItemId })
  }
  function closeLifecycle() { setLifecycle(null) }

  const filtered = items
    .filter(r => filterStatus === 'ALL' || r.status === filterStatus)
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

  function toggleSort(col) { setSort(p => ({ col, dir: p.col === col && p.dir === 'asc' ? 'desc' : 'asc' })); setPage(1) }

  const shortTotal = items.filter(r => r.status === 'SHORT_PAID').reduce((s, r) => s + Math.abs(Number(r.difference) || 0), 0)
  const overTotal  = items.filter(r => r.status === 'OVER_PAID').reduce((s,  r) => s + Math.abs(Number(r.difference) || 0), 0)
  const netLeak    = shortTotal - overTotal

  const TABS = [
    { key: 'ALL',               label: 'All',          count: items.length,                     color: '#0D1F35' },
    { key: 'SHORT_PAID',        label: 'Short Paid',   count: summary?.short_paid        ?? 0,  color: '#E8344A' },
    { key: 'OVER_PAID',         label: 'Over Paid',    count: summary?.over_paid         ?? 0,  color: '#D97706' },
    { key: 'MATCHED',           label: 'Matched',      count: summary?.matched           ?? 0,  color: '#10B981' },
    { key: 'RETURN_RECOVERY',   label: 'Returns',      count: summary?.return_recovery   ?? 0,  color: '#2563EB' },
    { key: 'MISSING_SETTLEMENT',label: 'No Settlement',count: summary?.missing_settlement ?? 0, color: '#F97316' },
    { key: 'MISSING_FEE_RECORD',label: 'No Fee Record',count: summary?.missing_fee_record ?? 0, color: '#CA8A04' },
  ]

  const KPI_CARDS = [
    { label: 'Short Paid',       value: inr(shortTotal), sub: `${summary?.short_paid ?? 0} orders`,          color: '#E8344A', bg: '#FFF1F2' },
    { label: 'Over Paid',        value: inr(overTotal),  sub: `${summary?.over_paid ?? 0} orders`,           color: '#D97706', bg: '#FFFBEB' },
    { label: 'Net Underpayment', value: inr(netLeak),    sub: netLeak > 0 ? 'Flipkart owes you' : 'You owe Flipkart', color: netLeak > 0 ? '#E8344A' : '#10B981', bg: netLeak > 0 ? '#FFF1F2' : '#F0FDF4' },
    { label: 'Returns',          value: String(summary?.return_recovery ?? 0), sub: 'return/refund orders',  color: '#2563EB', bg: '#EFF6FF' },
  ]

  const mainContent = detailItem ? (
    <FlipkartOrderDetail
      item={detailItem}
      onBack={() => setDetailItem(null)}
      onOpenLifecycle={openLifecycle}
    />
  ) : (
    <>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button onClick={onBack} style={{ background: '#F3F4F6', border: 'none', borderRadius: 8, padding: '6px 12px', fontSize: 13, color: '#6B7280', cursor: 'pointer' }}>← Back</button>
        <div>
          <div style={{ fontSize: 17, fontWeight: 800, color: '#0D1F35' }}>Flipkart Reconciliation Results</div>
          <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{items.length} order items analysed</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button onClick={onNewUpload} style={{ padding: '7px 16px', borderRadius: 8, border: '1.5px solid #E5E7EB', background: '#fff', color: '#6B7280', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
            ↑ Upload New Files
          </button>
          <button onClick={() => window.open(`${MICRO}/reconciliation/export?period=April+2026`, '_blank')} style={{ padding: '7px 16px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg,#0ABFCA,#088F99)', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
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
            <button key={t.key} onClick={() => { setFilterStatus(t.key); setPage(1) }} style={{ padding: '5px 13px', borderRadius: 20, border: `1.5px solid ${active ? t.color : '#E5E7EB'}`, background: active ? t.color + '18' : '#fff', color: active ? t.color : '#6B7280', fontSize: 12, fontWeight: active ? 700 : 500, cursor: 'pointer', whiteSpace: 'nowrap' }}>
              {t.label} <span style={{ opacity: .7 }}>({t.count})</span>
            </button>
          )
        })}
        <input value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} placeholder="Search Order ID or SKU…" style={{ marginLeft: 'auto', padding: '7px 14px', borderRadius: 8, border: '1.5px solid #E5E7EB', fontSize: 13, outline: 'none', width: 230 }} />
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto', borderRadius: 12, border: '1.5px solid #E8EFF6', boxShadow: '0 2px 12px rgba(0,0,0,.05)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {COLS.map(c => (
                <th key={c.key} onClick={() => toggleSort(c.key)} style={{ padding: '11px 12px', textAlign: c.num ? 'right' : 'left', background: '#0D1F35', color: '#CBD5E1', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap', minWidth: c.w, borderRight: '1px solid rgba(255,255,255,.07)' }}>
                  {c.label}{sort.col === c.key ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr><td colSpan={COLS.length} style={{ textAlign: 'center', padding: '48px', color: '#9CA3AF', fontSize: 14 }}>No records match your filter</td></tr>
            ) : visible.map((r, i) => {
              const s    = SC[r.status] || SC.MISSING_ORDER
              const diff = Number(r.difference) || 0
              const rowBg = i % 2 === 0 ? s.rowBg : s.rowBg + 'bb'

              return (
                <tr
                  key={r.order_item_id + i}
                  onClick={() => setDetailItem(r)}
                  style={{ background: rowBg, borderBottom: `1px solid ${s.border}`, cursor: 'pointer', transition: 'filter .1s' }}
                  onMouseEnter={e => e.currentTarget.style.filter = 'brightness(0.97)'}
                  onMouseLeave={e => e.currentTarget.style.filter = 'none'}
                >
                  {COLS.map(c => {
                    const val = r[c.key]
                    const base = { padding: '8px 12px', textAlign: c.num ? 'right' : 'left', whiteSpace: 'nowrap', color: '#1E293B' }

                    if (c.key === 'status') {
                      return (
                        <td key={c.key} style={base}>
                          <span style={{ background: s.badgeBg, color: s.badge, borderRadius: 6, padding: '3px 9px', fontSize: 11, fontWeight: 700 }}>{s.text}</span>
                        </td>
                      )
                    }

                    if (c.clickable && val) {
                      return (
                        <td key={c.key} style={base}>
                          <button
                            onClick={e => { e.stopPropagation(); openLifecycle(r.order_item_id) }}
                            style={{ background: 'none', border: 'none', padding: 0, fontSize: 11, fontFamily: 'monospace', fontWeight: 700, color: '#0ABFCA', cursor: 'pointer', textDecoration: 'underline' }}
                          >
                            {val}
                          </button>
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

      {/* Pagination */}
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
    </>
  )

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: 0 }}>
      {/* Main area */}
      <div style={{ flex: 1, minWidth: 0, overflow: 'auto' }}>
        {mainContent}
      </div>

      {/* Lifecycle panel */}
      {lifecycle && (
        <LifecyclePanel
          orderItemId={lifecycle.orderItemId}
          items={items}
          onClose={closeLifecycle}
          width={panelWidth}
          onWidthChange={setPanelWidth}
        />
      )}
    </div>
  )
}
