import { create } from 'zustand'

var useAuthStore = create(function(set) {
  var token = localStorage.getItem('cs_token')
  var userRaw = localStorage.getItem('cs_user')
  var user = null
  try { user = userRaw ? JSON.parse(userRaw) : null } catch(e) {}
  return {
    user: user,
    token: token,
    isAuth: !!token,
    login: function(token, user) {
      localStorage.setItem('cs_token', token)
      localStorage.setItem('cs_user', JSON.stringify(user))
      set({ token: token, user: user, isAuth: true })
    },
    logout: function() {
      localStorage.removeItem('cs_token')
      localStorage.removeItem('cs_user')
      localStorage.removeItem('cs_onboarded')
      set({ token: null, user: null, isAuth: false })
    },
  }
})

export default useAuthStore
