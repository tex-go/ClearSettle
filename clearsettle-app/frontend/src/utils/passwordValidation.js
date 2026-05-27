/**
 * Password rules mirror backend app/core/security.py validate_password_strength.
 * Any change here must also update the backend.
 */

export var PASSWORD_RULES = [
  { id: 'len',     label: 'Minimum 10 characters',     test: function(p) { return p.length >= 10 } },
  { id: 'upper',   label: 'Contains uppercase letter',  test: function(p) { return /[A-Z]/.test(p) } },
  { id: 'lower',   label: 'Contains lowercase letter',  test: function(p) { return /[a-z]/.test(p) } },
  { id: 'digit',   label: 'Contains a number',          test: function(p) { return /[0-9]/.test(p) } },
  { id: 'special', label: 'Contains special character', test: function(p) { return /[^A-Za-z0-9]/.test(p) } },
]

export function checkPassword(pw) {
  return PASSWORD_RULES.map(function(r) {
    return { id: r.id, label: r.label, passed: r.test(pw) }
  })
}

export function isPasswordValid(pw) {
  return PASSWORD_RULES.every(function(r) { return r.test(pw) })
}

export function friendlyApiError(detail) {
  if (!detail) return 'Registration failed. Please try again.'
  if (Array.isArray(detail)) {
    var msgs = detail.map(function(m) {
      var raw = (m.msg || '').toLowerCase()
      if (raw.includes('10 character') || raw.includes('at least 10')) return 'Password must be at least 10 characters.'
      if (raw.includes('uppercase')) return 'Password must include an uppercase letter.'
      if (raw.includes('lowercase')) return 'Password must include a lowercase letter.'
      if (raw.includes('digit') || raw.includes('number')) return 'Password must include a number.'
      if (raw.includes('special')) return 'Password must include a special character.'
      if (raw.includes('already') && raw.includes('email')) return 'An account with this email already exists.'
      if (raw.includes('gstin')) return 'Invalid GSTIN format. Example: 33ABCDE1234F1Z5'
      return m.msg || 'An error occurred'
    })
    return msgs.join(' ')
  }
  if (typeof detail === 'string') {
    var d = detail.toLowerCase()
    if (d.includes('already registered') || d.includes('already exists')) return 'An account with this email already exists.'
    if (d.includes('10 character') || d.includes('at least 10')) return 'Password must be at least 10 characters.'
    if (d.includes('uppercase')) return 'Password must include an uppercase letter.'
    return detail
  }
  return 'Registration failed. Please try again.'
}
