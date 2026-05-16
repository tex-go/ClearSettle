import React from 'react'
import useApi from '../hooks/useApi'
import useUIStore from '../store/uiStore'
import api from '../utils/api'

function Reports() {
  var { data, loading } = useApi('/reports/')
  var addToast = useUIStore(function(s) { return s.addToast })

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  function handleGenerate(reportId, format) {
    addToast('Generating ' + format + ' report...', 'info', 'This may take 30 seconds')
    api.post('/reports/generate/' + reportId + '?format=' + format).then(function() {
      setTimeout(function() {
        addToast('Report ready!', 'success', 'Click to download ' + format)
      }, 2000)
    })
  }

  var formatColors = { PDF: '#E8344A', Excel: '#0DB07A', CSV: '#2563EB', ZIP: '#7B52E8' }

  return (
    <div className="page page-anim">
      {/* Header */}
      <div className="page-hd">
        <div>
          <div className="page-title">Report Centre</div>
          <div className="page-sub">Generate and download all reconciliation reports</div>
        </div>
        <button className="btn btn-p" onClick={function() { addToast('Preparing all reports...', 'info') }}>
          ⬇ Download All
        </button>
      </div>

      {/* Reports grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        {data.items.map(function(r) {
          return (
            <div key={r.id} className="card" style={{ padding: '20px 22px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 14 }}>
                <span style={{ fontSize: 28, flexShrink: 0 }}>{r.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 4 }}>{r.title}</div>
                  <div style={{ fontSize: 12, color: '#4B6080', lineHeight: 1.5 }}>{r.desc}</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                {r.formats.map(function(fmt) {
                  return (
                    <button
                      key={fmt}
                      className="btn btn-s btn-sm"
                      onClick={function() { handleGenerate(r.id, fmt) }}
                      style={{ borderColor: formatColors[fmt] + '44', color: formatColors[fmt] }}
                    >
                      {fmt}
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      {/* Scheduled reports */}
      <div className="card" style={{ padding: '28px', textAlign: 'center' }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>📅</div>
        <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 6 }}>Scheduled Reports</div>
        <div style={{ fontSize: 13, color: '#4B6080', marginBottom: 20, maxWidth: 400, margin: '0 auto 20px' }}>
          Automatically generate and email reports on a schedule. Set up weekly settlement summaries, monthly GST packs, and more.
        </div>
        <button className="btn btn-p" onClick={function() { addToast('Schedule feature coming soon', 'info') }}>
          Schedule a Report
        </button>
      </div>
    </div>
  )
}

export default Reports
