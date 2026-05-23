import { create } from 'zustand'

var useAuthStore = create(function(set, get) {
  var token = localStorage.getItem('cs_token')
  var refreshToken = localStorage.getItem('cs_refresh_token')
  var userRaw = localStorage.getItem('cs_user')
  var user = null
  try { user = userRaw ? JSON.parse(userRaw) : null } catch(e) {}

  var store = {
    user: user,
    token: token,
    refreshToken: refreshToken,
    isAuth: !!token,

    login: function(accessToken, newRefreshToken, user) {
      localStorage.setItem('cs_token', accessToken)
      if (newRefreshToken) localStorage.setItem('cs_refresh_token', newRefreshToken)
      localStorage.setItem('cs_user', JSON.stringify(user))
      set({ token: accessToken, refreshToken: newRefreshToken, user: user, isAuth: true })
    },

    setTokens: function(accessToken, newRefreshToken) {
      localStorage.setItem('cs_token', accessToken)
      if (newRefreshToken) localStorage.setItem('cs_refresh_token', newRefreshToken)
      set(function(s) {
        return { token: accessToken, refreshToken: newRefreshToken || s.refreshToken }
      })
    },

    logout: function() {
      localStorage.removeItem('cs_token')
      localStorage.removeItem('cs_refresh_token')
      localStorage.removeItem('cs_user')
      localStorage.removeItem('cs_onboarded')
      set({ token: null, refreshToken: null, user: null, isAuth: false })
    },
  }

  // Keep store in sync when api.js silently refreshes tokens
  if (typeof window !== 'undefined') {
    window.addEventListener('cs:tokens-refreshed', function(e) {
      set(function(s) {
        return {
          token: e.detail.accessToken,
          refreshToken: e.detail.refreshToken || s.refreshToken,
        }
      })
    })
  }

  return store
})

export default useAuthStore
