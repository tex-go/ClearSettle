/**
 * FlowConnector — animated directional arrow between pipeline stages.
 *
 * States:
 *   idle      — static dashed grey line
 *   active    — animated moving dash pattern (data flowing through)
 *   completed — solid teal line with filled arrow
 *
 * SVG-based; uses CSS stroke-dashoffset animation for the flow effect.
 * No DOM mutations — safe to render in any container.
 */
import { motion } from 'framer-motion'

/**
 * @param {'idle'|'active'|'completed'} status
 * @param {number} width   — connector width in px (default 40)
 */
export function FlowConnector({ status = 'idle', width = 40 }) {
  const isActive    = status === 'active'
  const isCompleted = status === 'completed'

  const color = isCompleted ? '#0ABFCA' : isActive ? '#4B6080' : '#2D3D50'
  const W = width
  const H = 20
  const arrowX = W - 7

  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      style={{ flexShrink: 0, overflow: 'visible' }}
      aria-hidden="true"
    >
      {/* Main line */}
      <motion.line
        x1={2} y1={H / 2} x2={arrowX} y2={H / 2}
        stroke={color}
        strokeWidth={isCompleted ? 2 : 1.5}
        strokeDasharray={isActive ? '6 4' : isCompleted ? 'none' : '4 4'}
        animate={isActive ? { strokeDashoffset: [0, -20] } : { strokeDashoffset: 0 }}
        transition={isActive ? { duration: 0.6, repeat: Infinity, ease: 'linear' } : {}}
        strokeLinecap="round"
      />
      {/* Arrowhead */}
      <motion.polyline
        points={`${arrowX - 5},${H / 2 - 4} ${arrowX},${H / 2} ${arrowX - 5},${H / 2 + 4}`}
        stroke={color}
        strokeWidth={isCompleted ? 2 : 1.5}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={false}
        animate={{ opacity: isActive ? 0.5 : 1 }}
      />
    </svg>
  )
}
