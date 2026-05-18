/**
 * CountUp — animated numeric counter.
 *
 * Uses Framer Motion's `animate` utility to tween a value.
 * GPU-accelerated via transform; no layout thrashing.
 *
 * Platform: pure React + Framer Motion, no DOM-specific assumptions.
 */
import { useEffect, useRef, useState } from 'react'
import { animate } from 'framer-motion'

/**
 * @param {number}   value    - target value
 * @param {function} format   - format fn, e.g. n => `₹${n.toLocaleString()}`
 * @param {number}   duration - animation duration in seconds
 * @param {object}   style    - container style
 */
export function CountUp({ value = 0, format = n => n.toFixed(0), duration = 1.2, style }) {
  const [display, setDisplay] = useState(format(0))
  const prevRef  = useRef(0)
  const ctrlRef  = useRef(null)

  useEffect(() => {
    if (ctrlRef.current) ctrlRef.current.stop()

    const from = prevRef.current
    prevRef.current = value

    ctrlRef.current = animate(from, value, {
      duration,
      ease: 'easeOut',
      onUpdate: v => setDisplay(format(v)),
    })

    return () => ctrlRef.current?.stop()
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  return <span style={style}>{display}</span>
}
