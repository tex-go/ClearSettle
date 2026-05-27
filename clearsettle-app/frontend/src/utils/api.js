import axios from 'axios'

var api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' })

// Attach access token to every request
api.interceptors.request.use(function(config) {
  var token = localStorage.getItem('cs_token')
  if (token) {
    config.headers.Authorization = 'Bearer ' + token
  }
  return config
})

// Silent token refresh on 401
var _refreshing = null  // single in-flight refresh promise

api.interceptors.response.use(
  function(res) { return res },
  function(err) {
    var original = err.config

    // Only attempt refresh for 401s on non-auth endpoints and non-retried requests
    if (
      err.response &&
      err.response.status === 401 &&
      !original._retried &&
      !original.url.includes('/auth/login') &&
      !original.url.includes('/auth/refresh')
    ) {
      original._retried = true

      if (!_refreshing) {
        var refreshToken = localStorage.getItem('cs_refresh_token')
        if (!refreshToken) {
          _forceLogout()
          return Promise.reject(err)
        }

        _refreshing = axios
          .post((import.meta.env.VITE_API_URL || '/api') + '/auth/refresh', {
            refresh_token: refreshToken,
          })
          .then(function(res) {
            var data = res.data
            localStorage.setItem('cs_token', data.access_token)
            if (data.refresh_token) {
              localStorage.setItem('cs_refresh_token', data.refresh_token)
            }
            // Update the Zustand store without importing it (avoids circular deps)
            window.dispatchEvent(new CustomEvent('cs:tokens-refreshed', {
              detail: { accessToken: data.access_token, refreshToken: data.refresh_token },
            }))
            return data.access_token
          })
          .catch(function() {
            _forceLogout()
            return Promise.reject(new Error('Session expired'))
          })
          .finally(function() {
            _refreshing = null
          })
      }

      return _refreshing.then(function(newToken) {
        original.headers.Authorization = 'Bearer ' + newToken
        return api(original)
      })
    }

    return Promise.reject(err)
  }
)

function _forceLogout() {
  localStorage.removeItem('cs_token')
  localStorage.removeItem('cs_refresh_token')
  localStorage.removeItem('cs_user')
  localStorage.removeItem('cs_onboarded')
  window.location.href = '/login'
}

export default api
