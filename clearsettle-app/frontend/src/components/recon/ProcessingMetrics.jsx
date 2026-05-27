/**
 * ProcessingMetrics — bottom metrics bar showing live financial totals.
 *
 * Three large animated counters:
 *   Total Leakage | Disputable Amount | Recovery Potential
 *
 * Each counter uses CountUp for smooth animation as values accumulate.
 */
import { motion } from 'framer-motion'
import { CountUp } from '../../motion/primitives/CountUp'

const inr = n => `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

function MetricBlock({ label, value, color, sub, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      style={{
        flex: 1, textAlign: 'center',
        padding: '18px 20px',
        background: 'rgba(255,255,255,.04)',
        border: '1px solid rgba(255,255,255,.07)',
        borderRadius: 12,
      }}
    >
      <div style={{ fontSize: 11, color: '#4B6080', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 6 }}>
        {label}
      </div>
      <CountUp
        value={value}
        format={inr}
        duration={1.0}
        style={{ fontSize: 26, fontWeight: 800, color, display: 'block', lineHeight: 1 }}
      />
      {sub && (
        <div style={{ fontSize: 11, color: '#2D4A6B', marginTop: 4 }}>{sub}</div>
      )}
    </motion.div>
  )
}

export function ProcessingMetrics({ metrics, status }) {
  const { totalLeakage = 0, disputable = 0, recoveryTotal = 0, expectedPayout = 0, actualPayout = 0, variance = 0 } = metrics

  const confidence = expectedPayout > 0
    ? Math.max(0, 1 - (totalLeakage / expectedPayout))
    : 0

  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
      <MetricBlock
        label="Total Leakage"
        value={totalLeakage}
        color="#E8344A"
        sub={`${confidence > 0 ? Math.round(confidence * 100) + '% reconciliation confidence' : 'detection running'}`}
        delay={0}
      />
      <MetricBlock
        label="Disputable Amount"
        value={disputable}
        color="#E9930D"
        sub="can be recovered"
        delay={0.1}
      />
      <MetricBlock
        label="Recovery Potential"
        value={recoveryTotal}
        color="#10B981"
        sub="estimated recovery"
        delay={0.2}
      />
      {status === 'completed' && expectedPayout > 0 && (
        <MetricBlock
          label="Payout Variance"
          value={Math.abs(variance)}
          color={variance > 0 ? '#E8344A' : '#10B981'}
          sub={variance > 0 ? 'underpaid' : 'overpaid'}
          delay={0.3}
        />
      )}
    </div>
  )
}
