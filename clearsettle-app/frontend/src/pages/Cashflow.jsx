import React from 'react'
import useApi from '../hooks/useApi'
import { INR } from '../utils/format'

var EVENT_TYPE_COLOR = { expected: '#2563EB', paid: '#0DB07A', predicted: '#E9930D' }
var EVENT_TYPE_LABEL = { expected: 'Expected', paid: 'Confirmed', predicted: 'Predicted' }

function Cashflow() {
  var { data, loading } = useApi('/cashflow/')

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var s = data.summary
  var events = data.events

  var eventsByDate = {}
  events.forEach(function(ev) {
    var day = parseInt(ev.date.split('-')[2], 10)
    if (!eventsByDate[day]) eventsByDate[day] = []
    eventsByDate[day].push(ev)
  })

  var daysInMay = 31
  var mayStartDay = 4

  return (
    <div className="page page-anim">
      {/* Stats */}
      <div className="stats-row cols-3">
        {[
          { label: 'Expected This Month', val: INR(s.expected_total), stripe: 'tl' },
          {
            label: 'Next Settlement',
            val: s.next_settlement ? INR(s.next_settlement.amt) : '—',
            sub: s.next_settlement ? s.next_settlement.label : '',
            stripe: 'bl',
          },
          { label: '30-Day Forecast', val: INR(s.expected_total), sub: 'Estimated total', stripe: 'gn' },
        ].map(function(k) {
          return (
            <div key={k.label} className="stat-card">
              <div className={'sc-stripe ' + k.stripe} />
              <div className="sc-label" style={{ marginTop: 8 }}>{k.label}</div>
              <div className="sc-val">{k.val}</div>
              {k.sub && <div className="sc-sub">{k.sub}</div>}
            </div>
          )
        })}
      </div>

      <div className="two-col-wide">
        {/* Calendar */}
        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-title">May 2026</div>
              <div className="card-sub">Settlement forecast calendar</div>
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              {Object.entries(EVENT_TYPE_LABEL).map(function(entry) {
                return (
                  <div key={entry[0]} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: EVENT_TYPE_COLOR[entry[0]] }} />
                    <span style={{ fontSize: 11, color: '#8FA5BD' }}>{entry[1]}</span>
                  </div>
                )
              })}
            </div>
          </div>
          <div className="card-bd">
            {/* Day headers */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 4 }}>
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(function(d) {
                return (
                  <div key={d} style={{ textAlign: 'center', fontSize: 11, fontWeight: 700, color: '#8FA5BD', padding: '4px 0' }}>
                    {d}
                  </div>
                )
              })}
            </div>
            {/* Calendar grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
              {/* Empty cells */}
              {Array.from({ length: mayStartDay }).map(function(_, i) {
                return <div key={'empty-' + i} />
              })}
              {/* Day cells */}
              {Array.from({ length: daysInMay }).map(function(_, i) {
                var day = i + 1
                var isToday = day === 16
                var dayEvents = eventsByDate[day] || []
                return (
                  <div key={day} style={{
                    padding: '6px 4px 4px',
                    borderRadius: 8,
                    background: isToday ? 'rgba(10,191,202,.12)' : dayEvents.length > 0 ? 'rgba(37,99,235,.04)' : 'transparent',
                    border: isToday ? '1.5px solid #0ABFCA' : '1px solid transparent',
                    minHeight: 52, position: 'relative',
                  }}>
                    <div style={{
                      fontSize: 12, fontWeight: isToday ? 800 : 400,
                      color: isToday ? '#0ABFCA' : '#4B6080',
                      textAlign: 'center',
                    }}>
                      {day}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2, marginTop: 4, justifyContent: 'center' }}>
                      {dayEvents.map(function(ev, j) {
                        return (
                          <div key={j} style={{
                            width: 6, height: 6, borderRadius: '50%',
                            background: EVENT_TYPE_COLOR[ev.type] || '#8FA5BD',
                          }} title={ev.label + ' — ' + INR(ev.amt)} />
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Upcoming list */}
        <div className="card">
          <div className="card-hd">
            <div className="card-title">Upcoming Settlements</div>
          </div>
          <div className="card-bd" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {events
              .filter(function(ev) { return ev.type !== 'paid' })
              .sort(function(a, b) { return a.date.localeCompare(b.date) })
              .map(function(ev, i) {
                var day = ev.date.split('-')[2]
                var color = EVENT_TYPE_COLOR[ev.type]
                return (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 12px', borderRadius: 10,
                    background: '#F1F5F9',
                  }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 8, flexShrink: 0,
                      background: color + '22', color: color,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 16, fontWeight: 800,
                    }}>
                      {day}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 700 }}>{ev.label}</div>
                      <div style={{ fontSize: 11, color: '#8FA5BD' }}>{ev.date}</div>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: color }}>
                      {INR(ev.amt)}
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Cashflow
