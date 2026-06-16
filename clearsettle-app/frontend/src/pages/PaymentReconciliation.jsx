import React, { useState, useEffect } from 'react'
import useApi from '../hooks/useApi'
import api from '../utils/api'
import { INR, INRL } from '../utils/format'

// ─── Reconciliation status helpers ───────────────────────────────────────────

var RECON_COLOR = {
  MATCHED: '#0DB07A', SHORT_PAID: '#E8344A', OVER_PAID: '#E9930D',
  MISSING_SETTLEMENT: '#8B5CF6', RETURN_RECOVERY: '#0ABFCA',
  MISSING_FEE_RECORD: '#8FA5BD', MISSING_ORDER: '#E8344A', PARTIAL: '#E9930D',
}
var RECON_BG = {
  MATCHED: 'rgba(13,176,122,.12)', SHORT_PAID: 'rgba(232,52,74,.12)',
  OVER_PAID: 'rgba(233,147,13,.12)', MISSING_SETTLEMENT: 'rgba(139,92,246,.12)',
  RETURN_RECOVERY: 'rgba(10,191,202,.12)', MISSING_FEE_RECORD: 'rgba(143,165,189,.12)',
  MISSING_ORDER: 'rgba(232,52,74,.12)', PARTIAL: 'rgba(233,147,13,.12)',
}
var RECON_LABEL = {
  MATCHED: 'Matched', SHORT_PAID: 'Short Paid', OVER_PAID: 'Over Paid',
  MISSING_SETTLEMENT: 'Missing Settlement', RETURN_RECOVERY: 'Return Recovery',
  MISSING_FEE_RECORD: 'No Fee Record', MISSING_ORDER: 'Missing Order', PARTIAL: 'Partial',
}

function ReconChip({ status }) {
  var c = RECON_COLOR[status] || '#8FA5BD'
  var bg = RECON_BG[status] || 'rgba(143,165,189,.12)'
  var lbl = RECON_LABEL[status] || status
  return (
    <span style={{
      background: bg, color: c, borderRadius: 6,
      padding: '3px 9px', fontSize: 11, fontWeight: 700,
      whiteSpace: 'nowrap', display: 'inline-block',
    }}>
      {lbl}
    </span>
  )
}

// ─── Spinner ─────────────────────────────────────────────────────────────────

function Spin() {
  return <div className="loading-wrap" style={{ minHeight: 120 }}><div className="spinner" /></div>
}

// ─── KPI Cards ───────────────────────────────────────────────────────────────

function KpiCards({ kpis }) {
  if (!kpis) return null
  var cards = [
    { label: 'Total Payments', value: kpis.total_payments, stripe: 'tl', sub: 'NEFT batches' },
    { label: 'Total Orders',   value: kpis.total_orders,   stripe: 'tl', sub: 'Settled order items' },
    { label: 'Total Settlement', value: INRL(kpis.total_settlement), stripe: 'tl', sub: 'Sum of all NEFT payouts', raw: true },
    { label: 'Matched Orders', value: kpis.matched_orders, stripe: 'gn', sub: 'Formula verified' },
    { label: 'Potential Leakage', value: kpis.potential_leakage_count > 0 ? kpis.potential_leakage_count + ' orders · ' + INR(kpis.potential_leakage_amount) : 'None', stripe: 'gn', sub: 'SHORT_PAID count', raw: true },
    { label: 'Missing Settlements', value: kpis.missing_settlements, stripe: kpis.missing_settlements > 0 ? 'am' : 'gn', sub: 'Fee invoice, no settlement' },
  ]
  return (
    <div className="stats-row" style={{ gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 20 }}>
      {cards.map(function(c) {
        return (
          <div key={c.label} className="stat-card" style={{ padding: '14px 18px' }}>
            <div className={'sc-stripe ' + c.stripe} />
            <div className="sc-label" style={{ marginTop: 8, fontSize: 11 }}>{c.label}</div>
            <div className="sc-val" style={{ fontSize: 22 }}>{c.raw ? c.value : c.value?.toLocaleString('en-IN')}</div>
            <div className="sc-sub">{c.sub}</div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Payment List (Screen 1) ──────────────────────────────────────────────────

function PaymentList({ onSelect }) {
  var { data: payments, loading } = useApi('/payment-reconciliation/payments')
  var [search, setSearch]         = useState('')
  var [statusFilter, setStatusFilter] = useState('all')
  var [dateFrom, setDateFrom]     = useState('')
  var [dateTo, setDateTo]         = useState('')

  if (loading) return <Spin />

  var items = (payments || []).filter(function(p) {
    if (statusFilter !== 'all' && p.status !== statusFilter) return false
    if (search && !p.payment_id.toLowerCase().includes(search.toLowerCase())) return false
    if (dateFrom && p.settlement_date && p.settlement_date < dateFrom) return false
    if (dateTo && p.settlement_date && p.settlement_date > dateTo) return false
    return true
  })

  var statusCounts = (payments || []).reduce(function(acc, p) {
    acc[p.status] = (acc[p.status] || 0) + 1
    return acc
  }, {})

  return (
    <div>
      {/* Search + date filters */}
      <div className="filter-row" style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', gap: 8, flex: 1, flexWrap: 'wrap' }}>
          <input
            style={{ flex: '1 1 200px', minWidth: 0 }}
            placeholder="Search Payment ID..."
            value={search}
            onChange={function(e) { setSearch(e.target.value) }}
          />
          <input type="date" value={dateFrom} onChange={function(e) { setDateFrom(e.target.value) }}
            style={{ width: 150 }} title="From date" />
          <input type="date" value={dateTo} onChange={function(e) { setDateTo(e.target.value) }}
            style={{ width: 150 }} title="To date" />
        </div>
      </div>

      {/* Status pills */}
      <div className="filter-pills" style={{ marginBottom: 12 }}>
        <button className={'pill' + (statusFilter === 'all' ? ' active' : '')} onClick={function() { setStatusFilter('all') }}>
          All ({(payments || []).length})
        </button>
        {['MATCHED','PARTIAL','OVER_PAID','MISSING_SETTLEMENT','SHORT_PAID'].map(function(s) {
          var cnt = statusCounts[s] || 0
          if (!cnt) return null
          return (
            <button key={s} className={'pill' + (statusFilter === s ? ' active' : '')} onClick={function() { setStatusFilter(s) }}>
              {RECON_LABEL[s] || s} ({cnt})
            </button>
          )
        })}
      </div>

      {/* Table */}
      <div className="tw">
        <table>
          <thead>
            <tr>
              {['Payment ID','Settlement Date','Orders','Settlement Amount','Status',''].map(function(h) {
                return <th key={h}>{h}</th>
              })}
            </tr>
          </thead>
          <tbody>
            {items.map(function(p) {
              return (
                <tr key={p.payment_id} style={{ cursor: 'pointer' }} onClick={function() { onSelect(p) }}>
                  <td>
                    <span className="mono" style={{ color: '#0ABFCA', fontSize: 12 }}>{p.payment_id}</span>
                  </td>
                  <td style={{ color: '#4B6080' }}>{p.settlement_date || '—'}</td>
                  <td style={{ fontWeight: 600 }}>{p.order_count}</td>
                  <td style={{ fontWeight: 700 }}>{INR(p.total_settlement_amount)}</td>
                  <td><ReconChip status={p.status} /></td>
                  <td>
                    <button className="btn btn-g btn-sm" onClick={function(e) { e.stopPropagation(); onSelect(p) }}>
                      Investigate →
                    </button>
                  </td>
                </tr>
              )
            })}
            {items.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center', color: '#8FA5BD', padding: '32px 0' }}>
                No payments match the current filter
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 8 }}>
        {items.length} of {(payments || []).length} payments · Source: settlements_etl (deduplicated by order_item_id)
      </div>
    </div>
  )
}

// ─── Payment Detail (Screen 2) ────────────────────────────────────────────────

function PaymentDetail({ payment, onBack, onOrderSelect }) {
  var [detail, setDetail]     = useState(null)
  var [loading, setLoading]   = useState(true)
  var [search, setSearch]     = useState('')
  var [statusFilter, setStatusFilter] = useState('all')

  useEffect(function() {
    setLoading(true)
    setDetail(null)
    api.get('/payment-reconciliation/payment/' + encodeURIComponent(payment.payment_id))
      .then(function(res) { setDetail(res.data); setLoading(false) })
      .catch(function() { setLoading(false) })
  }, [payment.payment_id])

  if (loading) return <Spin />
  if (!detail) return (
    <div style={{ padding: 40, textAlign: 'center', color: '#8FA5BD' }}>
      Failed to load payment details.
    </div>
  )

  var orders = (detail.orders || []).filter(function(o) {
    if (statusFilter !== 'all' && o.status !== statusFilter) return false
    if (search) {
      var q = search.toLowerCase()
      return (o.order_item_id || '').toLowerCase().includes(q)
          || (o.order_id || '').toLowerCase().includes(q)
          || (o.sku || '').toLowerCase().includes(q)
          || (o.product_title || '').toLowerCase().includes(q)
    }
    return true
  })

  var statusCounts = (detail.orders || []).reduce(function(acc, o) {
    acc[o.status] = (acc[o.status] || 0) + 1
    return acc
  }, {})

  return (
    <div>
      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <button className="btn btn-s btn-sm" onClick={onBack}>← Back</button>
        <span style={{ color: '#8FA5BD', fontSize: 13 }}>Payment Reconciliation</span>
        <span style={{ color: '#8FA5BD' }}>›</span>
        <span className="mono" style={{ color: '#0ABFCA', fontSize: 13 }}>{payment.payment_id}</span>
      </div>

      {/* Payment header summary */}
      <div style={{ background: '#F8FAFC', border: '1px solid #E2EBF3', borderRadius: 12, padding: '16px 20px', marginBottom: 18, display: 'flex', gap: 32, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 2 }}>Payment ID</div>
          <div className="mono" style={{ fontWeight: 700, color: '#0ABFCA' }}>{detail.payment_id}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 2 }}>Settlement Date</div>
          <div style={{ fontWeight: 700 }}>{detail.settlement_date || '—'}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 2 }}>Total Orders</div>
          <div style={{ fontWeight: 700 }}>{detail.total_orders}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#8FA5BD', marginBottom: 2 }}>Total Settlement</div>
          <div style={{ fontWeight: 800, color: '#0DB07A', fontSize: 18 }}>{INR(detail.total_settlement)}</div>
        </div>
        {/* Reconciliation summary pills */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          {Object.entries(statusCounts).map(function([s, cnt]) {
            return (
              <span key={s} style={{
                background: RECON_BG[s] || 'rgba(143,165,189,.12)',
                color: RECON_COLOR[s] || '#8FA5BD',
                borderRadius: 6, padding: '3px 9px', fontSize: 11, fontWeight: 700,
              }}>
                {RECON_LABEL[s] || s}: {cnt}
              </span>
            )
          })}
        </div>
      </div>

      {/* Order grid filters */}
      <div className="filter-row" style={{ marginBottom: 10 }}>
        <div className="filter-pills" style={{ marginBottom: 0 }}>
          <button className={'pill' + (statusFilter === 'all' ? ' active' : '')} onClick={function() { setStatusFilter('all') }}>
            All ({(detail.orders || []).length})
          </button>
          {Object.entries(statusCounts).map(function([s, cnt]) {
            return (
              <button key={s} className={'pill' + (statusFilter === s ? ' active' : '')} onClick={function() { setStatusFilter(s) }}>
                {RECON_LABEL[s] || s} ({cnt})
              </button>
            )
          })}
        </div>
        <div className="filter-search">
          <input
            placeholder="Search order, SKU, product..."
            value={search}
            onChange={function(e) { setSearch(e.target.value) }}
          />
        </div>
      </div>

      {/* Order grid */}
      <div className="tw">
        <table>
          <thead>
            <tr>
              {['Order Item ID','Order ID','Product / SKU','Selling Price','Expected','Actual','Difference','Status',''].map(function(h) {
                return <th key={h}>{h}</th>
              })}
            </tr>
          </thead>
          <tbody>
            {orders.map(function(o) {
              var diff = o.difference
              var diffColor = diff === null ? '#8FA5BD' : diff > 2 ? '#E9930D' : diff < -2 ? '#E8344A' : '#0DB07A'
              return (
                <tr key={o.order_item_id} style={{ cursor: 'pointer' }} onClick={function() { onOrderSelect(o.order_item_id) }}>
                  <td>
                    <span className="mono" style={{ color: '#0ABFCA', fontSize: 11 }}>{o.order_item_id}</span>
                  </td>
                  <td>
                    <span className="mono" style={{ fontSize: 11, color: '#4B6080' }}>{o.order_id}</span>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, fontSize: 12 }}>{o.product_title || '—'}</div>
                    <div style={{ fontSize: 10, color: '#8FA5BD' }}>{o.sku}</div>
                  </td>
                  <td>{o.selling_price != null ? INR(o.selling_price) : '—'}</td>
                  <td>{o.expected_settlement != null ? INR(o.expected_settlement) : '—'}</td>
                  <td style={{ fontWeight: 700 }}>{o.actual_settlement != null ? INR(o.actual_settlement) : '—'}</td>
                  <td style={{ fontWeight: 700, color: diffColor }}>
                    {diff === null ? '—' : (diff >= 0 ? '+' : '') + INR(diff)}
                  </td>
                  <td><ReconChip status={o.status} /></td>
                  <td>
                    <button className="btn btn-g btn-sm" onClick={function(e) { e.stopPropagation(); onOrderSelect(o.order_item_id) }}>
                      View
                    </button>
                  </td>
                </tr>
              )
            })}
            {orders.length === 0 && (
              <tr><td colSpan={9} style={{ textAlign: 'center', color: '#8FA5BD', padding: '32px 0' }}>
                No orders match the current filter
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 8 }}>
        {orders.length} orders · Source: settlements_etl + order_financials + orders_etl
      </div>
    </div>
  )
}

// ─── Order Investigation Drawer ───────────────────────────────────────────────

function OrderDrawer({ orderItemId, onClose }) {
  var [activeTab, setActiveTab]   = useState(0)
  var [timeline, setTimeline]     = useState(null)
  var [financials, setFinancials] = useState(null)
  var [debugData, setDebugData]   = useState(null)
  var [loading, setLoading]       = useState({})

  useEffect(function() {
    if (!orderItemId) return
    // Load timeline on open
    setLoading(function(prev) { return Object.assign({}, prev, { timeline: true }) })
    api.get('/payment-reconciliation/order/' + orderItemId + '/timeline')
      .then(function(res) {
        setTimeline(res.data)
        setLoading(function(prev) { return Object.assign({}, prev, { timeline: false }) })
      })
      .catch(function() { setLoading(function(prev) { return Object.assign({}, prev, { timeline: false }) }) })
  }, [orderItemId])

  useEffect(function() {
    if (!orderItemId || (activeTab !== 1 && activeTab !== 2) || financials) return
    setLoading(function(prev) { return Object.assign({}, prev, { financials: true }) })
    api.get('/payment-reconciliation/order/' + orderItemId + '/financials')
      .then(function(res) {
        setFinancials(res.data)
        setLoading(function(prev) { return Object.assign({}, prev, { financials: false }) })
      })
      .catch(function() { setLoading(function(prev) { return Object.assign({}, prev, { financials: false }) }) })
  }, [orderItemId, activeTab])

  useEffect(function() {
    if (!orderItemId || activeTab !== 3 || debugData) return
    setLoading(function(prev) { return Object.assign({}, prev, { debug: true }) })
    api.get('/payment-reconciliation/order/' + orderItemId + '/debug')
      .then(function(res) {
        setDebugData(res.data)
        setLoading(function(prev) { return Object.assign({}, prev, { debug: false }) })
      })
      .catch(function() { setLoading(function(prev) { return Object.assign({}, prev, { debug: false }) }) })
  }, [orderItemId, activeTab])

  var tabs = ['Order Timeline', 'Financial Timeline', 'Reconciliation', 'Source Data']

  return (
    <div
      onClick={function(e) { if (e.target === e.currentTarget) onClose() }}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(13,31,53,.55)',
        zIndex: 1000, display: 'flex', justifyContent: 'flex-end',
      }}
    >
      <div style={{
        width: '100%', maxWidth: 680, background: '#fff',
        height: '100vh', display: 'flex', flexDirection: 'column',
        boxShadow: '-8px 0 40px rgba(0,0,0,.18)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: '18px 20px 14px',
          borderBottom: '1px solid #E2EBF3',
          display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
          flexShrink: 0,
        }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 800, color: '#0D1F35' }}>Order Investigation</div>
            <div className="mono" style={{ fontSize: 11, color: '#0ABFCA', marginTop: 3 }}>{orderItemId}</div>
          </div>
          <button
            onClick={onClose}
            style={{
              width: 30, height: 30, borderRadius: 8,
              background: '#F1F5F9', border: 'none', cursor: 'pointer',
              fontSize: 14, color: '#4B6080', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >✕</button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex', borderBottom: '1px solid #E2EBF3',
          padding: '0 20px', flexShrink: 0,
        }}>
          {tabs.map(function(t, i) {
            return (
              <button
                key={t}
                onClick={function() { setActiveTab(i) }}
                style={{
                  padding: '10px 14px',
                  fontSize: 12, fontWeight: 600,
                  color: activeTab === i ? '#0ABFCA' : '#8FA5BD',
                  borderBottom: activeTab === i ? '2px solid #0ABFCA' : '2px solid transparent',
                  background: 'none', border: 'none', cursor: 'pointer',
                  marginBottom: -1,
                  transition: 'color .15s',
                }}
              >
                {t}
              </button>
            )
          })}
        </div>

        {/* Tab content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>

          {/* Tab 0: Order Timeline */}
          {activeTab === 0 && (
            loading.timeline
              ? <Spin />
              : timeline
                ? <TimelineTab timeline={timeline} />
                : <div style={{ color: '#8FA5BD', textAlign: 'center', marginTop: 40 }}>No timeline data available</div>
          )}

          {/* Tab 1: Financial Timeline */}
          {activeTab === 1 && (
            loading.financials
              ? <Spin />
              : financials
                ? <FinancialsTab financials={financials} />
                : <div style={{ color: '#8FA5BD', textAlign: 'center', marginTop: 40 }}>No financial data available</div>
          )}

          {/* Tab 2: Reconciliation Breakdown */}
          {activeTab === 2 && (
            loading.financials
              ? <Spin />
              : financials
                ? <ReconciliationTab financials={financials} />
                : <div style={{ color: '#8FA5BD', textAlign: 'center', marginTop: 40 }}>No reconciliation data available</div>
          )}

          {/* Tab 3: Source Data */}
          {activeTab === 3 && (
            loading.debug
              ? <Spin />
              : debugData
                ? <SourceDataTab debugData={debugData} />
                : <div style={{ color: '#8FA5BD', textAlign: 'center', marginTop: 40 }}>No source data available</div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Tab 1: Order Timeline ────────────────────────────────────────────────────

var EVENT_ICON = {
  ORDER_CREATED: '📦', DISPATCHED: '🚚', DELIVERED: '✅', SETTLED: '💰',
  RETURNED: '↩️', RETURN_REQUESTED: '🔄', RETURN_COMPLETED: '↩️',
  REFUNDED: '💸', CANCELLED: '❌',
}
var EVENT_COLOR = {
  ORDER_CREATED: '#0ABFCA', DISPATCHED: '#E9930D', DELIVERED: '#0DB07A',
  SETTLED: '#7C3AED', RETURNED: '#E8344A', RETURN_REQUESTED: '#E8344A',
  RETURN_COMPLETED: '#E8344A', REFUNDED: '#E8344A', CANCELLED: '#8FA5BD',
}

function TimelineTab({ timeline }) {
  var events = (timeline.events || [])

  return (
    <div>
      {/* Summary header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 8 }}>
          <div style={{ background: '#F1F5F9', borderRadius: 8, padding: '8px 14px' }}>
            <div style={{ fontSize: 10, color: '#8FA5BD' }}>Current Status</div>
            <ReconChip status={timeline.current_status || 'UNKNOWN'} />
          </div>
          {timeline.payment_id && (
            <div style={{ background: '#F1F5F9', borderRadius: 8, padding: '8px 14px' }}>
              <div style={{ fontSize: 10, color: '#8FA5BD' }}>Payment ID</div>
              <div className="mono" style={{ fontSize: 12, fontWeight: 700, color: '#0ABFCA' }}>{timeline.payment_id}</div>
            </div>
          )}
        </div>
      </div>

      {/* Timeline events */}
      <div style={{ position: 'relative' }}>
        {events.map(function(ev, i) {
          var color = EVENT_COLOR[ev.event] || '#8FA5BD'
          var icon  = EVENT_ICON[ev.event] || '•'
          var isLast = i === events.length - 1
          return (
            <div key={i} style={{ display: 'flex', gap: 14, marginBottom: isLast ? 0 : 20 }}>
              {/* Line + circle */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0, width: 32 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: color + '20', border: '2px solid ' + color,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 14, flexShrink: 0,
                }}>
                  {icon}
                </div>
                {!isLast && (
                  <div style={{ width: 2, flex: 1, background: '#E2EBF3', margin: '4px 0', minHeight: 16 }} />
                )}
              </div>
              {/* Content */}
              <div style={{ paddingTop: 4, flex: 1 }}>
                <div style={{ fontWeight: 700, color: color, fontSize: 13, marginBottom: 2 }}>{ev.event}</div>
                {ev.timestamp && (
                  <div style={{ fontSize: 12, color: '#4B6080' }}>{ev.timestamp}</div>
                )}
                <div style={{ fontSize: 10, color: '#8FA5BD', marginTop: 2 }}>{ev.source}</div>
                {ev.payment_id && (
                  <div className="mono" style={{ fontSize: 10, color: '#0ABFCA', marginTop: 2 }}>{ev.payment_id}</div>
                )}
              </div>
            </div>
          )
        })}
        {events.length === 0 && (
          <div style={{ color: '#8FA5BD', padding: '24px 0' }}>No timeline events found</div>
        )}
      </div>

      <div style={{ marginTop: 16, fontSize: 11, color: '#8FA5BD' }}>
        Sources: orders_etl.order_date / dispatch_date / delivery_date · settlements_etl.settlement_date
      </div>
    </div>
  )
}

// ─── Tab 2: Financial Timeline ────────────────────────────────────────────────

function FinancialsTab({ financials }) {
  var fc = financials.formula_components || {}
  var ib = financials.invoice_breakdown  || {}
  var recon = financials.reconciliation  || {}

  var rows = [
    { label: 'Selling Price (Sale Amount)',    value: fc.sale_amount,        sign: '+', color: '#0DB07A' },
    { label: 'Total Offer Amount',             value: fc.total_offer_amount, sign: '+', color: '#0DB07A' },
    { label: 'My Share (Seller-funded offer)', value: fc.my_share,           sign: fc.my_share < 0 ? '−' : '+', color: fc.my_share < 0 ? '#E8344A' : '#0DB07A' },
    { label: 'Marketplace Fee (settlement)',   value: fc.marketplace_fee,    sign: '−', color: '#E8344A' },
    { label: 'TCS (Tax Collected at Source)',  value: fc.tcs,                sign: '−', color: '#E8344A' },
    { label: 'TDS (Tax Deducted at Source)',   value: fc.tds,                sign: '−', color: '#E8344A' },
    { label: 'GST on Marketplace Fees',        value: fc.gst_on_mp_fees,     sign: '−', color: '#E8344A' },
    { label: 'Refund (Return deduction)',      value: fc.refund,             sign: '−', color: fc.refund !== 0 ? '#E8344A' : '#8FA5BD' },
    null, // divider
    { label: 'Invoice Fee Total (audit)',      value: ib.invoice_fee_total,  sign: '−', color: '#E9930D' },
    { label: 'Invoice GST Total (audit)',      value: ib.invoice_gst_total,  sign: '−', color: '#E9930D' },
    null,
    { label: 'Expected Settlement',            value: recon.expected_settlement, sign: '=', color: '#0ABFCA', bold: true },
    { label: 'Actual Settlement Received',     value: recon.actual_settlement,   sign: '=', color: '#0D1F35', bold: true },
    { label: 'Difference',                     value: recon.difference,          sign: recon.difference > 0 ? '+' : '', color: recon.difference > 2 ? '#E9930D' : recon.difference < -2 ? '#E8344A' : '#0DB07A', bold: true },
  ]

  return (
    <div>
      {/* Product info */}
      {financials.product_title && (
        <div style={{ background: '#F8FAFC', borderRadius: 10, padding: '10px 14px', marginBottom: 16 }}>
          <div style={{ fontWeight: 700, fontSize: 13 }}>{financials.product_title}</div>
          <div style={{ fontSize: 11, color: '#8FA5BD' }}>{financials.sku}</div>
          <div style={{ fontSize: 11, color: '#4B6080', marginTop: 4 }}>
            Order: {financials.order_date || '—'} → Settlement: {financials.settlement_date || '—'}
          </div>
        </div>
      )}

      {/* Component rows */}
      <div style={{ background: '#F8FAFC', borderRadius: 10, overflow: 'hidden', marginBottom: 16 }}>
        {rows.map(function(row, i) {
          if (!row) return (
            <div key={'div' + i} style={{ height: 1, background: '#E2EBF3', margin: '0 16px' }} />
          )
          return (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '10px 16px',
              background: row.bold ? 'rgba(10,191,202,.06)' : 'transparent',
              borderBottom: '1px solid #E2EBF3',
            }}>
              <span style={{ fontSize: 12, color: '#4B6080', fontWeight: row.bold ? 700 : 400 }}>{row.sign} {row.label}</span>
              <span style={{ fontSize: 13, fontWeight: row.bold ? 800 : 600, color: row.color }}>
                {row.value != null ? INR(Math.abs(row.value)) : '—'}
              </span>
            </div>
          )
        })}
      </div>

      {/* Invoice fee lines */}
      {ib.fee_lines && ib.fee_lines.length > 0 && (
        <div>
          <div className="card-title" style={{ marginBottom: 8 }}>Invoice Lines (fees_etl)</div>
          <div style={{ background: '#F8FAFC', borderRadius: 10, overflow: 'hidden' }}>
            {ib.fee_lines.map(function(fl, i) {
              return (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '8px 16px', borderBottom: '1px solid #E2EBF3', fontSize: 12,
                }}>
                  <div>
                    <span style={{ fontWeight: 600 }}>{fl.fee_name}</span>
                    {fl.fee_date && <span style={{ color: '#8FA5BD', marginLeft: 8 }}>{fl.fee_date}</span>}
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ color: '#E8344A', fontWeight: 600 }}>{INR(fl.fee_amount)}</span>
                    {fl.tax_amount ? <span style={{ color: '#E9930D', marginLeft: 6 }}>+{INR(fl.tax_amount)} GST</span> : null}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div style={{ marginTop: 12, fontSize: 11, color: '#8FA5BD' }}>
        Source: order_financials (formula_components) + fees_etl (invoice lines)
      </div>
    </div>
  )
}

// ─── Tab 3: Reconciliation Breakdown ─────────────────────────────────────────

function ReconciliationTab({ financials }) {
  var recon = financials.reconciliation || {}
  var fc = financials.formula_components || {}

  var credits = [
    { label: 'Sale Amount',        value: fc.sale_amount,        note: 'Buyer paid' },
    { label: 'Total Offer Amount', value: fc.total_offer_amount, note: 'Flipkart subsidy' },
  ].filter(function(r) { return r.value != null && r.value !== 0 })

  var debits = [
    { label: 'My Share',         value: fc.my_share,                note: 'Seller-funded discount' },
    { label: 'Invoice Fees',     value: financials.invoice_breakdown?.invoice_fee_total, note: 'Commission + shipping + others' },
    { label: 'Invoice GST',      value: financials.invoice_breakdown?.invoice_gst_total, note: 'GST on fees' },
    { label: 'TCS',              value: fc.tcs,                     note: 'Tax Collected at Source' },
    { label: 'TDS',              value: fc.tds,                     note: 'Tax Deducted at Source' },
    { label: 'GST on MP Fees',   value: fc.gst_on_mp_fees,          note: 'GST on marketplace fees' },
    { label: 'Refund',           value: fc.refund,                  note: 'Return recovery' },
  ].filter(function(r) { return r.value != null && r.value !== 0 })

  var statusColor = RECON_COLOR[recon.status] || '#8FA5BD'
  var statusBg    = RECON_BG[recon.status] || 'rgba(143,165,189,.12)'

  return (
    <div>
      {/* Status banner */}
      <div style={{
        background: statusBg, border: '1.5px solid ' + statusColor,
        borderRadius: 10, padding: '12px 16px', marginBottom: 20,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: 12, color: '#4B6080', marginBottom: 2 }}>Reconciliation Status</div>
          <ReconChip status={recon.status} />
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, color: '#8FA5BD' }}>Difference</div>
          <div style={{ fontWeight: 800, fontSize: 18, color: statusColor }}>
            {recon.difference != null ? (recon.difference >= 0 ? '+' : '') + INR(recon.difference) : '—'}
          </div>
        </div>
      </div>

      {/* Formula layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 12, alignItems: 'start', marginBottom: 20 }}>
        {/* Credits */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#0DB07A', marginBottom: 8 }}>CREDITS</div>
          {credits.length > 0 ? credits.map(function(c, i) {
            return (
              <div key={i} style={{ background: 'rgba(13,176,122,.08)', borderRadius: 8, padding: '8px 12px', marginBottom: 6 }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{c.label}</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: '#0DB07A' }}>+{INR(c.value)}</div>
                <div style={{ fontSize: 10, color: '#8FA5BD' }}>{c.note}</div>
              </div>
            )
          }) : <div style={{ color: '#8FA5BD', fontSize: 12 }}>No credits</div>}
        </div>

        {/* Operator */}
        <div style={{ paddingTop: 28, fontSize: 20, fontWeight: 800, color: '#8FA5BD' }}>−</div>

        {/* Debits */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#E8344A', marginBottom: 8 }}>DEBITS</div>
          {debits.length > 0 ? debits.map(function(d, i) {
            return (
              <div key={i} style={{ background: 'rgba(232,52,74,.06)', borderRadius: 8, padding: '8px 12px', marginBottom: 6 }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{d.label}</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: '#E8344A' }}>−{INR(Math.abs(d.value))}</div>
                <div style={{ fontSize: 10, color: '#8FA5BD' }}>{d.note}</div>
              </div>
            )
          }) : <div style={{ color: '#8FA5BD', fontSize: 12 }}>No debits</div>}
        </div>
      </div>

      {/* Result row */}
      <div style={{ background: '#F1F5F9', borderRadius: 10, padding: '14px 18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>Expected Settlement</span>
          <span style={{ fontSize: 16, fontWeight: 800, color: '#0ABFCA' }}>
            {recon.expected_settlement != null ? INR(recon.expected_settlement) : '—'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>Actual Settlement</span>
          <span style={{ fontSize: 16, fontWeight: 800, color: '#0D1F35' }}>
            {recon.actual_settlement != null ? INR(recon.actual_settlement) : '—'}
          </span>
        </div>
        <div style={{ height: 1, background: '#E2EBF3', margin: '10px 0' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 14, fontWeight: 800 }}>Difference</span>
          <span style={{ fontSize: 18, fontWeight: 900, color: statusColor }}>
            {recon.difference != null ? (recon.difference >= 0 ? '+' : '') + INR(recon.difference) : '—'}
          </span>
        </div>
      </div>

      {/* Formula note */}
      {recon.formula && (
        <div style={{ marginTop: 12, background: '#F8FAFC', borderRadius: 8, padding: '10px 14px' }}>
          <div style={{ fontSize: 10, color: '#8FA5BD', fontFamily: 'monospace', lineHeight: 1.6 }}>
            {recon.formula}
          </div>
        </div>
      )}

      <div style={{ marginTop: 10, fontSize: 11, color: '#8FA5BD' }}>
        Source: order_financials.expected_settlement / settlement_amount / difference
      </div>
    </div>
  )
}

// ─── Tab 4: Source Data ───────────────────────────────────────────────────────

function SourceDataTab({ debugData }) {
  var [expanded, setExpanded] = useState(null)
  var sources = debugData.sources || {}

  var sections = [
    { key: 'orders_etl',      label: 'Orders Report (orders_etl)',       rows: sources.orders_etl      || [] },
    { key: 'fees_etl',        label: 'Commission Report (fees_etl)',      rows: sources.fees_etl        || [] },
    { key: 'settlements_etl', label: 'Settlements Report (settlements_etl)', rows: sources.settlements_etl || [] },
    { key: 'order_financials', label: 'Reconciliation Record (order_financials)', rows: sources.order_financials ? [sources.order_financials] : [] },
  ]

  return (
    <div>
      {/* Traceability summary */}
      <div style={{ background: '#F1F5F9', borderRadius: 10, padding: '12px 16px', marginBottom: 18 }}>
        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Traceability Summary</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 8 }}>
          {[
            { label: 'orders_etl rows',      value: debugData.traceability?.orders_etl_rows },
            { label: 'fees_etl rows',         value: debugData.traceability?.fees_etl_rows },
            { label: 'settlements_etl rows',  value: debugData.traceability?.settlements_etl_rows },
            { label: 'Has reconciled record', value: debugData.traceability?.has_financials ? 'Yes' : 'No' },
          ].map(function(t) {
            return (
              <div key={t.label} style={{ background: '#fff', borderRadius: 8, padding: '8px 12px' }}>
                <div style={{ fontSize: 10, color: '#8FA5BD' }}>{t.label}</div>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{t.value}</div>
              </div>
            )
          })}
        </div>
        <div style={{ fontSize: 10, color: '#8FA5BD', marginTop: 8 }}>
          {debugData.traceability?.deduplication_note}
        </div>
      </div>

      {/* Source sections */}
      {sections.map(function(sec) {
        var isOpen = expanded === sec.key
        var isEmpty = sec.rows.length === 0
        return (
          <div key={sec.key} style={{ marginBottom: 10 }}>
            <button
              onClick={function() { setExpanded(isOpen ? null : sec.key) }}
              style={{
                width: '100%', textAlign: 'left', padding: '10px 14px',
                background: isOpen ? '#E8F4FB' : '#F8FAFC',
                border: '1px solid ' + (isOpen ? '#0ABFCA' : '#E2EBF3'),
                borderRadius: isOpen ? '10px 10px 0 0' : 10,
                cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
              }}
            >
              <span style={{ fontWeight: 700, fontSize: 13 }}>{sec.label}</span>
              <span style={{ color: '#8FA5BD', fontSize: 12 }}>
                {isEmpty ? 'No data' : sec.rows.length + ' row' + (sec.rows.length > 1 ? 's' : '')} {isOpen ? '▲' : '▼'}
              </span>
            </button>
            {isOpen && !isEmpty && (
              <div style={{
                border: '1px solid #0ABFCA', borderTop: 'none',
                borderRadius: '0 0 10px 10px', overflow: 'auto',
                maxHeight: 320,
              }}>
                <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {Object.keys(sec.rows[0]).map(function(col) {
                        return <th key={col} style={{ padding: '6px 10px', background: '#F1F5F9', borderBottom: '1px solid #E2EBF3', textAlign: 'left', fontWeight: 700, whiteSpace: 'nowrap' }}>{col}</th>
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {sec.rows.map(function(row, ri) {
                      return (
                        <tr key={ri} style={{ background: ri % 2 === 0 ? '#fff' : '#F8FAFC' }}>
                          {Object.values(row).map(function(val, ci) {
                            return (
                              <td key={ci} style={{
                                padding: '5px 10px', borderBottom: '1px solid #E2EBF3',
                                fontFamily: typeof val === 'number' ? 'monospace' : 'inherit',
                                color: val === null ? '#CBD5E1' : 'inherit',
                                whiteSpace: 'nowrap',
                              }}>
                                {val === null ? 'null' : String(val)}
                              </td>
                            )
                          })}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )
      })}

      <div style={{ marginTop: 10, fontSize: 11, color: '#8FA5BD' }}>
        Every value above is directly from the uploaded Flipkart report rows. batch_id + raw_id trace to the source file.
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

function PaymentReconciliation() {
  var { data: kpis, loading: kpisLoading } = useApi('/payment-reconciliation/kpis')
  var [selectedPayment, setSelectedPayment] = useState(null)
  var [selectedOrder,   setSelectedOrder]   = useState(null)

  function handlePaymentSelect(p) {
    setSelectedPayment(p)
    setSelectedOrder(null)
  }

  function handleBack() {
    setSelectedPayment(null)
    setSelectedOrder(null)
  }

  function handleOrderSelect(orderItemId) {
    setSelectedOrder(orderItemId)
  }

  function handleCloseDrawer() {
    setSelectedOrder(null)
  }

  return (
    <div className="page page-anim">
      {/* Page title */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 22, fontWeight: 800, color: '#0D1F35' }}>Payment Reconciliation</div>
        <div style={{ fontSize: 13, color: '#8FA5BD', marginTop: 3 }}>
          Track and verify marketplace settlements
        </div>
      </div>

      {/* KPI cards */}
      {kpisLoading
        ? <div style={{ marginBottom: 20 }}><Spin /></div>
        : <KpiCards kpis={kpis} />
      }

      {/* Screen 1 or 2 */}
      {!selectedPayment
        ? <PaymentList onSelect={handlePaymentSelect} />
        : <PaymentDetail
            payment={selectedPayment}
            onBack={handleBack}
            onOrderSelect={handleOrderSelect}
          />
      }

      {/* Order Investigation Drawer (Screen 3) */}
      {selectedOrder && (
        <OrderDrawer
          orderItemId={selectedOrder}
          onClose={handleCloseDrawer}
        />
      )}
    </div>
  )
}

export default PaymentReconciliation
