import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

var STEPS = ['Company Setup', 'Connect Platforms', 'Test Connections', 'Done']

var PLATFORMS_OB = [
  { id: 'amazon', name: 'Amazon', icon: '🛒', connected: true },
  { id: 'flipkart', name: 'Flipkart', icon: '🛍️', connected: true },
  { id: 'meesho', name: 'Meesho', icon: '👗', connected: true },
  { id: 'myntra', name: 'Myntra', icon: '👠', connected: false },
  { id: 'nykaa', name: 'Nykaa', icon: '💄', connected: false },
  { id: 'ajio', name: 'AJIO', icon: '👔', connected: false },
  { id: 'snapdeal', name: 'Snapdeal', icon: '🏷️', connected: false },
  { id: 'jiomart', name: 'JioMart', icon: '🛒', connected: false },
]

var TEST_RESULTS = [
  { platform: 'Amazon', icon: '🛒', orders: '2,847 orders', gmv: '₹18.4L GMV' },
  { platform: 'Flipkart', icon: '🛍️', orders: '1,923 orders', gmv: '₹12.8L GMV' },
  { platform: 'Meesho', icon: '👗', orders: '3,401 orders', gmv: '₹5.2L GMV' },
]

function Onboarding() {
  var navigate = useNavigate()
  var [step, setStep] = useState(0)
  var [form, setForm] = useState({
    company: 'Tirupur Exports Pvt. Ltd.',
    gstin: '33ABCDE1234F1Z5',
    city: 'Tirupur, Tamil Nadu',
    industry: 'Textile & Apparel',
    email: 'demo@clearsettle.in',
  })
  var [platforms, setPlatforms] = useState(PLATFORMS_OB)

  function handleFinish() {
    localStorage.setItem('cs_onboarded', '1')
    navigate('/')
  }

  function togglePlatform(id) {
    setPlatforms(platforms.map(function(p) {
      return p.id === id ? { ...p, connected: !p.connected } : p
    }))
  }

  return (
    <div style={{
      minHeight: '100vh', background: 'linear-gradient(135deg,#0D1F35,#0A1628)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 40,
    }}>
      <div style={{
        background: '#fff', borderRadius: 20, maxWidth: 680, width: '100%',
        overflow: 'hidden', boxShadow: '0 32px 80px rgba(0,0,0,.4)',
      }}>
        {/* Step indicator */}
        <div style={{ padding: '28px 36px 24px', borderBottom: '1px solid #E2EBF3' }}>
          <div style={{ fontSize: 11, color: '#8FA5BD', fontWeight: 700, marginBottom: 16 }}>
            Step {step + 1} of {STEPS.length}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
            {STEPS.map(function(s, i) {
              return (
                <React.Fragment key={i}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%',
                      background: i < step ? '#0DB07A' : i === step ? '#0ABFCA' : '#E2EBF3',
                      color: i <= step ? '#fff' : '#8FA5BD',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 13, fontWeight: 700, flexShrink: 0,
                    }}>
                      {i < step ? '✓' : i + 1}
                    </div>
                    <div style={{
                      fontSize: 10, fontWeight: 600,
                      color: i === step ? '#0ABFCA' : '#8FA5BD',
                      whiteSpace: 'nowrap',
                    }}>
                      {s}
                    </div>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div style={{
                      flex: 1, height: 2, margin: '0 8px',
                      background: i < step ? '#0DB07A' : '#E2EBF3',
                      marginBottom: 22,
                    }} />
                  )}
                </React.Fragment>
              )
            })}
          </div>
        </div>

        <div style={{ padding: '28px 36px 32px' }}>
          {/* Step 0: Company Setup */}
          {step === 0 && (
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 6 }}>Company Setup</div>
              <div style={{ fontSize: 13, color: '#8FA5BD', marginBottom: 24 }}>Let's get your account configured</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                {[
                  { label: 'Company Name', key: 'company' },
                  { label: 'GSTIN', key: 'gstin' },
                  { label: 'City', key: 'city' },
                  { label: 'Industry', key: 'industry' },
                ].map(function(f) {
                  return (
                    <div key={f.key} className="fg">
                      <label>{f.label}</label>
                      <input
                        value={form[f.key]}
                        onChange={function(e) { setForm({ ...form, [f.key]: e.target.value }) }}
                      />
                    </div>
                  )
                })}
                <div className="fg" style={{ gridColumn: '1 / -1' }}>
                  <label>Email</label>
                  <input value={form.email} onChange={function(e) { setForm({ ...form, email: e.target.value }) }} />
                </div>
              </div>
            </div>
          )}

          {/* Step 1: Connect Platforms */}
          {step === 1 && (
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 6 }}>Connect Platforms</div>
              <div style={{ fontSize: 13, color: '#8FA5BD', marginBottom: 24 }}>Link your marketplace accounts</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {platforms.map(function(p) {
                  return (
                    <div key={p.id} onClick={function() { togglePlatform(p.id) }} style={{
                      padding: '12px 14px', borderRadius: 10, cursor: 'pointer',
                      border: '1px solid ' + (p.connected ? '#0ABFCA' : '#E2EBF3'),
                      background: p.connected ? 'rgba(10,191,202,.06)' : '#fff',
                      display: 'flex', alignItems: 'center', gap: 10,
                      transition: 'all .15s',
                    }}>
                      <span style={{ fontSize: 20 }}>{p.icon}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{p.name}</span>
                      <span style={{
                        fontSize: 11, fontWeight: 700,
                        color: p.connected ? '#0DB07A' : '#8FA5BD',
                      }}>
                        {p.connected ? '✓ Connected' : 'Connect'}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Step 2: Test Connections */}
          {step === 2 && (
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 6 }}>Test Connections</div>
              <div style={{ fontSize: 13, color: '#8FA5BD', marginBottom: 24 }}>Verifying data access from connected platforms</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {TEST_RESULTS.map(function(t) {
                  return (
                    <div key={t.platform} style={{
                      display: 'flex', alignItems: 'center', gap: 14,
                      padding: '14px 18px', borderRadius: 12,
                      background: '#E6F7F2', border: '1px solid rgba(13,176,122,.25)',
                    }}>
                      <span style={{ fontSize: 22 }}>{t.icon}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, color: '#0D1F35' }}>{t.platform}</div>
                        <div style={{ fontSize: 12, color: '#4B6080' }}>
                          {t.orders} · {t.gmv}
                        </div>
                      </div>
                      <span style={{ fontSize: 18 }}>✅</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Step 3: Done */}
          {step === 3 && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: 56, marginBottom: 16 }}>🎉</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#0D1F35', marginBottom: 8 }}>
                You're all set!
              </div>
              <div style={{ fontSize: 14, color: '#4B6080', marginBottom: 28 }}>
                ClearSettle is ready to monitor your settlements
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginBottom: 32 }}>
                {[
                  { val: '3', label: 'Platforms Connected' },
                  { val: '₹36.4L', label: 'GMV Monitored' },
                  { val: '8,171', label: 'Orders Tracked' },
                ].map(function(stat) {
                  return (
                    <div key={stat.label} style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 24, fontWeight: 800, color: '#0ABFCA' }}>{stat.val}</div>
                      <div style={{ fontSize: 11, color: '#8FA5BD' }}>{stat.label}</div>
                    </div>
                  )
                })}
              </div>
              <button onClick={handleFinish} className="btn btn-p" style={{ fontSize: 15, padding: '12px 32px' }}>
                Go to Dashboard →
              </button>
            </div>
          )}

          {/* Navigation buttons */}
          {step < 3 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32 }}>
              <button
                onClick={function() { setStep(Math.max(0, step - 1)) }}
                className="btn btn-s"
                style={{ visibility: step === 0 ? 'hidden' : 'visible' }}
              >
                ← Back
              </button>
              <button
                onClick={function() { setStep(step + 1) }}
                className="btn btn-p"
              >
                {step === 2 ? 'Finish Setup' : 'Continue →'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Onboarding
