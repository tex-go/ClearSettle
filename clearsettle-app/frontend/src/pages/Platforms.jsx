import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import useApi from '../hooks/useApi'
import { StatusChip } from '../components/ui/Chip'
import { Modal } from '../components/ui/Modal'
import useUIStore from '../store/uiStore'
import api from '../utils/api'

var STATUS_TABS = ['All', 'Connected', 'Pending', 'Not Connected']

var PLATFORM_META = {
  amazon:   { icon: '🛒', label: 'Amazon',   sp_api: true },
  flipkart: { icon: '🛍️', label: 'Flipkart',  sp_api: false },
  meesho:   { icon: '👗', label: 'Meesho',    sp_api: false },
  myntra:   { icon: '👠', label: 'Myntra',    sp_api: false },
  nykaa:    { icon: '💄', label: 'Nykaa',     sp_api: false },
  ajio:     { icon: '👔', label: 'AJIO',      sp_api: false },
  snapdeal: { icon: '🏷️', label: 'Snapdeal',  sp_api: false },
  jiomart:  { icon: '🛒', label: 'JioMart',   sp_api: false },
}

var STATUS_DOT = {
  connected:     '#0DB07A',
  configured:    '#0ABFCA',
  oauth_pending: '#E9930D',
  pending:       '#E9930D',
  disconnected:  '#8FA5BD',
  error:         '#E8344A',
}

var STATUS_LABEL = {
  connected:     'Connected',
  configured:    'Credentials saved — OAuth pending',
  oauth_pending: 'Awaiting Amazon auth…',
  pending:       'Pending',
  disconnected:  'Not connected',
  error:         'Connection error',
}

var DEFAULT_CRED_FORM = {
  app_id:         '',
  client_id:      '',
  client_secret:  '',
  redirect_uri:   window.location.origin + '/api/sp-api/callback',
  marketplace_id: 'A21TJRUUN4KGV',
  region:         'eu',
}

function SyncJobsTable({ connectionId }) {
  var { data, loading } = useApi('/sp-api/connections/' + connectionId + '/sync-jobs')
  if (loading) return <div className="spinner" style={{ margin: '20px auto' }} />
  var jobs = data || []
  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Sync History</div>
      {jobs.length === 0 && (
        <div style={{ color: '#8FA5BD', fontSize: 13 }}>No sync jobs yet.</div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {jobs.map(function(j) {
          var color = j.status === 'completed' ? '#0DB07A' : j.status === 'failed' ? '#E8344A' : '#E9930D'
          return (
            <div key={j.id} style={{
              padding: '10px 14px', borderRadius: 10,
              background: '#F8FAFC', border: '1px solid #E2EBF3', fontSize: 12,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontWeight: 700, textTransform: 'capitalize' }}>{j.job_type}</span>
                <span style={{ color, fontWeight: 700, textTransform: 'uppercase', fontSize: 11 }}>{j.status}</span>
              </div>
              <div style={{ color: '#4B6080' }}>
                {j.records_synced > 0 && <span>{j.records_synced} records · </span>}
                {j.completed_at && <span>Completed {new Date(j.completed_at).toLocaleString('en-IN')}</span>}
                {j.error_message && <div style={{ color: '#E8344A', marginTop: 4 }}>{j.error_message}</div>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Credentials field config ───────────────────────────────────────────────

var CRED_FIELDS = [
  {
    key: 'app_id',
    label: 'SP API Application ID',
    type: 'text',
    placeholder: 'amzn1.sellerapps.app.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
    help: 'Found in Seller Central → Apps & Services → Develop Apps → Your App',
    required: true,
  },
  {
    key: 'client_id',
    label: 'LWA Client ID',
    type: 'text',
    placeholder: 'amzn1.application-oa2-client.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    help: 'Login with Amazon Client ID from your SP API app settings',
    required: true,
  },
  {
    key: 'client_secret',
    label: 'LWA Client Secret',
    type: 'password',
    placeholder: 'amzn1.oa2-cs.v1.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    help: 'Keep this secret — stored encrypted in the database',
    required: true,
  },
  {
    key: 'redirect_uri',
    label: 'OAuth Redirect URI',
    type: 'text',
    placeholder: 'https://yourdomain.com/api/sp-api/callback',
    help: 'Must exactly match the redirect URI registered in your SP API app',
    required: true,
  },
]

function Platforms() {
  var { data, loading } = useApi('/platforms/')
  var addToast = useUIStore(function(s) { return s.addToast })
  var [tab, setTab] = useState('All')
  var [connectModal, setConnectModal] = useState(null)
  var [configModal, setConfigModal] = useState(null)
  var [syncJobsModal, setSyncJobsModal] = useState(null)
  var [connectForm, setConnectForm] = useState({ api_key: '', secret: '', seller_id: '' })
  var [connecting, setConnecting] = useState(false)
  var [syncing, setSyncing] = useState(null)
  var [searchParams] = useSearchParams()

  // SP API credentials modal state
  var [credModal, setCredModal] = useState(false)
  var [credForm, setCredForm] = useState(DEFAULT_CRED_FORM)
  var [credSaving, setCredSaving] = useState(false)
  var [credErrors, setCredErrors] = useState({})

  // Handle OAuth callback redirect (?connected=amazon&status=success)
  useEffect(function() {
    var connected = searchParams.get('connected')
    var status = searchParams.get('status')
    if (connected && status === 'success') {
      addToast(connected.charAt(0).toUpperCase() + connected.slice(1) + ' SP API connected successfully!', 'success')
    }
    if (status === 'error') {
      addToast('Amazon SP API connection failed. Please try again.', 'error')
    }
  }, [])

  if (loading || !data) {
    return <div className="loading-wrap page-anim"><div className="spinner" /></div>
  }

  var filtered = data.items.filter(function(p) {
    if (tab === 'All') return true
    if (tab === 'Connected') return p.status === 'connected'
    if (tab === 'Pending') return p.status === 'pending' || p.status === 'oauth_pending'
    if (tab === 'Not Connected') return p.status === 'disconnected' || p.status === 'configured'
    return true
  })

  // ── Amazon SP API OAuth — fast path (credentials already saved) ────────────
  async function startOAuthFlow() {
    setConnecting(true)
    try {
      var res = await api.get('/sp-api/authorize')
      window.location.href = res.data.authorization_url
    } catch (err) {
      setConnecting(false)
      var status = err?.response?.status
      var detail = err?.response?.data?.detail || ''
      var isCredsMissing = (
        status === 503 ||
        (typeof detail === 'string' && (
          detail.toLowerCase().includes('not configured') ||
          detail.toLowerCase().includes('credentials')
        ))
      )
      if (isCredsMissing) {
        setCredModal(true)
      } else if (!err.response) {
        addToast('Network error — please check your connection', 'error')
      } else {
        addToast(detail || 'Failed to initiate Amazon connection', 'error')
      }
    }
  }

  // ── Validate credentials form ─────────────────────────────────────────────
  function validateCredForm() {
    var errs = {}
    CRED_FIELDS.forEach(function(f) {
      if (f.required && !credForm[f.key].trim()) {
        errs[f.key] = f.label + ' is required'
      }
    })
    setCredErrors(errs)
    return Object.keys(errs).length === 0
  }

  // ── Save credentials then start OAuth ─────────────────────────────────────
  async function handleSaveCredentialsAndConnect() {
    if (!validateCredForm()) return

    setCredSaving(true)
    try {
      await api.post('/sp-api/config', {
        app_id:         credForm.app_id.trim(),
        client_id:      credForm.client_id.trim(),
        client_secret:  credForm.client_secret.trim(),
        redirect_uri:   credForm.redirect_uri.trim(),
        marketplace_id: credForm.marketplace_id,
        region:         credForm.region,
      })
      var res = await api.get('/sp-api/authorize')
      setCredModal(false)
      window.location.href = res.data.authorization_url
    } catch (err) {
      setCredSaving(false)
      var detail = err?.response?.data?.detail
      addToast(
        typeof detail === 'string' ? detail : 'Failed to save credentials. Check all fields and try again.',
        'error'
      )
    }
  }

  // ── Generic API key connect ────────────────────────────────────────────────
  function handleGenericConnect() {
    setConnecting(true)
    api.post('/platforms/' + connectModal.id + '/connect', connectForm)
      .then(function() {
        addToast(connectModal.label + ' connected!', 'success')
        setConnectModal(null)
        setConnectForm({ api_key: '', secret: '', seller_id: '' })
        window.location.reload()
      })
      .catch(function() {
        addToast('Connection failed — check your credentials', 'error')
      })
      .finally(function() { setConnecting(false) })
  }

  // ── Sync triggers ─────────────────────────────────────────────────────────
  function handleSyncOrders(p) {
    if (!p.connection_id) return
    setSyncing(p.id)
    api.post('/sp-api/connections/' + p.connection_id + '/sync/orders?days_back=30')
      .then(function() { addToast('Order sync started for ' + (p.label || p.name), 'info') })
      .catch(function(err) { addToast(err.response?.data?.detail || 'Sync failed', 'error') })
      .finally(function() { setSyncing(null) })
  }

  function handleSyncSettlements(p) {
    if (!p.connection_id) return
    setSyncing(p.id + '_settlements')
    api.post('/sp-api/connections/' + p.connection_id + '/sync/settlements?days_back=30')
      .then(function() { addToast('Settlement sync started for ' + (p.label || p.name), 'info') })
      .catch(function(err) { addToast(err.response?.data?.detail || 'Sync failed', 'error') })
      .finally(function() { setSyncing(null) })
  }

  function handleDisconnect(p) {
    if (!p.connection_id) return
    api.delete('/sp-api/connections/' + p.connection_id)
      .then(function() {
        addToast(p.label + ' disconnected', 'warn')
        setConfigModal(null)
        window.location.reload()
      })
      .catch(function() { addToast('Disconnect failed', 'error') })
  }

  return (
    <div className="page page-anim">
      {/* Banner */}
      <div className="ab inf" style={{ marginBottom: 24 }}>
        <span>ℹ️</span>
        <div className="ab-body">
          <div className="ab-title">
            {data.summary.connected} of {data.items.length} platforms connected
          </div>
          <div className="ab-sub">
            Connect platforms to sync settlements, orders, and returns automatically
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {STATUS_TABS.map(function(t) {
          var count = data.items.filter(function(p) {
            if (t === 'All') return true
            if (t === 'Connected') return p.status === 'connected'
            if (t === 'Pending') return p.status === 'pending' || p.status === 'oauth_pending'
            if (t === 'Not Connected') return p.status === 'disconnected' || p.status === 'configured'
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
          var meta = PLATFORM_META[p.id] || { icon: '🏪', label: p.name, sp_api: false }
          var dotColor = STATUS_DOT[p.status] || '#8FA5BD'
          var statusLabel = STATUS_LABEL[p.status] || p.status
          var isDisconnected = p.status === 'disconnected' || p.status === 'error' || p.status === 'configured'

          return (
            <div key={p.id} className="card" style={{ padding: '18px 22px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                {/* Icon + status dot */}
                <div style={{ position: 'relative', flexShrink: 0 }}>
                  <span style={{ fontSize: 28 }}>{meta.icon}</span>
                  <div style={{
                    position: 'absolute', bottom: -2, right: -2,
                    width: 10, height: 10, borderRadius: '50%',
                    background: dotColor, border: '2px solid #fff',
                  }} />
                </div>

                {/* Name + details */}
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 800, fontSize: 15 }}>{meta.label}</span>
                    {meta.sp_api && (
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '2px 7px',
                        borderRadius: 6, background: 'rgba(10,191,202,.12)', color: '#0ABFCA',
                      }}>SP API</span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: '#8FA5BD', marginTop: 2 }}>{statusLabel}</div>
                  {p.status === 'connected' && p.total_orders_synced > 0 && (
                    <div style={{ fontSize: 12, color: '#4B6080', marginTop: 4 }}>
                      {p.total_orders_synced.toLocaleString('en-IN')} orders synced
                      {p.last_sync && ' · Last sync: ' + new Date(p.last_sync).toLocaleDateString('en-IN')}
                    </div>
                  )}
                  {p.status === 'error' && (
                    <div style={{ fontSize: 12, color: '#E8344A', marginTop: 4 }}>
                      Connection error — reconnect required
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  <StatusChip status={p.status} />

                  {p.status === 'connected' && (
                    <>
                      {meta.sp_api && (
                        <>
                          <button
                            className="btn btn-s btn-sm"
                            disabled={syncing === p.id}
                            onClick={function() { handleSyncOrders(p) }}
                          >
                            {syncing === p.id ? '⏳' : '🔄'} Orders
                          </button>
                          <button
                            className="btn btn-s btn-sm"
                            disabled={syncing === p.id + '_settlements'}
                            onClick={function() { handleSyncSettlements(p) }}
                          >
                            {syncing === p.id + '_settlements' ? '⏳' : '📊'} Settlements
                          </button>
                          <button
                            className="btn btn-s btn-sm"
                            onClick={function() { setSyncJobsModal(p) }}
                          >
                            📋 History
                          </button>
                        </>
                      )}
                      <button
                        className="btn btn-g btn-sm"
                        onClick={function() { setConfigModal({ ...p, ...meta }) }}
                      >
                        ⚙ Settings
                      </button>
                    </>
                  )}

                  {isDisconnected && (
                    meta.sp_api
                      ? (
                        <button
                          className="btn btn-p btn-sm"
                          disabled={connecting}
                          onClick={startOAuthFlow}
                          style={{ background: 'linear-gradient(135deg,#FF9900,#FF6600)', border: 'none' }}
                        >
                          {connecting ? 'Please wait…' : '🔗 Connect via Amazon'}
                        </button>
                      )
                      : (
                        <button
                          className="btn btn-p btn-sm"
                          onClick={function() { setConnectModal({ ...p, ...meta }) }}
                        >
                          + Connect
                        </button>
                      )
                  )}

                  {p.status === 'oauth_pending' && (
                    <button
                      className="btn btn-s btn-sm"
                      disabled={connecting}
                      onClick={startOAuthFlow}
                    >
                      {connecting ? 'Please wait…' : 'Resume Auth →'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* SP API info banner */}
      <div className="card" style={{ marginTop: 24, padding: '18px 22px', background: 'rgba(10,191,202,.04)', border: '1px solid rgba(10,191,202,.2)' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#0ABFCA', marginBottom: 6 }}>
          🔒 Amazon SP API — Secure OAuth 2.0 Connection
        </div>
        <div style={{ fontSize: 12, color: '#4B6080', lineHeight: 1.7 }}>
          ClearSettle uses Amazon's official Selling Partner API with LWA (Login with Amazon) OAuth.
          Your credentials are encrypted at rest using AES-256 Fernet encryption.
          We only request <strong>read-only</strong> scopes: Orders, Finances, and Reports.
          Access tokens refresh automatically every hour.
        </div>
      </div>

      {/* ── SP API Credentials Modal ──────────────────────────────────────────── */}
      {credModal && (
        <Modal
          open={credModal}
          title="Amazon SP API — Developer Credentials"
          sub="Enter your SP API app credentials to enable the OAuth connection"
          onClose={function() {
            if (!credSaving) {
              setCredModal(false)
              setCredErrors({})
              setConnecting(false)
            }
          }}
          size="lg"
          footer={
            <>
              <button
                className="btn btn-s"
                disabled={credSaving}
                onClick={function() {
                  setCredModal(false)
                  setCredErrors({})
                  setConnecting(false)
                }}
              >
                Cancel
              </button>
              <button
                className="btn btn-p"
                disabled={credSaving}
                onClick={handleSaveCredentialsAndConnect}
                style={{ background: 'linear-gradient(135deg,#FF9900,#FF6600)', border: 'none' }}
              >
                {credSaving ? 'Saving & connecting…' : 'Save & Connect via Amazon →'}
              </button>
            </>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>

            {/* Info alert */}
            <div className="ab inf" style={{ marginBottom: 12 }}>
              <span>ℹ️</span>
              <div className="ab-body">
                <div className="ab-title">Where to find these credentials</div>
                <div className="ab-sub">
                  Log in to <strong>Seller Central</strong> → Apps &amp; Services → Develop Apps →
                  select your app → View credentials. Your App ID and LWA credentials are listed there.
                </div>
              </div>
            </div>

            {/* Credential fields */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {CRED_FIELDS.map(function(f) {
                return (
                  <div key={f.key} className="fg">
                    <label style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>{f.label} {f.required && <span style={{ color: '#E8344A' }}>*</span>}</span>
                    </label>
                    <input
                      type={f.type}
                      placeholder={f.placeholder}
                      value={credForm[f.key]}
                      autoComplete="off"
                      onChange={function(e) {
                        var val = e.target.value
                        setCredForm(function(prev) { return Object.assign({}, prev, { [f.key]: val }) })
                        if (credErrors[f.key]) {
                          setCredErrors(function(prev) { return Object.assign({}, prev, { [f.key]: '' }) })
                        }
                      }}
                      style={credErrors[f.key] ? { borderColor: '#E8344A' } : {}}
                    />
                    {credErrors[f.key]
                      ? <div style={{ fontSize: 11, color: '#E8344A', marginTop: 4 }}>{credErrors[f.key]}</div>
                      : <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 4 }}>{f.help}</div>
                    }
                  </div>
                )
              })}

              {/* Advanced: marketplace / region */}
              <details style={{ marginTop: 4 }}>
                <summary style={{ fontSize: 12, color: '#4B6080', cursor: 'pointer', userSelect: 'none' }}>
                  Advanced settings (Marketplace &amp; Region)
                </summary>
                <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
                  <div className="fg" style={{ flex: 1 }}>
                    <label>Marketplace ID</label>
                    <input
                      type="text"
                      value={credForm.marketplace_id}
                      onChange={function(e) {
                        var val = e.target.value
                        setCredForm(function(prev) { return Object.assign({}, prev, { marketplace_id: val }) })
                      }}
                    />
                    <div style={{ fontSize: 11, color: '#8FA5BD', marginTop: 4 }}>Default: A21TJRUUN4KGV (Amazon.in)</div>
                  </div>
                  <div className="fg" style={{ flex: 1 }}>
                    <label>Region</label>
                    <select
                      value={credForm.region}
                      onChange={function(e) {
                        var val = e.target.value
                        setCredForm(function(prev) { return Object.assign({}, prev, { region: val }) })
                      }}
                    >
                      <option value="eu">EU (India, Europe, Middle East)</option>
                      <option value="na">NA (North America)</option>
                      <option value="fe">FE (Far East)</option>
                    </select>
                  </div>
                </div>
              </details>
            </div>

            {/* Security note */}
            <div style={{
              marginTop: 8, padding: '10px 14px', borderRadius: 10,
              background: 'rgba(13,176,122,.06)', border: '1px solid rgba(13,176,122,.2)',
              fontSize: 12, color: '#4B6080',
            }}>
              🔒 <strong>Your credentials are stored encrypted</strong> (AES-256 Fernet) and never logged.
              The client secret is used only to exchange OAuth codes for tokens.
            </div>
          </div>
        </Modal>
      )}

      {/* ── Generic Connect Modal ─────────────────────────────────────────────── */}
      {connectModal && (
        <Modal
          open={!!connectModal}
          title={'Connect ' + connectModal.label}
          sub={'Link your ' + connectModal.label + ' seller account'}
          onClose={function() { setConnectModal(null) }}
          size="sm"
          footer={
            <>
              <button className="btn btn-s" onClick={function() { setConnectModal(null) }}>Cancel</button>
              <button className="btn btn-p" disabled={connecting} onClick={handleGenericConnect}>
                {connecting ? 'Connecting…' : 'Save & Connect →'}
              </button>
            </>
          }
        >
          <div className="ab inf" style={{ marginBottom: 16 }}>
            <span>ℹ️</span>
            <div className="ab-body">
              <div className="ab-title">Read-only access</div>
              <div className="ab-sub">ClearSettle only reads settlement and order data</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {[
              { label: 'API Key / Client ID', key: 'api_key', type: 'text', placeholder: 'Enter API key' },
              { label: 'API Secret', key: 'secret', type: 'password', placeholder: 'Enter secret' },
              { label: 'Seller ID', key: 'seller_id', type: 'text', placeholder: 'Enter seller ID' },
            ].map(function(f) {
              return (
                <div key={f.key} className="fg">
                  <label>{f.label}</label>
                  <input
                    type={f.type}
                    placeholder={f.placeholder}
                    value={connectForm[f.key]}
                    onChange={function(e) {
                      var val = e.target.value
                      setConnectForm(function(prev) { return Object.assign({}, prev, { [f.key]: val }) })
                    }}
                  />
                </div>
              )
            })}
          </div>
        </Modal>
      )}

      {/* ── Configure / Disconnect Modal ──────────────────────────────────────── */}
      {configModal && (
        <Modal
          open={!!configModal}
          title={'Configure ' + configModal.label}
          sub={'Manage SP API settings and sync preferences'}
          onClose={function() { setConfigModal(null) }}
          size="lg"
          footer={
            <>
              <button className="btn btn-s" onClick={function() { setConfigModal(null) }}>Close</button>
              {configModal.sp_api && configModal.connection_id && (
                <button
                  className="btn btn-d btn-sm"
                  onClick={function() {
                    if (window.confirm('Disconnect ' + configModal.label + '? All stored tokens will be deleted.')) {
                      handleDisconnect(configModal)
                    }
                  }}
                >
                  Disconnect
                </button>
              )}
            </>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                { label: 'Selling Partner ID', val: configModal.selling_partner_id || '—' },
                { label: 'Marketplace ID',     val: configModal.marketplace_id || '—' },
                { label: 'Orders Synced',      val: (configModal.total_orders_synced || 0).toLocaleString('en-IN') },
                { label: 'Last Sync',          val: configModal.last_sync ? new Date(configModal.last_sync).toLocaleString('en-IN') : 'Never' },
              ].map(function(item) {
                return (
                  <div key={item.label} style={{
                    padding: '12px 14px', borderRadius: 10,
                    background: '#F8FAFC', border: '1px solid #E2EBF3',
                  }}>
                    <div style={{ fontSize: 11, color: '#8FA5BD', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
                      {item.label}
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
                      {item.val}
                    </div>
                  </div>
                )
              })}
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#4B6080', marginBottom: 10, textTransform: 'uppercase' }}>
                Active Data Streams
              </div>
              {['Orders', 'Settlements', 'Returns', 'Commission', 'Inventory', 'GST/TCS'].map(function(opt) {
                return (
                  <div key={opt} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 0', borderBottom: '1px solid #E2EBF3',
                  }}>
                    <span style={{ fontSize: 13 }}>{opt}</span>
                    <div style={{
                      width: 36, height: 20, borderRadius: 10,
                      background: '#0ABFCA', cursor: 'pointer', position: 'relative',
                    }}>
                      <div style={{
                        width: 16, height: 16, borderRadius: '50%',
                        background: '#fff', position: 'absolute', top: 2, right: 2,
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </Modal>
      )}

      {/* ── Sync Jobs History Modal ───────────────────────────────────────────── */}
      {syncJobsModal && (
        <Modal
          open={!!syncJobsModal}
          title={'Sync History — ' + (PLATFORM_META[syncJobsModal.id]?.label || syncJobsModal.id)}
          sub={'Last 20 sync jobs'}
          onClose={function() { setSyncJobsModal(null) }}
          size="md"
          footer={<button className="btn btn-s" onClick={function() { setSyncJobsModal(null) }}>Close</button>}
        >
          {syncJobsModal.connection_id
            ? <SyncJobsTable connectionId={syncJobsModal.connection_id} />
            : <div style={{ color: '#8FA5BD', fontSize: 13 }}>No connection ID available.</div>
          }
        </Modal>
      )}
    </div>
  )
}

export default Platforms
