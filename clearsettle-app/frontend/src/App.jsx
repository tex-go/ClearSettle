import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import useAuthStore from './store/authStore'
import { ToastContainer } from './components/ui/Toast'
import Sidebar from './components/layout/Sidebar'
import Topbar from './components/layout/Topbar'

import Login from './pages/Login'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import Settlements from './pages/Settlements'
import BankRecon from './pages/BankRecon'
import Disputes from './pages/Disputes'
import Returns from './pages/Returns'
import Commission from './pages/Commission'
import GST from './pages/GST'
import Inventory from './pages/Inventory'
import Analytics from './pages/Analytics'
import Platforms from './pages/Platforms'
import Reports from './pages/Reports'
import DisputeEngine from './pages/DisputeEngine'
import Recovery from './pages/Recovery'
import Competitors from './pages/Competitors'
import Rules from './pages/Rules'
import ReconEngine from './pages/ReconEngine'
import SellerDiscovery from './pages/SellerDiscovery'
import CashFlowForecast from './pages/CashFlowForecast'
import MeetingCalendar from './pages/MeetingCalendar'
import Register from './pages/Register'
import AdminPanel from './pages/AdminPanel'

function ProtectedRoute({ children, adminOnly }) {
  var isAuth = useAuthStore(function(s) { return s.isAuth })
  var user = useAuthStore(function(s) { return s.user })
  var onboarded = localStorage.getItem('cs_onboarded')
  var location = useLocation()

  if (!isAuth) return <Navigate to="/login" replace />

  var role = user && user.role
  var isAdmin = role === 'admin' || role === 'superadmin'

  if (adminOnly && !isAdmin) return <Navigate to="/" replace />

  if (!isAdmin && role !== 'seller' && !onboarded && location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />
  }
  return children
}

function AppLayout({ children }) {
  var [sidebarOpen, setSidebarOpen] = useState(false)
  var location = useLocation()

  // Close sidebar on route change
  useEffect(function() { setSidebarOpen(false) }, [location.pathname])

  // Body scroll lock when mobile sidebar is open
  useEffect(function() {
    if (sidebarOpen) {
      // Save scroll position and lock body
      var scrollY = window.scrollY
      document.body.classList.add('sidebar-open')
      document.body.style.top = '-' + scrollY + 'px'
      return function() {
        document.body.classList.remove('sidebar-open')
        document.body.style.top = ''
        window.scrollTo(0, scrollY)
      }
    }
  }, [sidebarOpen])

  return (
    <div style={{
      display: 'flex',
      height: '100%',
      width: '100%',
      background: 'var(--sf2)',
      overflow: 'hidden',
    }}>
      <div
        className={'sidebar-overlay' + (sidebarOpen ? ' open' : '')}
        onClick={function() { setSidebarOpen(false) }}
        aria-hidden="true"
      />
      <Sidebar open={sidebarOpen} onClose={function() { setSidebarOpen(false) }} />
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        minWidth: 0,
      }}>
        <Topbar onMenuClick={function() { setSidebarOpen(true) }} />
        <main
          style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}
          id="main-content"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        <Route path="/login"      element={<Login />} />
        <Route path="/register"   element={<Register />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/admin"      element={<ProtectedRoute adminOnly><AppLayout><AdminPanel /></AppLayout></ProtectedRoute>} />
        <Route path="/"           element={<ProtectedRoute><AppLayout><Dashboard /></AppLayout></ProtectedRoute>} />
        <Route path="/settlements" element={<ProtectedRoute><AppLayout><Settlements /></AppLayout></ProtectedRoute>} />
        <Route path="/bank"        element={<ProtectedRoute><AppLayout><BankRecon /></AppLayout></ProtectedRoute>} />
        <Route path="/disputes"    element={<ProtectedRoute><AppLayout><Disputes /></AppLayout></ProtectedRoute>} />
        <Route path="/returns"     element={<ProtectedRoute><AppLayout><Returns /></AppLayout></ProtectedRoute>} />
        <Route path="/commission"  element={<ProtectedRoute><AppLayout><Commission /></AppLayout></ProtectedRoute>} />
        <Route path="/gst"         element={<ProtectedRoute><AppLayout><GST /></AppLayout></ProtectedRoute>} />
        <Route path="/inventory"   element={<ProtectedRoute><AppLayout><Inventory /></AppLayout></ProtectedRoute>} />
        <Route path="/cashflow"    element={<Navigate to="/forecast" replace />} />
        <Route path="/analytics"   element={<ProtectedRoute><AppLayout><Analytics /></AppLayout></ProtectedRoute>} />
        <Route path="/platforms"   element={<ProtectedRoute><AppLayout><Platforms /></AppLayout></ProtectedRoute>} />
        <Route path="/reports"     element={<ProtectedRoute><AppLayout><Reports /></AppLayout></ProtectedRoute>} />
        <Route path="/dispute-engine" element={<ProtectedRoute><AppLayout><DisputeEngine /></AppLayout></ProtectedRoute>} />
        <Route path="/recovery"    element={<ProtectedRoute><AppLayout><Recovery /></AppLayout></ProtectedRoute>} />
        <Route path="/competitors" element={<ProtectedRoute><AppLayout><Competitors /></AppLayout></ProtectedRoute>} />
        <Route path="/rules"       element={<ProtectedRoute><AppLayout><Rules /></AppLayout></ProtectedRoute>} />
        <Route path="/recon-engine" element={<ProtectedRoute><AppLayout><ReconEngine /></AppLayout></ProtectedRoute>} />
        <Route path="/seller-discovery" element={<ProtectedRoute><AppLayout><SellerDiscovery /></AppLayout></ProtectedRoute>} />
        <Route path="/forecast"    element={<ProtectedRoute><AppLayout><CashFlowForecast /></AppLayout></ProtectedRoute>} />
        <Route path="/meetings"    element={<ProtectedRoute><AppLayout><MeetingCalendar /></AppLayout></ProtectedRoute>} />
        <Route path="*"            element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
