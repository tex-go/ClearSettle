import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../utils/api'
import useAuthStore from '../store/authStore'

// ── Constants ──────────────────────────────────────────────────────────────────

var STATES = [
  'Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh',
  'Goa','Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka',
  'Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram',
  'Nagaland','Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana',
  'Tripura','Uttar Pradesh','Uttarakhand','West Bengal',
  'Delhi','Jammu & Kashmir','Ladakh','Puducherry','Chandigarh',
  'Dadra and Nagar Haveli and Daman & Diu','Lakshadweep',
  'Andaman & Nicobar Islands',
]

var GSTIN_STATE_MAP = {
  '01':'Jammu & Kashmir','02':'Himachal Pradesh','03':'Punjab','04':'Chandigarh',
  '05':'Uttarakhand','06':'Haryana','07':'Delhi','08':'Rajasthan','09':'Uttar Pradesh',
  '10':'Bihar','11':'Sikkim','12':'Arunachal Pradesh','13':'Nagaland','14':'Manipur',
  '15':'Mizoram','16':'Tripura','17':'Meghalaya','18':'Assam','19':'West Bengal',
  '20':'Jharkhand','21':'Odisha','22':'Chhattisgarh','23':'Madhya Pradesh',
  '24':'Gujarat','26':'Dadra and Nagar Haveli and Daman & Diu','27':'Maharashtra',
  '29':'Karnataka','30':'Goa','32':'Kerala','33':'Tamil Nadu','34':'Puducherry',
  '36':'Telangana','37':'Andhra Pradesh','38':'Ladakh',
}

var INDUSTRIES = [
  'Textile & Apparel','Electronics & Gadgets','Home & Furniture',
  'Beauty & Personal Care','Food & Groceries','Books & Stationery',
  'Sports & Outdoors','Automotive','Toys & Baby Products',
  'Health & Wellness','Jewelry & Accessories','Other',
]

var GMV_RANGES = [
  '< ₹1 Lakh/month','₹1L – ₹5L/month','₹5L – ₹25L/month',
  '₹25L – ₹1 Cr/month','> ₹1 Cr/month',
]

var PLATFORMS = [
  { id: 'flipkart', label: 'Flipkart',   icon: '🛒' },
  { id: 'amazon',   label: 'Amazon',     icon: '📦' },
  { id: 'meesho',   label: 'Meesho',     icon: '🧵' },
  { id: 'myntra',   label: 'Myntra',     icon: '👗' },
  { id: 'ajio',     label: 'Ajio',       icon: '🎽' },
  { id: 'nykaa',    label: 'Nykaa',      icon: '💄' },
  { id: 'snapdeal', label: 'Snapdeal',   icon: '🔖' },
  { id: 'jiomart',  label: 'JioMart',    icon: '🏪' },
  { id: 'indiamart',label: 'IndiaMART',  icon: '🏭' },
  { id: 'other',    label: 'Other',      icon: '➕' },
]

var STEPS = [
  { num: 1, label: 'Your Account' },
  { num: 2, label: 'Business Profile' },
  { num: 3, label: 'Marketplaces' },
]

// ── Styles helpers ─────────────────────────────────────────────────────────────

var inputStyle = {
  padding: '11px 14px', borderRadius: 10,
  background: 'rgba(255,255,255,.07)',
  border: '1px solid rgba(255,255,255,.13)',
  color: '#fff', fontSize: 14, outline: 'none', width: '100%',
  boxSizing: 'border-box',
}
var labelStyle = { fontSize: 12, fontWeight: 600, color: '#8FA5BD', marginBottom: 5, display: 'block' }
var fieldWrap = { display: 'flex', flexDirection: 'column', marginBottom: 16 }

// ── Component ──────────────────────────────────────────────────────────────────

function Register() {
  var navigate = useNavigate()
  var loginStore = useAuthStore(function(s) { return s.login })

  var [step, setStep] = useState(1)
  var [loading, setLoading] = useState(false)
  var [error, setError] = useState('')

  // Step 1
  var [name, setName] = useState('')
  var [email, setEmail] = useState('')
  var [phone, setPhone] = useState('')
  var [password, setPassword] = useState('')
  var [confirmPassword, setConfirmPassword] = useState('')

  // Step 2
  var [companyName, setCompanyName] = useState('')
  var [gstin, setGstin] = useState('')
  var [pan, setPan] = useState('')
  var [state, setState] = useState('')
  var [city, setCity] = useState('')
  var [pincode, setPincode] = useState('')
  var [address, setAddress] = useState('')
  var [industry, setIndustry] = useState('')
  var [gmvRange, setGmvRange] = useState('')
  var [website, setWebsite] = useState('')

  // Step 3
  var [platforms, setPlatforms] = useState([])

  function togglePlatform(id) {
    setPlatforms(function(prev) {
      return prev.includes(id) ? prev.filter(function(p) { return p !== id }) : [...prev, id]
    })
  }

  function handleGstinChange(v) {
    var val = v.toUpperCase()
    setGstin(val)
    if (val.length >= 2) {
      var code = val.slice(0, 2)
      var mapped = GSTIN_STATE_MAP[code]
      if (mapped && !state) setState(mapped)
    }
  }

  function validateStep1() {
    if (!name.trim()) return 'Full name is required'
    if (!email.trim() || !email.includes('@')) return 'Valid email is required'
    if (!/^\+?[\d\s\-()]{10,}$/.test(phone)) return 'Valid 10-digit phone number is required'
    if (password.length < 8) return 'Password must be at least 8 characters'
    if (password !== confirmPassword) return 'Passwords do not match'
    return null
  }

  function validateStep2() {
    if (!companyName.trim()) return 'Company / business name is required'
    var gstinPat = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/
    if (!gstinPat.test(gstin.trim())) return 'Invalid GSTIN format (e.g. 33ABCDE1234F1Z5)'
    if (!state) return 'State is required'
    return null
  }

  function validateStep3() {
    if (platforms.length === 0) return 'Select at least one marketplace'
    return null
  }

  function nextStep() {
    setError('')
    var err = null
    if (step === 1) err = validateStep1()
    if (step === 2) err = validateStep2()
    if (err) { setError(err); return }
    setStep(function(s) { return s + 1 })
  }

  function prevStep() {
    setError('')
    setStep(function(s) { return s - 1 })
  }

  function handleSubmit(e) {
    e.preventDefault()
    var err = validateStep3()
    if (err) { setError(err); return }

    setLoading(true)
    setError('')

    api.post('/auth/register', {
      name: name.trim(),
      email: email.trim(),
      phone: phone.trim(),
      password: password,
      confirm_password: confirmPassword,
      company_name: companyName.trim(),
      gstin: gstin.trim().toUpperCase(),
      pan: pan.trim() || null,
      state: state,
      city: city.trim() || null,
      pincode: pincode.trim() || null,
      address: address.trim() || null,
      industry: industry || null,
      monthly_gmv_range: gmvRange || null,
      website: website.trim() || null,
      active_platforms: platforms,
    })
      .then(function(res) {
        loginStore(res.data.access_token, res.data.user)
        localStorage.setItem('cs_onboarded', 'true')
        navigate('/')
      })
      .catch(function(err) {
        var msg = err.response ? err.response.data.detail : 'Registration failed. Please try again.'
        if (Array.isArray(msg)) {
          setError(msg.map(function(m) { return m.msg }).join('; '))
        } else {
          setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
        }
        setLoading(false)
      })
  }

  return (
    <div style={{
      minHeight: '100vh', width: '100%',
      background: 'linear-gradient(135deg,#0D1F35 0%,#0A1628 50%,#061020 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '32px 16px', boxSizing: 'border-box',
    }}>
      {/* Orbs */}
      {[
        { w: 400, h: 400, top: '-10%', left: '-10%', c: 'rgba(10,191,202,.05)' },
        { w: 300, h: 300, bottom: '-5%', right: '5%',  c: 'rgba(123,82,232,.05)' },
      ].map(function(orb, i) {
        return (
          <div key={i} style={{
            position: 'fixed', borderRadius: '50%',
            width: orb.w, height: orb.h,
            background: orb.c,
            top: orb.top, left: orb.left, bottom: orb.bottom, right: orb.right,
            pointerEvents: 'none',
          }} />
        )
      })}

      <div style={{ width: '100%', maxWidth: 560, position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            fontSize: 26, fontWeight: 800,
            background: 'linear-gradient(135deg,#0ABFCA,#7FE4EC)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            marginBottom: 6,
          }}>
            ClearSettle
          </div>
          <div style={{ fontSize: 14, color: '#4B6080' }}>
            Detect settlement discrepancies. Recover what you're owed.
          </div>
        </div>

        {/* Step indicator */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0, marginBottom: 24 }}>
          {STEPS.map(function(s, i) {
            var done = step > s.num
            var active = step === s.num
            return (
              <React.Fragment key={s.num}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 700,
                    background: done ? '#0ABFCA' : active ? 'linear-gradient(135deg,#0ABFCA,#088F99)' : 'rgba(255,255,255,.1)',
                    color: done || active ? '#fff' : '#4B6080',
                    boxShadow: active ? '0 0 12px rgba(10,191,202,.4)' : 'none',
                    transition: 'all .3s',
                  }}>
                    {done ? '✓' : s.num}
                  </div>
                  <div style={{ fontSize: 10, color: active ? '#0ABFCA' : done ? '#4BB8A0' : '#4B6080', fontWeight: 600, whiteSpace: 'nowrap' }}>
                    {s.label}
                  </div>
                </div>
                {i < STEPS.length - 1 && (
                  <div style={{
                    height: 2, width: 80, margin: '0 6px', marginBottom: 16,
                    background: done ? '#0ABFCA' : 'rgba(255,255,255,.08)',
                    transition: 'background .3s',
                  }} />
                )}
              </React.Fragment>
            )
          })}
        </div>

        {/* Card */}
        <div style={{
          background: 'rgba(255,255,255,.04)',
          border: '1px solid rgba(255,255,255,.1)',
          borderRadius: 16, padding: '28px 32px',
          backdropFilter: 'blur(10px)',
        }}>
          {error && (
            <div style={{
              background: 'rgba(232,52,74,.15)', border: '1px solid rgba(232,52,74,.3)',
              borderRadius: 10, padding: '10px 14px',
              color: '#F87171', fontSize: 13, marginBottom: 20,
            }}>
              {error}
            </div>
          )}

          {/* ── Step 1: Account ─────────────────────────────────────────────── */}
          {step === 1 && (
            <div>
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 17, fontWeight: 800, color: '#E2EBF3' }}>Create your account</div>
                <div style={{ fontSize: 13, color: '#4B6080', marginTop: 4 }}>Start your free seller account</div>
              </div>
              <div style={fieldWrap}>
                <label style={labelStyle}>Full Name *</label>
                <input style={inputStyle} type="text" placeholder="Ranjith Kumar" value={name} onChange={function(e) { setName(e.target.value) }} />
              </div>
              <div className="form-grid-2">
                <div style={fieldWrap}>
                  <label style={labelStyle}>Email Address *</label>
                  <input style={inputStyle} type="email" placeholder="you@company.com" value={email} onChange={function(e) { setEmail(e.target.value) }} />
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>Phone Number *</label>
                  <input style={inputStyle} type="tel" placeholder="+91 98765 43210" value={phone} onChange={function(e) { setPhone(e.target.value) }} />
                </div>
              </div>
              <div className="form-grid-2">
                <div style={fieldWrap}>
                  <label style={labelStyle}>Password *</label>
                  <input style={inputStyle} type="password" placeholder="Min. 8 characters" value={password} onChange={function(e) { setPassword(e.target.value) }} />
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>Confirm Password *</label>
                  <input style={inputStyle} type="password" placeholder="Repeat password" value={confirmPassword} onChange={function(e) { setConfirmPassword(e.target.value) }} />
                </div>
              </div>
            </div>
          )}

          {/* ── Step 2: Business Profile ────────────────────────────────────── */}
          {step === 2 && (
            <div>
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 17, fontWeight: 800, color: '#E2EBF3' }}>Business Profile</div>
                <div style={{ fontSize: 13, color: '#4B6080', marginTop: 4 }}>GSTIN is required for reconciliation accuracy</div>
              </div>
              <div className="form-grid-2">
                <div style={{ ...fieldWrap, gridColumn: '1 / -1' }}>
                  <label style={labelStyle}>Business / Company Name *</label>
                  <input style={inputStyle} type="text" placeholder="Tirupur Exports Pvt. Ltd." value={companyName} onChange={function(e) { setCompanyName(e.target.value) }} />
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>GSTIN *</label>
                  <input style={{ ...inputStyle, fontFamily: 'monospace', letterSpacing: '.05em' }} type="text" placeholder="33ABCDE1234F1Z5" maxLength={15} value={gstin} onChange={function(e) { handleGstinChange(e.target.value) }} />
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>PAN <span style={{ opacity: .6 }}>(optional)</span></label>
                  <input style={{ ...inputStyle, fontFamily: 'monospace' }} type="text" placeholder="ABCDE1234F" maxLength={10} value={pan} onChange={function(e) { setPan(e.target.value.toUpperCase()) }} />
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>State *</label>
                  <select style={{ ...inputStyle, appearance: 'none' }} value={state} onChange={function(e) { setState(e.target.value) }}>
                    <option value="" style={{ background: '#0D1F35' }}>Select state</option>
                    {STATES.map(function(s) { return <option key={s} value={s} style={{ background: '#0D1F35' }}>{s}</option> })}
                  </select>
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>City <span style={{ opacity: .6 }}>(optional)</span></label>
                  <input style={inputStyle} type="text" placeholder="Tirupur" value={city} onChange={function(e) { setCity(e.target.value) }} />
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>PIN Code <span style={{ opacity: .6 }}>(optional)</span></label>
                  <input style={inputStyle} type="text" placeholder="641604" maxLength={6} value={pincode} onChange={function(e) { setPincode(e.target.value.replace(/\D/g, '')) }} />
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>Industry</label>
                  <select style={{ ...inputStyle, appearance: 'none' }} value={industry} onChange={function(e) { setIndustry(e.target.value) }}>
                    <option value="" style={{ background: '#0D1F35' }}>Select industry</option>
                    {INDUSTRIES.map(function(ind) { return <option key={ind} value={ind} style={{ background: '#0D1F35' }}>{ind}</option> })}
                  </select>
                </div>
                <div style={fieldWrap}>
                  <label style={labelStyle}>Monthly GMV Range</label>
                  <select style={{ ...inputStyle, appearance: 'none' }} value={gmvRange} onChange={function(e) { setGmvRange(e.target.value) }}>
                    <option value="" style={{ background: '#0D1F35' }}>Select range</option>
                    {GMV_RANGES.map(function(r) { return <option key={r} value={r} style={{ background: '#0D1F35' }}>{r}</option> })}
                  </select>
                </div>
                <div style={{ ...fieldWrap, gridColumn: '1 / -1' }}>
                  <label style={labelStyle}>Business Address <span style={{ opacity: .6 }}>(optional)</span></label>
                  <textarea style={{ ...inputStyle, resize: 'vertical', minHeight: 64 }} placeholder="Street, area, landmark..." value={address} onChange={function(e) { setAddress(e.target.value) }} />
                </div>
                <div style={{ ...fieldWrap, gridColumn: '1 / -1' }}>
                  <label style={labelStyle}>Website <span style={{ opacity: .6 }}>(optional)</span></label>
                  <input style={inputStyle} type="url" placeholder="https://yourstore.com" value={website} onChange={function(e) { setWebsite(e.target.value) }} />
                </div>
              </div>
            </div>
          )}

          {/* ── Step 3: Marketplace Selection ───────────────────────────────── */}
          {step === 3 && (
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 17, fontWeight: 800, color: '#E2EBF3' }}>Your Marketplaces</div>
                <div style={{ fontSize: 13, color: '#4B6080', marginTop: 4 }}>
                  Select all platforms where you sell — we'll tailor reconciliation for each
                </div>
              </div>
              <div className="platform-grid">
                {PLATFORMS.map(function(p) {
                  var selected = platforms.includes(p.id)
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={function() { togglePlatform(p.id) }}
                      style={{
                        padding: '12px 16px',
                        borderRadius: 10,
                        background: selected ? 'rgba(10,191,202,.15)' : 'rgba(255,255,255,.05)',
                        border: selected ? '1px solid #0ABFCA' : '1px solid rgba(255,255,255,.1)',
                        color: selected ? '#0ABFCA' : '#8FA5BD',
                        fontSize: 13, fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: 10,
                        transition: 'all .15s',
                        boxShadow: selected ? '0 0 10px rgba(10,191,202,.15)' : 'none',
                      }}
                    >
                      <span style={{ fontSize: 18 }}>{p.icon}</span>
                      {p.label}
                      {selected && <span style={{ marginLeft: 'auto', fontSize: 15 }}>✓</span>}
                    </button>
                  )
                })}
              </div>

              {/* Disclaimer */}
              <div style={{
                background: 'rgba(10,191,202,.06)', border: '1px solid rgba(10,191,202,.15)',
                borderRadius: 10, padding: '10px 14px', marginBottom: 20,
              }}>
                <div style={{ fontSize: 11, color: '#4B6080', lineHeight: 1.6 }}>
                  <span style={{ color: '#0ABFCA', fontWeight: 700 }}>Note: </span>
                  ClearSettle analyses your uploaded reports to surface <em>potential</em> settlement discrepancies.
                  All figures shown are estimated anomalies and should be verified before raising disputes.
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || platforms.length === 0}
                style={{
                  width: '100%', padding: '13px',
                  borderRadius: 10,
                  background: loading || platforms.length === 0
                    ? 'rgba(10,191,202,.3)'
                    : 'linear-gradient(135deg,#0ABFCA,#088F99)',
                  color: '#fff', fontSize: 14, fontWeight: 700,
                  cursor: loading || platforms.length === 0 ? 'not-allowed' : 'pointer',
                  border: 'none',
                }}
              >
                {loading ? 'Creating your account...' : 'Create Account & Get Started →'}
              </button>
            </form>
          )}

          {/* Navigation */}
          {step < 3 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 20 }}>
              {step > 1 ? (
                <button onClick={prevStep} style={{
                  padding: '10px 20px', borderRadius: 8,
                  background: 'rgba(255,255,255,.07)', border: '1px solid rgba(255,255,255,.12)',
                  color: '#8FA5BD', fontSize: 13, cursor: 'pointer',
                }}>← Back</button>
              ) : <div />}
              <button onClick={nextStep} style={{
                padding: '10px 24px', borderRadius: 8,
                background: 'linear-gradient(135deg,#0ABFCA,#088F99)',
                border: 'none', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer',
              }}>
                Continue →
              </button>
            </div>
          )}

          {step > 1 && step === 3 && (
            <div style={{ textAlign: 'center', marginTop: 12 }}>
              <button onClick={prevStep} style={{
                background: 'none', border: 'none',
                color: '#4B6080', fontSize: 12, cursor: 'pointer',
              }}>← Back to business profile</button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#4B6080' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: '#0ABFCA', fontWeight: 700, textDecoration: 'none' }}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}

export default Register
