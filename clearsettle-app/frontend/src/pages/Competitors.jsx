import React, { useState } from 'react'
import useApi from '../hooks/useApi'
import { Chip } from '../components/ui/Chip'

var FEATURES = [
  { key: 'settleRecon', label: 'Settlement Recon' },
  { key: 'commAudit', label: 'Commission Audit' },
  { key: 'bankMatch', label: 'Bank Matching' },
  { key: 'disputeEngine', label: 'Dispute Engine' },
  { key: 'gstModule', label: 'GST/TCS' },
  { key: 'invSync', label: 'Inventory' },
  { key: 'profitAnalytics', label: 'P&L Analytics' },
  { key: 'cashForecast', label: 'Cash Flow' },
]

var CS_ROW = {
  name: 'ClearSettle', type: 'You', origin: 'Tirupur', founded: 2026,
  target: 'Tirupur textile sellers — all 8 Indian marketplaces',
  platforms: 'Amazon, Flipkart, Meesho, Myntra, Nykaa, AJIO, Snapdeal, JioMart',
  pricing: '₹1,499/mo or Success Fee',
  tirupurFit: 'Highest',
  settleRecon: true, commAudit: true, bankMatch: true, disputeEngine: true,
  gstModule: true, invSync: true, profitAnalytics: true, cashForecast: true,
  gap: '—',
}

var TIRUPUR_COLORS = {
  Highest: 'gn', High: 'gn', Medium: 'am', Low: 'rd', None: 'gr',
}

function Competitors() {
  var { data, loading } = useApi('/competitors/')
  var [view, setView] = useState('matrix')

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary
  var allRows = [CS_ROW, ...data.items]

  return (
    <div className="page page-anim">
      {/* Banner */}
      <div className="ab ok">
        <span>🏆</span>
        <div className="ab-body">
          <div className="ab-title">ClearSettle has the most complete feature set in the category</div>
          <div className="ab-sub">
            No competitor offers all 4 key moats: Dispute Engine + Bank Matching + Cash Forecast + Tirupur-specific coverage
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-row cols-4">
        {[
          { label: 'Direct Competitors', val: s.direct, stripe: 'rd' },
          { label: 'Adjacent Platforms', val: s.adjacent, stripe: 'am' },
          { label: 'With Dispute Engine', val: s.with_dispute_engine, stripe: 'tl' },
          { label: 'With Cash Forecast', val: s.with_cash_forecast + ' — ClearSettle only!', stripe: 'rd' },
        ].map(function(k) {
          return (
            <div key={k.label} className="stat-card">
              <div className={'sc-stripe ' + k.stripe} />
              <div className="sc-label" style={{ marginTop: 8 }}>{k.label}</div>
              <div className="sc-val" style={{ fontSize: typeof k.val === 'string' ? 14 : 24 }}>{k.val}</div>
            </div>
          )
        })}
      </div>

      {/* View toggle */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div className="toggle-wrap">
          {['matrix', 'cards'].map(function(v) {
            return (
              <button
                key={v}
                className={'toggle-btn' + (view === v ? ' active' : '')}
                onClick={function() { setView(v) }}
              >
                {v === 'matrix' ? '📊 Matrix' : '🃏 Cards'}
              </button>
            )
          })}
        </div>
      </div>

      {/* Matrix View */}
      {view === 'matrix' && (
        <div className="tw" style={{ marginBottom: 24 }}>
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Type</th>
                <th>Tirupur Fit</th>
                <th>Pricing</th>
                {FEATURES.map(function(f) { return <th key={f.key} style={{ textAlign: 'center' }}>{f.label}</th> })}
                <th>Key Gap</th>
              </tr>
            </thead>
            <tbody>
              {allRows.map(function(row) {
                var isCS = row.type === 'You'
                return (
                  <tr key={row.name} style={{ background: isCS ? 'rgba(233,147,13,.06)' : 'transparent' }}>
                    <td style={{ fontWeight: 700 }}>
                      {isCS && <span style={{ marginRight: 6 }}>⭐</span>}
                      {row.name}
                    </td>
                    <td>
                      <Chip color={isCS ? 'gn' : row.type === 'Direct' ? 'rd' : 'am'}>
                        {row.type}
                      </Chip>
                    </td>
                    <td>
                      <Chip color={TIRUPUR_COLORS[row.tirupurFit] || 'gr'}>
                        {row.tirupurFit}
                      </Chip>
                    </td>
                    <td style={{ fontSize: 12, color: '#4B6080' }}>{row.pricing}</td>
                    {FEATURES.map(function(f) {
                      return (
                        <td key={f.key} style={{ textAlign: 'center', fontSize: 16 }}>
                          {row[f.key] ? '✅' : <span style={{ color: '#E2EBF3' }}>—</span>}
                        </td>
                      )
                    })}
                    <td style={{ fontSize: 12, color: '#4B6080', maxWidth: 180 }}>{row.gap}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Cards View */}
      {view === 'cards' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16, marginBottom: 24 }}>
          {allRows.map(function(row) {
            var isCS = row.type === 'You'
            return (
              <div key={row.name} className="card" style={{
                padding: '18px 20px',
                border: isCS ? '1.5px solid #0ABFCA' : undefined,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ fontWeight: 800, fontSize: 15 }}>
                    {isCS && '⭐ '}{row.name}
                  </div>
                  <Chip color={isCS ? 'gn' : row.type === 'Direct' ? 'rd' : 'am'}>
                    {row.type}
                  </Chip>
                </div>
                <div style={{ marginBottom: 6 }}>
                  <Chip color={TIRUPUR_COLORS[row.tirupurFit] || 'gr'}>{row.tirupurFit} Fit</Chip>
                </div>
                <div style={{ fontSize: 12, color: '#4B6080', marginBottom: 4 }}>{row.target}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#0ABFCA', marginBottom: 12 }}>{row.pricing}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {FEATURES.map(function(f) {
                    return (
                      <span key={f.key} style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 6,
                        background: row[f.key] ? 'rgba(13,176,122,.1)' : '#F1F5F9',
                        color: row[f.key] ? '#065F46' : '#8FA5BD',
                      }}>
                        {row[f.key] ? '✓ ' : '✗ '}{f.label}
                      </span>
                    )
                  })}
                </div>
                {row.gap && row.gap !== '—' && (
                  <div style={{ marginTop: 10, fontSize: 12, color: '#4B6080', borderTop: '1px solid #E2EBF3', paddingTop: 10 }}>
                    🎯 {row.gap}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Bottom insights */}
      <div className="three-col">
        {[
          {
            icon: '🏆',
            title: "ClearSettle's Unique Moats",
            bullets: [
              'Only platform with built-in Legal Notice automation',
              'Tirupur-specific commission rate database',
              'Cash flow forecast for textile seasonal patterns',
              'SPF coverage auto-detection for Meesho returns',
            ],
          },
          {
            icon: '👁️',
            title: 'Direct Competitor Watch',
            bullets: [
              'SaySeller (Amazon-only) — growing fast, no multi-platform',
              'eVanik AI — widest SME reach, no dispute engine',
              'ReconPe — has bank match but missing GST module',
              'SellerApp — ads-focused, weak reconciliation depth',
            ],
          },
          {
            icon: '🎯',
            title: 'GTM Blind Spots (Open Territory)',
            bullets: [
              'No competitor targets Tirupur textile cluster specifically',
              'Cash flow forecast is uncontested whitespace',
              'Legal notice automation has zero competition',
              'SPF coverage detection not offered anywhere else',
            ],
          },
        ].map(function(card) {
          return (
            <div key={card.title} className="card" style={{ padding: '18px 20px' }}>
              <div style={{ fontSize: 20, marginBottom: 8 }}>{card.icon}</div>
              <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 12 }}>{card.title}</div>
              {card.bullets.map(function(b, i) {
                return (
                  <div key={i} style={{
                    fontSize: 12, color: '#4B6080', lineHeight: 1.5,
                    paddingBottom: 8, marginBottom: 8,
                    borderBottom: i < card.bullets.length - 1 ? '1px solid #E2EBF3' : 'none',
                  }}>
                    · {b}
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default Competitors
