import { create } from 'zustand'

var useUIStore = create(function(set, get) {
  return {
    toasts: [],
    addToast: function(msg, type, sub) {
      var id = Date.now() + Math.random()
      set(function(s) { return { toasts: [...s.toasts, { id, msg, type: type || 'info', sub }] } })
      setTimeout(function() {
        set(function(s) { return { toasts: s.toasts.filter(function(t) { return t.id !== id }) } })
      }, 4000)
    },
    removeToast: function(id) {
      set(function(s) { return { toasts: s.toasts.filter(function(t) { return t.id !== id }) } })
    },
  }
})

export default useUIStore
