/**
 * ConfidenceMeter — circular arc showing reconciliation confidence score.
 *
 * Score is derived from: 1 - (total_leakage / expected_payout).
 * Range: 0 (red) → 1 (green).  Arc fills clockwise as score increases.
 *
 * Uses SVG + Framer Motion for smooth arc animation.
 */
import { motion } from 'framer-motion'

const R   = 40          // circle radius
const CX  = 52          // viewBox centre X
const CY  = 52          // viewBox centre Y
const CIRC = 2 * Math.PI * R   // circumference ≈ 251.3

function scoreToColor(score) {
  if (score >= 0.85) return '#10B981'
  if (score >= 0.60) return '#E9930D'
  return '#E8344A'
}

function scoreToLabel(score) {
  if (score >= 0.85) return 'High'
  if (score >= 0.60) return 'Medium'
  return 'Low'
}

/**
 * @param {number} score      — 0–1
 * @param {number} size       — outer size px (default 104)
 * @param {boolean} showLabel — show text label (default true)
 */
export function ConfidenceMeter({ score = 0, size = 104, showLabel = true }) {
  const offset = CIRC * (1 - Math.max(0, Math.min(1, score)))
  const color  = scoreToColor(score)
  const label  = scoreToLabel(score)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={size} height={size} viewBox="0 0 104 104">
        {/* Track */}
        <circle
          cx={CX} cy={CY} r={R}
          fill="none"
          stroke="rgba(255,255,255,.08)"
          strokeWidth={10}
        />
        {/* Arc */}
        <motion.circle
          cx={CX} cy={CY} r={R}
          fill="none"
          stroke={color}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={CIRC}
          initial={{ strokeDashoffset: CIRC }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          style={{ transform: 'rotate(-90deg)', transformOrigin: `${CX}px ${CY}px` }}
        />
        {/* Score text */}
        <text x={CX} y={CY + 5} textAnchor="middle"
          fill={color} fontSize={17} fontWeight={800} fontFamily="system-ui">
          {Math.round(score * 100)}%
        </text>
      </svg>
      {showLabel && (
        <div style={{ fontSize: 11, fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: '.06em' }}>
          {label} Confidence
        </div>
      )}
    </div>
  )
}
