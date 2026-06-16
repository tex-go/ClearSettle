import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import usePermissions from '../../hooks/usePermissions'

// All nav items with permission gates
// permission: single permission required
// anyOf: any of these permissions grants access
var ALL_NAV = [
  {
    group: 'Overview',
    items: [
      { path: '/', label: 'Dashboard', icon: '⚡', permission: 'dashboard.view' },
    ],
  },
  {
    group: 'Finance',
    items: [
      { path: '/payment-reconciliation', label: 'Payment Reconciliation', icon: '💳', permission: 'settlements.view' },
      { path: '/returns',      label: 'Returns',          icon: '↩️', permission: 'settlements.view' },
      { path: '/commission',   label: 'Commission Audit', icon: '🔍', badge: 2, bc: 'am', permission: 'reconciliation.view' },
      { path: '/gst',          label: 'GST / TCS',        icon: '🧾', permission: 'gst.view' },
    ],
  },
  {
    group: 'Operations',
    items: [
      { path: '/inventory', label: 'Inventory Sync',  icon: '📦', badge: 3, bc: 'am', permission: 'reports.view' },
      { path: '/analytics', label: 'Analytics',       icon: '💰', badge: 'NEW', bc: 'tl', permission: 'dashboard.view' },
    ],
  },
  {
    group: 'Reconciliation',
    items: [
      { path: '/ingestion',    label: 'Upload Center',       icon: '📥', badge: 'NEW', bc: 'tl', permission: 'reports.upload' },
      { path: '/recon-engine', label: 'Recon Engine',        icon: '🔬', permission: 'reconciliation.view' },
      { path: '/bank',         label: 'Bank Reconciliation', icon: '🏦', badge: 2, bc: 'am', permission: 'bank_reconciliation.view' },
    ],
  },
  {
    group: 'Marketplace',
    items: [
      { path: '/platforms', label: 'Platform Settings', icon: '⚙️', permission: 'marketplace.view' },
    ],
  },
  {
    group: 'Intelligence',
    items: [
      { path: '/recovery-center',  label: 'Recovery Center',    icon: '🛡️', badge: 3, bc: 'rd', permission: 'disputes.view' },
      { path: '/rules',            label: 'Rule Manager',       icon: '⚙️', permission: 'reconciliation.view' },
      { path: '/competitors',      label: 'Market Intelligence', icon: '🔭', permission: 'ai.view' },
      { path: '/seller-discovery', label: 'Seller Discovery',   icon: '🧲', badge: 'NEW', bc: 'tl', permission: 'users.view' },
      { path: '/meetings',         label: 'Meeting Calendar',   icon: '📆', permission: 'dashboard.view' },
    ],
  },
  {
    group: 'Reports',
    items: [
      { path: '/reports', label: 'Reports', icon: '📊', permission: 'reports.view' },
    ],
  },
  {
    group: 'Admin',
    items: [
      { path: '/admin', label: 'Admin Panel', icon: '🛡️', badge: 'ADMIN', bc: 'rd', anyOf: ['users.create', 'roles.assign'] },
    ],
  },
]

var badgeColors = {
  rd: { bg: 'rgba(232,52,74,.18)',  color: '#E8344A' },
  am: { bg: 'rgba(233,147,13,.18)', color: '#E9930D' },
  tl: { bg: 'rgba(10,191,202,.18)', color: '#0ABFCA' },
}

function Sidebar({ open, onClose }) {
  var { user, logout } = useAuthStore()
  var navigate = useNavigate()
  var { can, canAny } = usePermissions()

  var initials = user && user.name ? user.name.split(' ').map(function(n) { return n[0] }).slice(0,2).join('') : 'U'

  function isVisible(item) {
    if (item.anyOf) return canAny(item.anyOf)
    if (item.permission) return can(item.permission)
    return true
  }

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside
      className={'sidebar' + (open ? ' open' : '')}
      aria-label="Primary navigation"
      style={{
        width: 'var(--sidebar-w)',
        minHeight: '100vh',
        background: '#0D1F35',
        display: 'flex',
        flexDirection: 'column',
        position: 'sticky',
        top: 0,
        height: '100vh',
        flexShrink: 0,
        overflowY: 'auto',
        overflowX: 'hidden',
      }}
    >
      {/* ── Logo row ── */}
      <div style={{
        padding: '20px 16px 14px',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <div>
          <div style={{
            fontSize: 20,
            fontWeight: 800,
            background: 'linear-gradient(135deg,#0ABFCA,#7FE4EC)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            lineHeight: 1.2,
          }}>
            ClearSettle
          </div>
          <div style={{
            fontSize: 9,
            color: '#4B6080',
            fontWeight: 700,
            letterSpacing: '.07em',
            marginTop: 3,
            textTransform: 'uppercase',
          }}>
            Unified eCommerce Intelligence
          </div>
        </div>

        {/* Close button — mobile only */}
        <button
          className="mob-show"
          onClick={onClose}
          aria-label="Close navigation"
          style={{
            display: 'none',
            alignItems: 'center',
            justifyContent: 'center',
            width: 32,
            height: 32,
            borderRadius: 8,
            flexShrink: 0,
            background: 'rgba(255,255,255,.1)',
            color: '#8FA5BD',
            fontSize: 16,
            cursor: 'pointer',
            border: 'none',
          }}
        >
          ✕
        </button>
      </div>

      {/* ── Company card ── */}
      <div style={{
        margin: '0 10px 12px',
        background: 'rgba(255,255,255,.05)',
        border: '1px solid rgba(255,255,255,.08)',
        borderRadius: 10,
        padding: '10px 12px',
        flexShrink: 0,
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#E2EBF3', lineHeight: 1.3 }}>
          {user ? user.company || 'Your Company' : 'Company Name'}
        </div>
        <div style={{ fontSize: 11, color: '#4B6080', marginTop: 2 }}>
          {user ? (user.city || user.state || '') : ''}
        </div>
      </div>

      {/* ── Navigation ── */}
      <nav style={{ flex: 1, padding: '0 6px', overflowY: 'auto' }} role="navigation">
        {ALL_NAV.map(function(group) {
          var visibleItems = group.items.filter(isVisible)
          if (visibleItems.length === 0) return null
          return (
            <div key={group.group} style={{ marginBottom: 4 }}>
              <div style={{
                fontSize: 9,
                fontWeight: 800,
                letterSpacing: '.1em',
                color: '#2D4A6B',
                padding: '10px 10px 4px',
                textTransform: 'uppercase',
              }}>
                {group.group}
              </div>
              {visibleItems.map(function(item) {
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    onClick={onClose}
                    aria-label={item.label}
                    style={function({ isActive }) {
                      return {
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '9px 10px',
                        borderRadius: 8,
                        fontSize: 13,
                        fontWeight: 500,
                        color: isActive ? '#0ABFCA' : '#8FA5BD',
                        background: isActive ? 'rgba(10,191,202,.14)' : 'transparent',
                        borderLeft: isActive ? '3px solid #0ABFCA' : '3px solid transparent',
                        textDecoration: 'none',
                        transition: 'all .15s',
                        marginBottom: 1,
                        /* Ensure touch target */
                        minHeight: 40,
                      }
                    }}
                  >
                    <span style={{ fontSize: 15, flexShrink: 0, lineHeight: 1 }}>{item.icon}</span>
                    <span style={{ flex: 1, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.label}
                    </span>
                    {item.badge !== undefined && (
                      <span style={{
                        ...(badgeColors[item.bc || 'rd']),
                        borderRadius: 10,
                        padding: '1px 7px',
                        fontSize: 10,
                        fontWeight: 700,
                        flexShrink: 0,
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

      {/* ── User footer ── */}
      <div style={{
        padding: '10px 10px 14px',
        borderTop: '1px solid rgba(255,255,255,.06)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <div style={{
            width: 34,
            height: 34,
            borderRadius: '50%',
            background: 'linear-gradient(135deg,#0ABFCA,#088F99)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 13,
            fontWeight: 800,
            color: '#fff',
            flexShrink: 0,
            letterSpacing: '-.5px',
          }}>
            {initials}
          </div>
          <div style={{ overflow: 'hidden', flex: 1 }}>
            <div style={{
              fontSize: 12,
              fontWeight: 700,
              color: '#E2EBF3',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {user ? user.name : 'User'}
            </div>
            <div style={{ fontSize: 10, color: '#4B6080', textTransform: 'capitalize' }}>
              {user ? user.role : 'member'}
            </div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          style={{
            width: '100%',
            padding: '8px',
            minHeight: 36,
            borderRadius: 8,
            background: 'rgba(232,52,74,.1)',
            color: '#E8344A',
            fontSize: 12,
            fontWeight: 600,
            cursor: 'pointer',
            border: '1px solid rgba(232,52,74,.2)',
            transition: 'background .15s',
          }}
        >
          Sign Out
        </button>
      </div>
    </aside>
  )
}

export default Sidebar
