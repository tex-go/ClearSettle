import React, { useState, useEffect } from 'react'
import useApi from '../hooks/useApi'
import { INR } from '../utils/format'
import api from '../utils/api'

var VERDICT_STYLE = {
  'AUTO-DISPUTE': { bg: 'rgba(13,176,122,.12)', color: '#065F46' },
  'GST RECOVERY': { bg: 'rgba(37,99,235,.12)', color: '#1E40AF' },
  'INVESTIGATE': { bg: 'rgba(233,147,13,.12)', color: '#7A4E09' },
  'LISTING ALERT': { bg: 'rgba(10,191,202,.12)', color: '#088F99' },
}

function DisputeEngine() {
  var { data, loading } = useApi('/dispute-engine/rules')
  var [expanded, setExpanded] = useState(null)
  var [calcParams, setCalcParams] = useState({ gmv: 5000000, years: 1, platform: 'multi', model: 's15' })
  var [calcResult, setCalcResult] = useState(null)

  useEffect(function() {
    var params = new URLSearchParams({
      gmv: calcParams.gmv,
      years: calcParams.years,
      platform: calcParams.platform,
      model: calcParams.model,
    })
    api.get('/dispute-engine/calculator?' + params.toString()).then(function(res) {
      setCalcResult(res.data)
    })
  }, [calcParams.gmv, calcParams.years, calcParams.platform, calcParams.model])

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  function toggleExpand(id) {
    setExpanded(expanded === id ? null : id)
  }

  return (
    <div className="page page-anim">
      {/* Stats */}
      <div className="stats-row cols-2">
        {[
          { label: 'Rules Active', val: data.items.length, stripe: 'tl' },
          { label: 'Auto-Raise Rules', val: data.auto_raise_count, stripe: 'gn' },
        ].map(function(k) {
          return (
            <div key={k.label} className="stat-card">
              <div className={'sc-stripe ' + k.stripe} />
              <div className="sc-label" style={{ marginTop: 8 }}>{k.label}</div>
              <div className="sc-val" style={{ color: k.stripe === 'rd' ? '#E8344A' : undefined }}>{k.val}</div>
            </div>
          )
        })}
      </div>

      {/* Info banner */}
      <div className="ab inf">
        <span>🤖</span>
        <div className="ab-body">
          <div className="ab-title">How the Dispute Rule Engine works</div>
          <div className="ab-sub">
            Every settlement is scanned against 8 rules. Auto-raise rules file disputes instantly. Manual rules flag items for review.
            All evidence is auto-collected and structured for platform dispute portals.
          </div>
        </div>
      </div>

      {/* Rules accordion */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
        {data.items.map(function(rule) {
          var isOpen = expanded === rule.id
          var verdictStyle = VERDICT_STYLE[rule.verdict] || { bg: '#F1F5F9', color: '#4B6080' }
          return (
            <div key={rule.id} className="card" style={{ overflow: 'hidden' }}>
              {/* Collapsed header */}
              <div
                onClick={function() { toggleExpand(rule.id) }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '14px 20px', cursor: 'pointer',
                  borderBottom: isOpen ? '1px solid #E2EBF3' : 'none',
                }}
              >
                <div style={{
                  width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                  background: rule.color + '22', color: rule.color,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 800,
                }}>
                  {rule.id}
                </div>
                <div style={{ flex: 1, fontWeight: 700, fontSize: 14 }}>{rule.title}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{
                    padding: '3px 10px', borderRadius: 20,
                    fontSize: 11, fontWeight: 700,
                    background: verdictStyle.bg, color: verdictStyle.color,
                  }}>
                    {rule.verdict}
                  </span>
                  {rule.auto && (
                    <span className="cs-chip cs-chip-gn" style={{ fontSize: 10 }}>AUTO</span>
                  )}
                  <span style={{
                    fontSize: 16, color: '#8FA5BD',
                    transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform .2s',
                    display: 'inline-block',
                  }}>
                    ▼
                  </span>
                </div>
              </div>

              {/* Expanded content */}
              {isOpen && (
                <div style={{ padding: '18px 20px', animation: 'slideDown .2s ease both' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 14 }}>
                    {[
                      { k: 'Rule Condition', v: rule.logic, mono: true, dark: true },
                      { k: 'Time Window', v: rule.window, mono: false, dark: false },
                      { k: 'Immediate Action', v: rule.immediate, mono: false, dark: false },
                      { k: 'Legal Route', v: rule.legal, mono: false, dark: false },
                      { k: 'Avg Recovery', v: rule.recovery, mono: false, dark: false, green: true },
                      { k: 'Success Rate', v: rule.rate, mono: false, dark: false },
                    ].map(function(m) {
                      return (
                        <div key={m.k} style={{
                          padding: '10px 14px', borderRadius: 10,
                          background: m.dark ? '#0D1F35' : '#F1F5F9',
                        }}>
                          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: m.dark ? '#4B6080' : '#8FA5BD', marginBottom: 6 }}>
                            {m.k}
                          </div>
                          <div style={{
                            fontSize: 12,
                            fontFamily: m.mono ? 'JetBrains Mono, monospace' : 'inherit',
                            color: m.dark ? '#0ABFCA' : m.green ? '#0DB07A' : '#0D1F35',
                            fontWeight: m.green ? 700 : 400,
                          }}>
                            {m.v}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#8FA5BD', marginBottom: 8 }}>EVIDENCE REQUIRED</div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {rule.evidence.map(function(ev) {
                        return (
                          <span key={ev} className="cs-chip cs-chip-gr">{ev}</span>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Recovery Calculator */}
      <div className="card" style={{ border: '1.5px solid #0ABFCA' }}>
        <div className="card-hd">
          <div>
            <div className="card-title">💰 Recovery Calculator</div>
            <div className="card-sub">Estimate your recoverable amount based on GMV and platform</div>
          </div>
        </div>
        <div className="card-bd">
          <div className="input-grid-4">
            <div className="fg">
              <label>Annual GMV (₹)</label>
              <input
                type="number"
                value={calcParams.gmv}
                onChange={function(e) { setCalcParams({ ...calcParams, gmv: Number(e.target.value) }) }}
              />
            </div>
            <div className="fg">
              <label>Years of Data</label>
              <select value={calcParams.years} onChange={function(e) { setCalcParams({ ...calcParams, years: Number(e.target.value) }) }}>
                {[1, 2, 3].map(function(y) { return <option key={y} value={y}>{y} Year{y > 1 ? 's' : ''}</option> })}
              </select>
            </div>
            <div className="fg">
              <label>Primary Platform</label>
              <select value={calcParams.platform} onChange={function(e) { setCalcParams({ ...calcParams, platform: e.target.value }) }}>
                {[
                  { val: 'amazon', label: 'Amazon' },
                  { val: 'flipkart', label: 'Flipkart' },
                  { val: 'meesho', label: 'Meesho' },
                  { val: 'multi', label: 'Multi-Platform' },
                ].map(function(o) { return <option key={o.val} value={o.val}>{o.label}</option> })}
              </select>
            </div>
            <div className="fg">
              <label>Fee Model</label>
              <select value={calcParams.model} onChange={function(e) { setCalcParams({ ...calcParams, model: e.target.value }) }}>
                {[
                  { val: 's15', label: 'Success Fee 15%' },
                  { val: 's20', label: 'Success Fee 20%' },
                  { val: 's25', label: 'Success Fee 25%' },
                  { val: 'saas', label: 'SaaS ₹1,499/mo' },
                ].map(function(o) { return <option key={o.val} value={o.val}>{o.label}</option> })}
              </select>
            </div>
          </div>

          {calcResult && (
            <div style={{
              background: '#0D1F35', borderRadius: 14,
              padding: '20px 24px',
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
            }}>
              {[
                { label: 'Total GMV Analysed', val: INR(calcResult.total_gmv), color: '#E2EBF3' },
                { label: 'Raw Overcharges Found', val: INR(calcResult.raw_overcharge), color: '#F87171' },
                { label: '→ Platform dispute window', val: INR(calcResult.platform_dispute), color: '#FCD34D' },
                { label: '→ Legal notice route (2yr CPA)', val: INR(calcResult.legal_route), color: '#FCD34D' },
                { label: 'TCS/GST Unclaimed', val: INR(calcResult.gst_recovery), color: '#FCD34D' },
                null,
                { label: 'Total Recoverable for Vendor', val: INR(calcResult.total_recoverable), color: '#34D399', large: true },
                { label: 'ClearSettle Earnings', val: INR(calcResult.clearsettle_earnings), color: '#0ABFCA', large: true },
              ].map(function(row, i) {
                if (!row) return <div key={i} />
                return (
                  <div key={i}>
                    <div style={{ fontSize: 11, color: '#4B6080', marginBottom: 4 }}>{row.label}</div>
                    <div style={{
                      fontSize: row.large ? 22 : 16, fontWeight: row.large ? 800 : 700,
                      color: row.color,
                      fontFamily: 'JetBrains Mono, monospace',
                    }}>
                      {row.val}
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

export default DisputeEngine
