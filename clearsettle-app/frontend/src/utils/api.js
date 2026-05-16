import axios from 'axios'

var api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' })

api.interceptors.request.use(function(config) {
  var token = localStorage.getItem('cs_token')
  if (token) {
    config.headers.Authorization = 'Bearer ' + token
  }
  return config
})

api.interceptors.response.use(
  function(res) { return res },
  function(err) {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('cs_token')
      localStorage.removeItem('cs_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
