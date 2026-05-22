import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

// Full nav for admin/demo users
var NAV_ADMIN = [
  {
    group: 'Overview',
    items: [
      { path: '/', label: 'Dashboard', icon: '⚡' },
    ],
  },
  {
    group: 'Finance',
    items: [
      { path: '/settlements', label: 'Settlements', icon: '💳', badge: 3, bc: 'rd' },
      { path: '/disputes', label: 'Disputes', icon: '⚖️', badge: 1, bc: 'am' },
      { path: '/returns', label: 'Returns', icon: '↩️' },
      { path: '/commission', label: 'Commission Audit', icon: '🔍', badge: 2, bc: 'am' },
      { path: '/gst', label: 'GST / TCS', icon: '🧾' },
    ],
  },
  {
    group: 'Operations',
    items: [
      { path: '/inventory', label: 'Inventory Sync', icon: '📦', badge: 3, bc: 'am' },
      { path: '/cashflow', label: 'Cash Flow', icon: '📅' },
      { path: '/forecast', label: 'Cash Flow Forecast', icon: '📈', badge: 'NEW', bc: 'tl' },
      { path: '/analytics', label: 'Profitability', icon: '💰' },
    ],
  },
  {
    group: 'Reconciliation',
    items: [
      { path: '/recon-engine', label: 'Recon Engine', icon: '🔬', badge: 'NEW', bc: 'tl' },
      { path: '/bank', label: 'Bank Reconciliation', icon: '🏦', badge: 2, bc: 'am' },
    ],
  },
  {
    group: 'Marketplaces',
    items: [
      { path: '/flipkart', label: 'Flipkart Intelligence', icon: '🛒', badge: 'NEW', bc: 'tl' },
    ],
  },
  {
    group: 'Intelligence',
    items: [
      { path: '/dispute-engine', label: 'Dispute Rule Engine', icon: '🤖', badge: 8, bc: 'tl' },
      { path: '/rules', label: 'Rule Manager', icon: '⚙️' },
      { path: '/recovery', label: 'Recovery Tracker', icon: '🎯', badge: 3, bc: 'rd' },
      { path: '/competitors', label: 'Market Intelligence', icon: '🔭' },
      { path: '/seller-discovery', label: 'Seller Discovery', icon: '🧲', badge: 'NEW', bc: 'tl' },
      { path: '/meetings', label: 'Meeting Calendar', icon: '📆' },
    ],
  },
  {
    group: 'Account',
    items: [
      { path: '/platforms', label: 'Platform Settings', icon: '⚙️' },
      { path: '/reports', label: 'Reports', icon: '📊' },
    ],
  },
  {
    group: 'Admin',
    items: [
      { path: '/admin', label: 'Admin Panel', icon: '🛡️', badge: 'ADMIN', bc: 'rd' },
    ],
  },
]

// Minimal nav for public sellers
var NAV_SELLER = [
  {
    group: 'Overview',
    items: [
      { path: '/', label: 'Dashboard', icon: '⚡' },
    ],
  },
  {
    group: 'Marketplaces',
    items: [
      { path: '/flipkart', label: 'Flipkart Intelligence', icon: '🛒', badge: 'NEW', bc: 'tl' },
    ],
  },
  {
    group: 'Reconciliation',
    items: [
      { path: '/recon-engine', label: 'Recon Engine', icon: '🔬' },
    ],
  },
  {
    group: 'Finance',
    items: [
      { path: '/settlements', label: 'Settlements', icon: '💳' },
      { path: '/returns', label: 'Returns', icon: '↩️' },
      { path: '/gst', label: 'GST / TCS', icon: '🧾' },
    ],
  },
  {
    group: 'Account',
    items: [
      { path: '/platforms', label: 'Platform Settings', icon: '⚙️' },
    ],
  },
]

var badgeColors = {
  rd: { bg: 'rgba(232,52,74,.18)', color: '#E8344A' },
  am: { bg: 'rgba(233,147,13,.18)', color: '#E9930D' },
  tl: { bg: 'rgba(10,191,202,.18)', color: '#0ABFCA' },
}

function Sidebar({ open, onClose }) {
  var { user, logout } = useAuthStore()
  var navigate = useNavigate()

  var role = user && user.role
  var isSeller = role === 'seller'
  var NAV = isSeller ? NAV_SELLER : NAV_ADMIN

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className={'sidebar' + (open ? ' open' : '')} style={{
      width: 244, minHeight: '100vh', background: '#0D1F35',
      display: 'flex', flexDirection: 'column',
      position: 'sticky', top: 0, height: '100vh', flexShrink: 0,
      overflowY: 'auto',
    }}>
      {/* Logo row — close button visible on mobile only */}
      <div style={{ padding: '22px 20px 16px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{
            fontSize: 20, fontWeight: 800,
            background: 'linear-gradient(135deg,#0ABFCA,#7FE4EC)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            ClearSettle
          </div>
          <div style={{ fontSize: 10, color: '#4B6080', fontWeight: 600, letterSpacing: '.06em', marginTop: 2 }}>
            UNIFIED eCOMMERCE INTELLIGENCE
          </div>
        </div>
        <button
          className="mob-show"
          onClick={onClose}
          style={{
            display: 'none', alignItems: 'center', justifyContent: 'center',
            width: 28, height: 28, borderRadius: 6, flexShrink: 0,
            background: 'rgba(255,255,255,.08)', color: '#8FA5BD', fontSize: 16,
          }}
        >✕</button>
      </div>
      {/* Company card */}
      <div style={{
        margin: '0 12px 16px',
        background: 'rgba(255,255,255,.05)',
        border: '1px solid rgba(255,255,255,.08)',
        borderRadius: 10, padding: '10px 12px',
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#E2EBF3' }}>
          {user ? user.company : 'Tirupur Exports Pvt. Ltd.'}
        </div>
        <div style={{ fontSize: 11, color: '#4B6080', marginTop: 2 }}>
          {user ? user.city : 'Tirupur, Tamil Nadu'}
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '0 8px' }}>
        {NAV.map(function(group) {
          return (
            <div key={group.group} style={{ marginBottom: 8 }}>
              <div style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '.08em',
                color: '#2D4A6B', padding: '8px 12px 4px',
                textTransform: 'uppercase',
              }}>
                {group.group}
              </div>
              {group.items.map(function(item) {
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    style={function({ isActive }) {
                      return {
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '8px 12px', borderRadius: 8,
                        fontSize: 13, fontWeight: 500,
                        color: isActive ? '#0ABFCA' : '#8FA5BD',
                        background: isActive ? 'rgba(10,191,202,.14)' : 'transparent',
                        borderLeft: isActive ? '3px solid #0ABFCA' : '3px solid transparent',
                        textDecoration: 'none',
                        transition: 'all .15s',
                        marginBottom: 2,
                      }
                    }}
                  >
                    <span style={{ fontSize: 15, flexShrink: 0 }}>{item.icon}</span>
                    <span style={{ flex: 1 }}>{item.label}</span>
                    {item.badge && (
                      <span style={{
                        ...badgeColors[item.bc || 'rd'],
                        borderRadius: 10, padding: '1px 7px',
                        fontSize: 10, fontWeight: 700,
                      }}>
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                )
              })}
            </div>
          )
        })}
      </nav>

      {/* User footer */}
      <div style={{
        padding: '12px 12px 16px',
        borderTop: '1px solid rgba(255,255,255,.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'linear-gradient(135deg,#0ABFCA,#088F99)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 700, color: '#fff', flexShrink: 0,
          }}>
            {user ? user.name[0] : 'R'}
          </div>
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#E2EBF3', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {user ? user.name : 'Ranjith Kumar'}
            </div>
            <div style={{ fontSize: 10, color: '#4B6080' }}>
              {user ? user.role : 'admin'}
            </div>
          </div>
        </div>
        <button onClick={handleLogout} style={{
          width: '100%', padding: '7px', borderRadius: 8,
          background: 'rgba(232,52,74,.12)', color: '#E8344A',
          fontSize: 12, fontWeight: 600, cursor: 'pointer',
          border: '1px solid rgba(232,52,74,.2)',
        }}>
          Sign Out
        </button>
      </div>
    </div>
  )
}

export default Sidebar
