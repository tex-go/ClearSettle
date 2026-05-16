import React, { useState } from 'react'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import { Modal } from '../components/ui/Modal'
import useUIStore from '../store/uiStore'
import { INRL } from '../utils/format'
import api from '../utils/api'

var STATUS_TABS = ['All', 'Connected', 'Pending', 'Not Connected']

var statusDot = {
  connected: { bg: '#0DB07A', pulse: true },
  pending: { bg: '#E9930D', pulse: true },
  disconnected: { bg: '#8FA5BD', pulse: false },
}

function Platforms() {
  var { data, loading } = useApi('/platforms/')
  var addToast = useUIStore(function(s) { return s.addToast })
  var [tab, setTab] = useState('All')
  var [connectModal, setConnectModal] = useState(null)
  var [configModal, setConfigModal] = useState(null)
  var [connectForm, setConnectForm] = useState({ api_key: '', secret: '', seller_id: '' })

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var filtered = data.items.filter(function(p) {
    if (tab === 'All') return true
    if (tab === 'Connected') return p.status === 'connected'
    if (tab === 'Pending') return p.status === 'pending'
    if (tab === 'Not Connected') return p.status === 'disconnected'
    return true
  })

  function handleConnect() {
    api.post('/platforms/' + connectModal.id + '/connect', connectForm)
      .then(function() {
        addToast(connectModal.name + ' connected!', 'success')
        setConnectModal(null)
      })
  }

  function handleSync(p) {
    api.post('/platforms/' + p.id + '/sync').then(function() {
      addToast('Syncing ' + p.name + '...', 'info')
    })
  }

  return (
    <div className="page page-anim">
      {/* Banner */}
      <div className="ab inf" style={{ marginBottom: 24 }}>
        <span>ℹ️</span>
        <div className="ab-body">
          <div className="ab-title">{data.summary.connected} of {data.items.length} platforms connected</div>
          <div className="ab-sub">Connect more platforms to get a complete view of your eCommerce operations</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {STATUS_TABS.map(function(t) {
          var count = data.items.filter(function(p) {
            if (t === 'All') return true
            if (t === 'Connected') return p.status === 'connected'
            if (t === 'Pending') return p.status === 'pending'
            if (t === 'Not Connected') return p.status === 'disconnected'
            return true
          }).length
          return (
            <button
              key={t}
              className={'pill' + (tab === t ? ' active' : '')}
              onClick={function() { setTab(t) }}
            >
              {t} ({count})
            </button>
          )
        })}
      </div>

      {/* Platform list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {filtered.map(function(p) {
          var dot = statusDot[p.status] || statusDot.disconnected
          return (
            <div key={p.id} className="card" style={{ padding: '18px 22px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                {/* Icon + status dot */}
                <div style={{ position: 'relative', flexShrink: 0 }}>
                  <span style={{ fontSize: 28 }}>{p.icon}</span>
                  <div style={{
                    position: 'absolute', bottom: -2, right: -2,
                    width: 10, height: 10, borderRadius: '50%',
                    background: dot.bg, border: '2px solid #fff',
                  }} />
                </div>

                {/* Name + details */}
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 800, fontSize: 15 }}>{p.name}</div>
                  <div style={{ fontSize: 12, color: '#8FA5BD' }}>Phase {p.phase} · {p.ep}</div>
                  {p.status === 'connected' && (
                    <div style={{ fontSize: 12, color: '#4B6080', marginTop: 4 }}>
                      {INRL(p.gmv)} GMV · {p.orders} orders · Last sync: {p.sync}
                    </div>
                  )}
                  {p.status === 'pending' && (
                    <div style={{ fontSize: 12, color: '#E9930D', marginTop: 4 }}>
                      Connection pending approval
                    </div>
                  )}
                  {p.status === 'disconnected' && (
                    <div style={{ fontSize: 12, color: '#8FA5BD', marginTop: 4 }}>
                      Not connected — link your account to start syncing
                    </div>
                  )}
                </div>

                {/* Status + actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <StatusChip status={p.status} />
                  {p.status === 'connected' && (
                    <>
                      <button className="btn btn-s btn-sm" onClick={function() { setConfigModal(p) }}>
                        ⚙ Configure
                      </button>
                      <button className="btn btn-g btn-sm" onClick={function() { handleSync(p) }}>
                        🔄
                      </button>
                    </>
                  )}
                  {p.status === 'pending' && (
                    <button className="btn btn-s btn-sm" onClick={function() { addToast('Checking status for ' + p.name, 'info') }}>
                      Check Status
                    </button>
                  )}
                  {p.status === 'disconnected' && (
                    <button className="btn btn-p btn-sm" onClick={function() { setConnectModal(p) }}>
                      + Connect
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Connect Modal */}
      {connectModal && (
        <Modal
          open={!!connectModal}
          title={'Connect ' + connectModal.name}
          sub={'Link your ' + connectModal.name + ' seller account'}
          onClose={function() { setConnectModal(null) }}
          size="sm"
          footer={
            <>
              <button className="btn btn-s" onClick={function() { setConnectModal(null) }}>Cancel</button>
              <button className="btn btn-g btn-sm" onClick={function() { addToast('Testing connection...', 'info') }}>
                Test Connection
              </button>
              <button className="btn btn-p" onClick={handleConnect}>Save & Connect →</button>
            </>
          }
        >
          <div className="ab inf" style={{ marginBottom: 16 }}>
            <span>ℹ️</span>
            <div className="ab-body">
              <div className="ab-title">Read-only access only</div>
              <div className="ab-sub">ClearSettle only reads settlement and order data — no write access</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="fg">
              <label>App ID / Client ID</label>
              <input
                placeholder="Enter App ID"
                value={connectForm.api_key}
                onChange={function(e) { setConnectForm({ ...connectForm, api_key: e.target.value }) }}
              />
            </div>
            <div className="fg">
              <label>App Secret</label>
              <input
                type="password"
                placeholder="Enter App Secret"
                value={connectForm.secret}
                onChange={function(e) { setConnectForm({ ...connectForm, secret: e.target.value }) }}
              />
            </div>
            <div className="fg">
              <label>Seller ID</label>
              <input
                placeholder="Enter Seller ID"
                value={connectForm.seller_id}
                onChange={function(e) { setConnectForm({ ...connectForm, seller_id: e.target.value }) }}
              />
            </div>
          </div>
        </Modal>
      )}

      {/* Configure Modal */}
      {configModal && (
        <Modal
          open={!!configModal}
          title={'Configure ' + configModal.name}
          sub={'Manage API settings and sync preferences'}
          onClose={function() { setConfigModal(null) }}
          size="lg"
          footer={
            <>
              <button className="btn btn-s" onClick={function() { setConfigModal(null) }}>Cancel</button>
              <button className="btn btn-d btn-sm" onClick={function() { addToast(configModal.name + ' disconnected', 'warn'); setConfigModal(null) }}>
                Disconnect
              </button>
              <button className="btn btn-p" onClick={function() { addToast('Settings saved', 'success'); setConfigModal(null) }}>
                Save Settings
              </button>
            </>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="fg">
              <label>API Key</label>
              <input defaultValue={configModal.key} />
            </div>
            <div className="fg">
              <label>Sync Frequency</label>
              <select defaultValue="every_hour">
                {['Every 15 minutes', 'Every hour', 'Every 6 hours', 'Daily'].map(function(f) {
                  return <option key={f}>{f}</option>
                })}
              </select>
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#4B6080', marginBottom: 10 }}>Data Pull Settings</div>
              {['Settlements', 'Returns', 'Commission', 'Inventory', 'Orders', 'GST/TCS'].map(function(opt) {
                return (
                  <div key={opt} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '8px 0', borderBottom: '1px solid #E2EBF3',
                  }}>
                    <span style={{ fontSize: 13 }}>{opt}</span>
                    <div style={{
                      width: 36, height: 20, borderRadius: 10,
                      background: '#0ABFCA', cursor: 'pointer',
                      position: 'relative',
                    }}>
                      <div style={{
                        width: 16, height: 16, borderRadius: '50%',
                        background: '#fff', position: 'absolute',
                        top: 2, right: 2,
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default Platforms
