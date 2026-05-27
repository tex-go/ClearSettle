/**
 * PulseRing — expanding ring animation used to signal leakage detection.
 *
 * Renders three concentric rings that fade + scale out sequentially.
 * Designed to look like a sonar ping — deliberate and purposeful,
 * not decorative.
 *
 * Use on leakage event cards and the detection stage icon.
 */
import { motion } from 'framer-motion'

const RING_VARIANTS = {
  initial: { scale: 0.6, opacity: 0.8 },
  animate: (delay) => ({
    scale: [0.6, 2.2],
    opacity: [0.7, 0],
    transition: { duration: 1.8, delay, ease: 'easeOut', repeat: Infinity, repeatDelay: 0.4 },
  }),
}

/**
 * @param {string} color   - ring colour (default: #E8344A)
 * @param {number} size    - base size in px (default: 24)
 * @param {number} rings   - number of concentric rings (default: 3)
 */
export function PulseRing({ color = '#E8344A', size = 24, rings = 3 }) {
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: size, height: size }}>
      {Array.from({ length: rings }).map((_, i) => (
        <motion.span
          key={i}
          custom={i * 0.4}
          variants={RING_VARIANTS}
          initial="initial"
          animate="animate"
          style={{
            position: 'absolute',
            width:    size,
            height:   size,
            borderRadius: '50%',
            border: `1.5px solid ${color}`,
          }}
        />
      ))}
    </span>
  )
}
