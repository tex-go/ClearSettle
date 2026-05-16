import React from 'react'
import { statusColors } from '../../utils/format'

export function Chip({ children, color }) {
  var c = color || 'gr'
  return (
    <span className={'cs-chip cs-chip-' + c}>{children}</span>
  )
}

export function StatusChip({ status }) {
  var color = statusColors[status] || 'gr'
  var labels = {
    paid: 'Paid', connected: 'Connected', ok: 'OK', processed: 'Processed',
    won: 'Won', pending: 'Pending', partial: 'Partial', low: 'Low Stock',
    unmatched: 'Unmatched', disconnected: 'Disconnected', critical: 'Critical',
    disputed: 'Disputed', open: 'Open', lost: 'Lost', gst_pending: 'GST Pending',
  }
  return (
    <span className={'cs-chip cs-chip-' + color}>{labels[status] || status}</span>
  )
}
