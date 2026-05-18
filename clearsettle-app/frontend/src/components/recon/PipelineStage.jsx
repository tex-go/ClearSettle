/**
 * PipelineStage — single stage card in the reconciliation pipeline.
 *
 * Communicates three states visually:
 *   pending   — dim, grey border, waiting
 *   active    — teal accent border, gentle pulse, rotating progress indicator
 *   completed — green left-edge fill, checkmark, metric shown
 *   error     — red border, error message
 */
import { motion, AnimatePresence } from 'framer-motion'
import { STAGE_STATUS } from '../../motion/states/pipelineStages'

const BORDER = {
  [STAGE_STATUS.PENDING]:   'rgba(255,255,255,.08)',
  [STAGE_STATUS.ACTIVE]:    '#0ABFCA',
  [STAGE_STATUS.COMPLETED]: '#10B981',
  [STAGE_STATUS.ERROR]:     '#E8344A',
}

const BG = {
  [STAGE_STATUS.PENDING]:   'rgba(255,255,255,.03)',
  [STAGE_STATUS.ACTIVE]:    'rgba(10,191,202,.08)',
  [STAGE_STATUS.COMPLETED]: 'rgba(16,185,129,.06)',
  [STAGE_STATUS.ERROR]:     'rgba(232,52,74,.08)',
}

export function PipelineStage({ stage, stageState, detectorIndex, totalDetectors, isLast }) {
  const { status, metric, message } = stageState
  const isActive    = status === STAGE_STATUS.ACTIVE
  const isCompleted = status === STAGE_STATUS.COMPLETED
  const isError     = status === STAGE_STATUS.ERROR
  const isPending   = status === STAGE_STATUS.PENDING
  const isDetect    = stage.id === 'leakage_detection'

  // Detector sub-progress: 0–10 during leakage_detection active state
  const detectPct = isDetect && isActive && totalDetectors
    ? Math.round((detectorIndex / totalDetectors) * 100)
    : null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: isPending ? 0.45 : 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        position: 'relative',
        width: 130,
        background: BG[status],
        border: `1.5px solid ${BORDER[status]}`,
        borderRadius: 12,
        padding: '14px 14px 12px',
        flexShrink: 0,
        overflow: 'hidden',
      }}
    >
      {/* Active border pulse */}
      {isActive && (
        <motion.div
          style={{
            position: 'absolute', inset: 0, borderRadius: 11,
            border: '1.5px solid #0ABFCA', pointerEvents: 'none',
          }}
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}

      {/* Left edge completion fill */}
      {isCompleted && (
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: 3, background: '#10B981', borderRadius: '12px 0 0 12px',
        }} />
      )}

      {/* Icon + status dot */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <span style={{ fontSize: 22, lineHeight: 1 }}>{stage.icon}</span>
        <StatusDot status={status} />
      </div>

      {/* Stage name */}
      <div style={{
        fontSize: 11, fontWeight: 800, color: isPending ? '#4B6080' : '#E2EBF3',
        textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 4,
        lineHeight: 1.2,
      }}>
        {stage.shortLabel}
      </div>

      {/* Metric or sub-progress */}
      <AnimatePresence mode="wait">
        {isCompleted && metric != null && (
          <motion.div
            key="metric"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ fontSize: 12, fontWeight: 700, color: '#10B981', marginTop: 2 }}
          >
            {stage.metricFormat ? stage.metricFormat(metric) : metric}
          </motion.div>
        )}
        {isActive && !isDetect && (
          <motion.div
            key="active"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ fontSize: 11, color: '#0ABFCA', marginTop: 2 }}
          >
            Processing…
          </motion.div>
        )}
        {isActive && isDetect && detectPct !== null && (
          <motion.div key="detect-progress" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div style={{ fontSize: 11, color: '#0ABFCA', marginBottom: 4 }}>
              {detectorIndex}/{totalDetectors} detectors
            </div>
            <div style={{ height: 3, background: 'rgba(255,255,255,.1)', borderRadius: 2, overflow: 'hidden' }}>
              <motion.div
                style={{ height: '100%', background: '#0ABFCA', borderRadius: 2 }}
                animate={{ width: `${detectPct}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>
          </motion.div>
        )}
        {isPending && (
          <motion.div
            key="pending"
            style={{ fontSize: 11, color: '#2D4A6B', marginTop: 2 }}
          >
            Waiting
          </motion.div>
        )}
        {isError && (
          <motion.div
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ fontSize: 10, color: '#E8344A', marginTop: 2, lineHeight: 1.3 }}
          >
            {message || 'Error'}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function StatusDot({ status }) {
  if (status === STAGE_STATUS.COMPLETED) {
    return (
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        style={{
          width: 18, height: 18, borderRadius: '50%',
          background: '#10B981',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, color: '#fff', fontWeight: 800,
        }}
      >
        ✓
      </motion.div>
    )
  }
  if (status === STAGE_STATUS.ACTIVE) {
    return (
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
        style={{
          width: 16, height: 16, borderRadius: '50%',
          border: '2px solid rgba(10,191,202,.2)',
          borderTop: '2px solid #0ABFCA',
        }}
      />
    )
  }
  if (status === STAGE_STATUS.ERROR) {
    return (
      <div style={{
        width: 18, height: 18, borderRadius: '50%',
        background: '#E8344A',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, color: '#fff', fontWeight: 800,
      }}>!</div>
    )
  }
  return (
    <div style={{
      width: 10, height: 10, borderRadius: '50%',
      background: 'rgba(255,255,255,.1)',
      border: '1.5px solid rgba(255,255,255,.12)',
    }} />
  )
}
