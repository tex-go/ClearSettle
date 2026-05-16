export function INR(n) {
  if (n === null || n === undefined) return '₹0'
  return '₹' + Number(n).toLocaleString('en-IN')
}

export function INRL(n) {
  if (!n) return '₹0'
  if (n >= 10000000) return '₹' + (n / 10000000).toFixed(2) + ' Cr'
  if (n >= 100000) return '₹' + (n / 100000).toFixed(2) + ' L'
  return INR(n)
}

export function INRCR(n) {
  if (!n) return '₹0'
  if (n >= 10000000) return '₹' + (n / 10000000).toFixed(2) + ' Cr'
  return INRL(n)
}

export function PCT(n) {
  return Number(n).toFixed(1) + '%'
}

export var statusColors = {
  paid: 'gn',
  connected: 'gn',
  ok: 'gn',
  processed: 'gn',
  won: 'gn',
  pending: 'am',
  partial: 'am',
  low: 'am',
  unmatched: 'rd',
  disconnected: 'gr',
  critical: 'rd',
  disputed: 'pu',
  open: 'am',
  lost: 'rd',
  gst_pending: 'pu',
}
