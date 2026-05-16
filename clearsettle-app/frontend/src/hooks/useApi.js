import { useState, useEffect } from 'react'
import api from '../utils/api'

function useApi(url, deps) {
  var depsList = deps || []
  var [data, setData] = useState(null)
  var [loading, setLoading] = useState(true)
  var [error, setError] = useState(null)

  useEffect(function() {
    if (!url) return
    var cancelled = false
    setLoading(true)
    setError(null)
    api.get(url)
      .then(function(res) {
        if (!cancelled) {
          setData(res.data)
          setLoading(false)
        }
      })
      .catch(function(err) {
        if (!cancelled) {
          setError(err)
          setLoading(false)
        }
      })
    return function() { cancelled = true }
  }, [url, ...depsList])

  return { data: data, loading: loading, error: error }
}

export default useApi
