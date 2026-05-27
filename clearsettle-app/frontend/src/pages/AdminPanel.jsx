import React, { useState, useEffect, useCallback } from 'react'
import api from '../utils/api'

// ── Formatters ─────────────────────────────────────────────────────────────────

function inr(n, compact) {
  var num = Number(n) || 0
  if (compact) {
    if (num >= 1e7) return '₹' + (num / 1e7).toFixed(1) + ' Cr'
    if (num >= 1e5) return '₹' + (num / 1e5).toFixed(1) + ' L'
    if (num >= 1e3) return '₹' + (num / 1e3).toFixed(1) + 'K'
  }
  return '₹' + num.toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

function fmtRelative(iso) {
  if (!iso) return '—'
  var diff = (Date.now() - new Date(iso)) / 1000
  if (diff < 60) return 'Just now'
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago'
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago'
  if (diff < 2592000) return Math.floor(diff / 86400) + 'd ago'
  return fmtDate(iso)
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: 'rgba(255,255,255,.03)',
      border: '1px solid rgba(255,255,255,.08)',
      borderRadius: 12, padding: '18px 20px',
      borderTop: '3px solid ' + (color || '#0ABFCA'),
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 800, color: '#E2EBF3', marginBottom: 4 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: '#4B6080' }}>{sub}</div>}
    </div>
  )
}

function Badge({ text, color }) {
  var colors = {
    tl: { bg: 'rgba(10,191,202,.15)', fg: '#0ABFCA' },
    am: { bg: 'rgba(233,147,13,.15)', fg: '#E9930D' },
    rd: { bg: 'rgba(232,52,74,.15)', fg: '#E8344A' },
    gr: { bg: 'rgba(16,185,129,.15)', fg: '#10B981' },
  }
  var c = colors[color || 'tl']
  return (
    <span style={{
      background: c.bg, color: c.fg,
      borderRadius: 8, padding: '2px 8px',
      fontSize: 11, fontWeight: 700,
    }}>
      {text}
    </span>
  )
}

function PlatformChip({ name }) {
  var icons = { flipkart: '🛒', amazon: '📦', meesho: '🧵', myntra: '👗', ajio: '🎽', nykaa: '💄', other: '➕' }
  return (
    <span style={{
      background: 'rgba(255,255,255,.06)', borderRadius: 6,
      padding: '2px 6px', fontSize: 11, color: '#8FA5BD', marginRight: 4,
    }}>
      {icons[name] || '🏪'} {name}
    </span>
  )
}

function Spinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '48px 0' }}>
      <div style={{
        width: 36, height: 36, borderRadius: '50%',
        border: '3px solid rgba(10,191,202,.2)',
        borderTopColor: '#0ABFCA',
        animation: 'spin 0.8s linear infinite',
      }} />
    </div>
  )
}

// ── Seller detail modal ────────────────────────────────────────────────────────

function SellerModal({ sellerId, onClose }) {
  var [data, setData] = useState(null)
  var [loading, setLoading] = useState(true)

  useEffect(function() {
    api.get('/admin/sellers/' + sellerId)
      .then(function(res) { setData(res.data) })
      .finally(function() { setLoading(false) })
  }, [sellerId])

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,.65)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 24,
    }} onClick={function(e) { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        background: '#0D1F35', border: '1px solid rgba(255,255,255,.1)',
        borderRadius: 16, width: '100%', maxWidth: 680,
        maxHeight: '85vh', overflowY: 'auto', padding: 28,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#E2EBF3' }}>Seller Details</div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#8FA5BD', fontSize: 20, cursor: 'pointer' }}>✕</button>
        </div>

        {loading && <Spinner />}

        {!loading && data && (
          <div>
            {/* Account */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 10 }}>Account</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {[
                  ['Name', data.name],
                  ['Email', data.email],
                  ['Phone', data.phone || '—'],
                  ['Role', data.role],
                  ['Status', data.is_active ? 'Active' : 'Inactive'],
                  ['Joined', fmtDate(data.created_at)],
                ].map(function([label, val]) {
                  return (
                    <div key={label} style={{ background: 'rgba(255,255,255,.04)', borderRadius: 8, padding: '8px 12px' }}>
                      <div style={{ fontSize: 10, color: '#4B6080', fontWeight: 600 }}>{label}</div>
                      <div style={{ fontSize: 13, color: '#E2EBF3', marginTop: 2 }}>{val}</div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Company */}
            {data.company && data.company.id && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 10 }}>Business</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  {[
                    ['Company', data.company.name],
                    ['GSTIN', data.company.gstin || '—'],
                    ['State', data.company.state || '—'],
                    ['City', data.company.city || '—'],
                    ['Industry', data.company.industry || '—'],
                    ['GMV Range', data.company.monthly_gmv_range || '—'],
                  ].map(function([label, val]) {
                    return (
                      <div key={label} style={{ background: 'rgba(255,255,255,.04)', borderRadius: 8, padding: '8px 12px' }}>
                        <div style={{ fontSize: 10, color: '#4B6080', fontWeight: 600 }}>{label}</div>
                        <div style={{ fontSize: 13, color: '#E2EBF3', marginTop: 2 }}>{val}</div>
                      </div>
                    )
                  })}
                </div>
                {data.company.active_platforms && data.company.active_platforms.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 10, color: '#4B6080', fontWeight: 600, marginBottom: 6 }}>PLATFORMS</div>
                    <div>{data.company.active_platforms.map(function(p) { return <PlatformChip key={p} name={p} /> })}</div>
                  </div>
                )}
              </div>
            )}

            {/* Aggregates */}
            {data.aggregates && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 10 }}>Analytics Summary</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                  {[
                    ['Total GMV', inr(data.aggregates.total_gmv, true)],
                    ['Net Earnings', inr(data.aggregates.total_earnings, true)],
                    ['Total Orders', data.aggregates.total_orders?.toLocaleString()],
                    ['Amount Settled', inr(data.aggregates.amount_settled, true)],
                    ['Amount Pending', inr(data.aggregates.amount_pending, true)],
                  ].map(function([label, val]) {
                    return (
                      <div key={label} style={{ background: 'rgba(10,191,202,.06)', borderRadius: 8, padding: '10px 12px' }}>
                        <div style={{ fontSize: 10, color: '#4B6080', fontWeight: 600 }}>{label}</div>
                        <div style={{ fontSize: 15, color: '#0ABFCA', fontWeight: 700, marginTop: 2 }}>{val || '0'}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Uploads */}
            {data.flipkart_uploads && data.flipkart_uploads.length > 0 && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#4B6080', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 10 }}>
                  Recent Uploads ({data.flipkart_uploads.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {data.flipkart_uploads.map(function(u) {
                    return (
                      <div key={u.id} style={{
                        background: 'rgba(255,255,255,.04)', borderRadius: 8,
                        padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      }}>
                        <div>
                          <div style={{ fontSize: 12, color: '#E2EBF3', fontWeight: 600 }}>{u.original_name}</div>
                          <div style={{ fontSize: 11, color: '#4B6080' }}>{u.report_period || '—'} · {u.row_count_orders || 0} orders</div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                          <Badge
                            text={u.status}
                            color={u.status === 'done' ? 'gr' : u.status === 'failed' ? 'rd' : 'am'}
                          />
                          <div style={{ fontSize: 10, color: '#4B6080' }}>{fmtRelative(u.uploaded_at)}</div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

function AdminPanel() {
  var [stats, setStats] = useState(null)
  var [sellers, setSellers] = useState([])
  var [total, setTotal] = useState(0)
  var [pages, setPages] = useState(1)
  var [page, setPage] = useState(1)
  var [search, setSearch] = useState('')
  var [searchInput, setSearchInput] = useState('')
  var [platformFilter, setPlatformFilter] = useState('')
  var [loadingStats, setLoadingStats] = useState(true)
  var [loadingSellers, setLoadingSellers] = useState(true)
  var [selectedSeller, setSelectedSeller] = useState(null)
  var [activeTab, setActiveTab] = useState('sellers')

  useEffect(function() {
    api.get('/admin/stats')
      .then(function(res) { setStats(res.data) })
      .finally(function() { setLoadingStats(false) })
  }, [])

  var fetchSellers = useCallback(function() {
    setLoadingSellers(true)
    var params = new URLSearchParams({ page: page, limit: 20 })
    if (search) params.set('search', search)
    if (platformFilter) params.set('platform', platformFilter)
    api.get('/admin/sellers?' + params.toString())
      .then(function(res) {
        setSellers(res.data.sellers || [])
        setTotal(res.data.total || 0)
        setPages(res.data.pages || 1)
      })
      .finally(function() { setLoadingSellers(false) })
  }, [page, search, platformFilter])

  useEffect(function() { fetchSellers() }, [fetchSellers])

  function handleSearch(e) {
    e.preventDefault()
    setPage(1)
    setSearch(searchInput)
  }

  var navStyle = function(tab) {
    return {
      padding: '8px 18px', borderRadius: 8,
      background: activeTab === tab ? 'rgba(10,191,202,.15)' : 'transparent',
      border: activeTab === tab ? '1px solid rgba(10,191,202,.3)' : '1px solid transparent',
      color: activeTab === tab ? '#0ABFCA' : '#8FA5BD',
      fontSize: 13, fontWeight: 600, cursor: 'pointer',
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F1F5F9', padding: '28px 32px' }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#0D1F35' }}>Admin Operations</div>
          <div style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>
            ClearSettle platform overview — all sellers and uploads
          </div>
        </div>
        <div style={{
          background: 'rgba(10,191,202,.1)', border: '1px solid rgba(10,191,202,.3)',
          borderRadius: 8, padding: '6px 12px',
          fontSize: 11, fontWeight: 700, color: '#0ABFCA',
        }}>
          ADMIN VIEW
        </div>
      </div>

      {/* Stats row */}
      {loadingStats ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 14, marginBottom: 28 }}>
          {[1,2,3,4,5].map(function(i) {
            return <div key={i} style={{ height: 90, background: '#E5E7EB', borderRadius: 12, animation: 'pulse 1.5s infinite' }} />
          })}
        </div>
      ) : stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 14, marginBottom: 28 }}>
          <StatCard label="Total Sellers" value={stats.total_sellers?.toLocaleString()} sub="All registered" color="#0ABFCA" />
          <StatCard label="New (30 days)" value={stats.active_sellers_30d?.toLocaleString()} sub="Recent signups" color="#10B981" />
          <StatCard label="Total Uploads" value={stats.total_report_uploads?.toLocaleString()} sub="Across all sellers" color="#8B5CF6" />
          <StatCard
            label="GMV Processed"
            value={inr(stats.total_gmv_processed, true)}
            sub="Total gross sales"
            color="#F59E0B"
          />
          <StatCard
            label="Potential Leakage"
            value={inr(stats.total_money_leak_detected, true)}
            sub="Estimated anomalies"
            color="#E8344A"
          />
        </div>
      )}

      {/* Platform distribution */}
      {stats && stats.platform_distribution && stats.platform_distribution.length > 0 && (
        <div style={{
          background: '#fff', border: '1px solid #E5E7EB',
          borderRadius: 12, padding: '16px 20px', marginBottom: 24,
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 12 }}>
            Platform Distribution
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {stats.platform_distribution.map(function(p) {
              return (
                <div key={p.platform} style={{
                  background: '#F9FAFB', border: '1px solid #E5E7EB',
                  borderRadius: 8, padding: '6px 12px',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <PlatformChip name={p.platform} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#0D1F35' }}>{p.seller_count} sellers</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button style={navStyle('sellers')} onClick={function() { setActiveTab('sellers') }}>
          Sellers ({total})
        </button>
      </div>

      {/* Sellers table */}
      <div style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 12, overflow: 'hidden' }}>
        {/* Toolbar */}
        <div style={{
          padding: '14px 18px', borderBottom: '1px solid #F3F4F6',
          display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap',
        }}>
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, flex: 1 }}>
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchInput}
              onChange={function(e) { setSearchInput(e.target.value) }}
              style={{
                flex: 1, padding: '8px 12px', borderRadius: 8,
                border: '1px solid #E5E7EB', fontSize: 13, outline: 'none',
                minWidth: 200,
              }}
            />
            <button type="submit" style={{
              padding: '8px 16px', borderRadius: 8,
              background: '#0D1F35', color: '#fff',
              fontSize: 13, fontWeight: 600, cursor: 'pointer', border: 'none',
            }}>Search</button>
            {search && (
              <button type="button" onClick={function() { setSearchInput(''); setSearch(''); setPage(1) }} style={{
                padding: '8px 12px', borderRadius: 8,
                background: '#F3F4F6', color: '#6B7280',
                fontSize: 13, cursor: 'pointer', border: 'none',
              }}>Clear</button>
            )}
          </form>
          <select
            value={platformFilter}
            onChange={function(e) { setPlatformFilter(e.target.value); setPage(1) }}
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #E5E7EB', fontSize: 13 }}
          >
            <option value="">All Platforms</option>
            {['flipkart','amazon','meesho','myntra','ajio','nykaa','snapdeal','jiomart','indiamart'].map(function(p) {
              return <option key={p} value={p}>{p}</option>
            })}
          </select>
        </div>

        {/* Table */}
        {loadingSellers ? <Spinner /> : sellers.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 24px', color: '#9CA3AF' }}>
            No sellers found
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#F9FAFB' }}>
                  {['Seller','Company / GSTIN','State','Platforms','Uploads','Last Upload','Joined',''].map(function(h) {
                    return (
                      <th key={h} style={{
                        padding: '10px 16px', textAlign: 'left',
                        fontSize: 11, fontWeight: 700, color: '#6B7280',
                        textTransform: 'uppercase', letterSpacing: '.05em',
                        borderBottom: '1px solid #F3F4F6', whiteSpace: 'nowrap',
                      }}>{h}</th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {sellers.map(function(s, i) {
                  return (
                    <tr key={s.id} style={{ background: i % 2 === 0 ? '#fff' : '#FAFAFA', borderBottom: '1px solid #F3F4F6' }}>
                      <td style={{ padding: '12px 16px', whiteSpace: 'nowrap' }}>
                        <div style={{ fontWeight: 600, color: '#0D1F35' }}>{s.name}</div>
                        <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{s.email}</div>
                        {s.phone && <div style={{ fontSize: 11, color: '#9CA3AF' }}>{s.phone}</div>}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600, color: '#0D1F35', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {s.company.name || '—'}
                        </div>
                        <div style={{ fontSize: 11, color: '#6B7280', fontFamily: 'monospace' }}>
                          {s.company.gstin || '—'}
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', color: '#6B7280', whiteSpace: 'nowrap' }}>
                        {s.company.state || '—'}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                          {(s.company.active_platforms || []).slice(0, 3).map(function(p) {
                            return <PlatformChip key={p} name={p} />
                          })}
                          {(s.company.active_platforms || []).length > 3 && (
                            <span style={{ fontSize: 11, color: '#9CA3AF' }}>+{s.company.active_platforms.length - 3}</span>
                          )}
                          {!(s.company.active_platforms || []).length && '—'}
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                        <span style={{
                          background: s.upload_count > 0 ? 'rgba(16,185,129,.1)' : '#F3F4F6',
                          color: s.upload_count > 0 ? '#10B981' : '#9CA3AF',
                          borderRadius: 8, padding: '2px 10px', fontWeight: 700, fontSize: 13,
                        }}>
                          {s.upload_count}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', color: '#6B7280', whiteSpace: 'nowrap', fontSize: 12 }}>
                        {fmtRelative(s.last_upload_at)}
                      </td>
                      <td style={{ padding: '12px 16px', color: '#6B7280', whiteSpace: 'nowrap', fontSize: 12 }}>
                        {fmtDate(s.created_at)}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <button
                          onClick={function() { setSelectedSeller(s.id) }}
                          style={{
                            padding: '5px 12px', borderRadius: 6,
                            background: '#F0F9FF', border: '1px solid #BAE6FD',
                            color: '#0369A1', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                          }}
                        >
                          View →
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div style={{
            padding: '12px 18px', borderTop: '1px solid #F3F4F6',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div style={{ fontSize: 12, color: '#6B7280' }}>
              Page {page} of {pages} · {total} sellers
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={function() { setPage(function(p) { return Math.max(1, p - 1) }) }}
                disabled={page === 1}
                style={{
                  padding: '6px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                  background: '#fff', fontSize: 12, cursor: page === 1 ? 'not-allowed' : 'pointer',
                  color: page === 1 ? '#D1D5DB' : '#374151',
                }}
              >← Prev</button>
              <button
                onClick={function() { setPage(function(p) { return Math.min(pages, p + 1) }) }}
                disabled={page === pages}
                style={{
                  padding: '6px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                  background: '#fff', fontSize: 12, cursor: page === pages ? 'not-allowed' : 'pointer',
                  color: page === pages ? '#D1D5DB' : '#374151',
                }}
              >Next →</button>
            </div>
          </div>
        )}
      </div>

      {/* Seller detail modal */}
      {selectedSeller && (
        <SellerModal
          sellerId={selectedSeller}
          onClose={function() { setSelectedSeller(null) }}
        />
      )}

      {/* Legal disclaimer */}
      <div style={{ marginTop: 24, fontSize: 11, color: '#9CA3AF', lineHeight: 1.6 }}>
        Admin view — all data is confidential. GMV and leakage figures are derived from uploaded reports
        and represent estimated anomalies only. Verify before actioning recovery.
      </div>
    </div>
  )
}

export default AdminPanel
