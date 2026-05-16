import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../utils/api'
import useAuthStore from '../store/authStore'

var FEATURES = [
  { icon: '⚖️', text: 'AI-powered dispute engine with auto-raise' },
  { icon: '🏦', text: 'Bank reconciliation across 8 platforms' },
  { icon: '📅', text: '30-day cash flow forecast calendar' },
  { icon: '🔍', text: 'Commission overcharge audit & recovery' },
  { icon: '🧾', text: 'GST/TCS auto-reconciliation' },
  { icon: '💰', text: 'SKU-level profitability analysis' },
]

function Login() {
  var navigate = useNavigate()
  var login = useAuthStore(function(s) { return s.login })
  var [email, setEmail] = useState('')
  var [password, setPassword] = useState('')
  var [loading, setLoading] = useState(false)
  var [error, setError] = useState('')

  function fillDemo() {
    setEmail('demo@clearsettle.in')
    setPassword('demo123')
    setError('')
  }

  function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    api.post('/auth/login', { email: email, password: password })
      .then(function(res) {
        login(res.data.access_token, res.data.user)
        navigate('/onboarding')
      })
      .catch(function(err) {
        setError(err.response ? err.response.data.detail : 'Login failed. Check backend is running.')
        setLoading(false)
      })
  }

  return (
    <div style={{
      minHeight: '100vh', width: '100%',
      background: 'linear-gradient(135deg,#0D1F35 0%,#0A1628 50%,#061020 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Animated orbs */}
      {[
        { w: 400, h: 400, top: '-10%', left: '-10%', c: 'rgba(10,191,202,.06)' },
        { w: 300, h: 300, bottom: '-5%', right: '5%', c: 'rgba(123,82,232,.06)' },
        { w: 200, h: 200, top: '40%', left: '45%', c: 'rgba(10,191,202,.04)' },
      ].map(function(orb, i) {
        return (
          <div key={i} style={{
            position: 'absolute', borderRadius: '50%',
            width: orb.w, height: orb.h,
            background: orb.c,
            top: orb.top, left: orb.left, bottom: orb.bottom, right: orb.right,
            animation: 'pulse ' + (4 + i) + 's ease-in-out infinite',
            animationDelay: i + 's',
          }} />
        )
      })}

      <div style={{
        display: 'flex', alignItems: 'center', gap: 80,
        maxWidth: 960, width: '100%', padding: '0 40px',
        position: 'relative', zIndex: 1,
      }}>
        {/* Left branding */}
        <div style={{ flex: 1, color: '#fff' }}>
          <div style={{
            fontSize: 36, fontWeight: 800,
            background: 'linear-gradient(135deg,#0ABFCA,#7FE4EC)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            marginBottom: 8,
          }}>
            ClearSettle
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 12, color: '#E2EBF3' }}>
            Recover every rupee you're owed
          </div>
          <div style={{ fontSize: 14, color: '#4B6080', marginBottom: 32, lineHeight: 1.6 }}>
            The only reconciliation platform built specifically for Tirupur textile sellers on Indian marketplaces.
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {FEATURES.map(function(f, i) {
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{
                    width: 32, height: 32, borderRadius: 8,
                    background: 'rgba(10,191,202,.12)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 15, flexShrink: 0,
                  }}>{f.icon}</span>
                  <span style={{ fontSize: 13, color: '#8FA5BD' }}>{f.text}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Right form card */}
        <div style={{
          width: 380, flexShrink: 0,
          background: 'rgba(255,255,255,.05)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,.1)',
          borderRadius: 20, padding: 36,
        }}>
          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#fff', marginBottom: 6 }}>
              Sign in to ClearSettle
            </div>
            <div style={{ fontSize: 13, color: '#4B6080' }}>
              Manage your eCommerce settlements
            </div>
          </div>

          {error && (
            <div style={{
              background: 'rgba(232,52,74,.15)', border: '1px solid rgba(232,52,74,.3)',
              borderRadius: 10, padding: '10px 14px',
              color: '#F87171', fontSize: 13, marginBottom: 16,
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#8FA5BD' }}>Email address</label>
              <input
                type="email"
                value={email}
                onChange={function(e) { setEmail(e.target.value) }}
                placeholder="demo@clearsettle.in"
                required
                style={{
                  padding: '11px 14px', borderRadius: 10,
                  background: 'rgba(255,255,255,.07)',
                  border: '1px solid rgba(255,255,255,.12)',
                  color: '#fff', fontSize: 14, outline: 'none',
                }}
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#8FA5BD' }}>Password</label>
              <input
                type="password"
                value={password}
                onChange={function(e) { setPassword(e.target.value) }}
                placeholder="••••••••"
                required
                style={{
                  padding: '11px 14px', borderRadius: 10,
                  background: 'rgba(255,255,255,.07)',
                  border: '1px solid rgba(255,255,255,.12)',
                  color: '#fff', fontSize: 14, outline: 'none',
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '12px', borderRadius: 10,
                background: loading ? 'rgba(10,191,202,.5)' : 'linear-gradient(135deg,#0ABFCA,#088F99)',
                color: '#fff', fontSize: 14, fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer', border: 'none',
                marginTop: 4,
              }}
            >
              {loading ? 'Signing in...' : 'Sign In →'}
            </button>
          </form>

          <div
            onClick={fillDemo}
            style={{
              marginTop: 20, padding: '10px 14px', borderRadius: 10,
              background: 'rgba(10,191,202,.08)',
              border: '1px solid rgba(10,191,202,.2)',
              cursor: 'pointer', textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, color: '#0ABFCA', marginBottom: 4 }}>
              DEMO CREDENTIALS (click to fill)
            </div>
            <div style={{ fontSize: 12, color: '#4B6080', fontFamily: 'JetBrains Mono, monospace' }}>
              demo@clearsettle.in / demo123
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login
