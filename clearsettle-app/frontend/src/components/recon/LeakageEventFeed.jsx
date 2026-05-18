/**
 * LeakageEventFeed — animated live feed of leakage detections.
 *
 * Each event slides in from the right as it arrives.
 * Severity indicated by color accent and icon.
 * Amount shown with CountUp animation.
 */
import { AnimatePresence, motion } from 'framer-motion'
import { CountUp } from '../../motion/primitives/CountUp'
import { PulseRing } from '../../motion/primitives/PulseRing'

const fmt = n =>
  n == null ? '—' : `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

export function LeakageEventFeed({ events = [], maxVisible = 8 }) {
  const visible = events.slice(-maxVisible)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 60 }}>
      {visible.length === 0 && (
        <div style={{ fontSize: 12, color: '#2D4A6B', fontStyle: 'italic', paddingTop: 8 }}>
          No leakage events yet — detection running…
        </div>
      )}
      <AnimatePresence initial={false}>
        {visible.map(ev => (
          <motion.div
            key={ev.id}
            layout
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              background: `${ev.color}12`,
              border: `1px solid ${ev.color}30`,
              borderRadius: 8, padding: '8px 12px',
            }}
          >
            {/* Pulse ring only for large amounts */}
            {ev.amount > 10000 ? (
              <PulseRing color={ev.color} size={18} rings={2} />
            ) : (
              <div style={{
                width: 10, height: 10, borderRadius: '50%',
                background: ev.color, flexShrink: 0,
              }} />
            )}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: ev.color }}>
                {ev.label}
              </div>
              <div style={{ fontSize: 11, color: '#4B6080' }}>
                {ev.found} event{ev.found !== 1 ? 's' : ''} detected
              </div>
            </div>
            <CountUp
              value={ev.amount}
              format={fmt}
              duration={0.8}
              style={{ fontSize: 14, fontWeight: 800, color: ev.color, flexShrink: 0 }}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
