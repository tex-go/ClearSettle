/**
 * ReconciliationPipeline — full-screen reconciliation engine visualization.
 *
 * Rendered as a full-page overlay when a job is running.
 * Subscribes to real SSE events via useReconEvents + usePipelineState.
 * All animation is driven by actual backend stage transitions — no fake timers.
 *
 * Layout:
 *   ┌─── Header: job name · status · elapsed ───────────────────────┐
 *   │                                                                │
 *   │   [Stage] ──▶ [Stage] ──▶ [Stage] ──▶ [Stage] ──▶ [Stage]   │
 *   │                                                                │
 *   │   [Event Log]                  [Leakage Detections]           │
 *   │                                                                │
 *   │   [Total Leakage] [Disputable] [Recovery] [Variance]          │
 *   └────────────────────────────────────────────────────────────────┘
 */
import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useReconEvents } from '../../motion/engine/useReconEvents'
import { usePipelineState } from '../../motion/orchestration/usePipelineState'
import { PIPELINE_STAGES, STAGE_STATUS } from '../../motion/states/pipelineStages'
import { ConfidenceMeter } from '../../motion/primitives/ConfidenceMeter'
import { FlowConnector } from '../../motion/primitives/FlowConnector'
import { PipelineStage } from './PipelineStage'
import { LeakageEventFeed } from './LeakageEventFeed'
import { ProcessingMetrics } from './ProcessingMetrics'

function connectorStatus(leftStage, stageStates) {
  const leftState = stageStates[leftStage]?.status
  if (leftState === STAGE_STATUS.COMPLETED) return 'completed'
  if (leftState === STAGE_STATUS.ACTIVE)    return 'active'
  return 'idle'
}

function ElapsedTimer({ running }) {
  const [secs, setSecs] = useState(0)
  const startRef = useRef(Date.now())

  useEffect(() => {
    if (!running) return
    startRef.current = Date.now()
    setSecs(0)
    const id = setInterval(() => setSecs(Math.floor((Date.now() - startRef.current) / 1000)), 1000)
    return () => clearInterval(id)
  }, [running])

  const m = String(Math.floor(secs / 60)).padStart(2, '0')
  const s = String(secs % 60).padStart(2, '0')
  return <span>{m}:{s}</span>
}

function EventLog({ events }) {
  const bottomRef = useRef()
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  const typeIcon = {
    stage_start:  '▶',
    stage_done:   '✓',
    detector_run: '◎',
    leakage:      '⚠',
    ok:           '—',
    error:        '✗',
    complete:     '★',
  }
  const typeColor = {
    stage_start:  '#4B6080',
    stage_done:   '#10B981',
    detector_run: '#4B6080',
    leakage:      '#E9930D',
    ok:           '#2D4A6B',
    error:        '#E8344A',
    complete:     '#0ABFCA',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 220, overflowY: 'auto' }}>
      {events.map(ev => (
        <div key={ev.id} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12 }}>
          <span style={{ color: typeColor[ev.type] || '#4B6080', flexShrink: 0, fontWeight: 700 }}>
            {typeIcon[ev.type] || '·'}
          </span>
          <span style={{ color: '#8FA5BD', lineHeight: 1.4 }}>{ev.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

/**
 * @param {string}   jobId    — recon job UUID
 * @param {string}   jobName  — display name
 * @param {string}   token    — JWT
 * @param {function} onClose  — called to dismiss overlay
 * @param {function} onComplete — called with jobId when reconciliation finishes
 */
export function ReconciliationPipeline({ jobId, jobName, token, onClose, onComplete }) {
  const { state, handleEvent, reset } = usePipelineState()
  useReconEvents(jobId, token, handleEvent)

  const { stages, status, eventLog, leakageEvents, metrics, detectorIndex, totalDetectors } = state

  const isRunning   = status === 'running' || status === 'idle'
  const isCompleted = status === 'completed'
  const isFailed    = status === 'failed'

  // Notify parent when done
  useEffect(() => {
    if (isCompleted) onComplete?.(jobId)
  }, [isCompleted]) // eslint-disable-line react-hooks/exhaustive-deps

  const confidence = metrics.expectedPayout > 0
    ? Math.max(0, 1 - (metrics.totalLeakage / metrics.expectedPayout))
    : isCompleted ? 0.9 : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 40 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: '#0D1F35',
        display: 'flex', flexDirection: 'column',
        overflowY: 'auto',
      }}
    >
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16,
        padding: '18px 28px 16px',
        borderBottom: '1px solid rgba(255,255,255,.07)',
        flexShrink: 0,
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 16 }}>🔬</span>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#E2EBF3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {jobName}
            </div>
            <StatusPill status={status} />
          </div>
          <div style={{ fontSize: 12, color: '#4B6080', marginTop: 2 }}>
            Reconciliation Engine · <ElapsedTimer running={isRunning} />
          </div>
        </div>

        {/* Confidence meter — only shown once we have data */}
        {(isCompleted || metrics.totalLeakage > 0) && (
          <ConfidenceMeter score={confidence} size={72} showLabel={false} />
        )}

        <button
          onClick={onClose}
          style={{
            background: 'rgba(255,255,255,.06)', color: '#8FA5BD',
            border: '1px solid rgba(255,255,255,.08)',
            borderRadius: 8, padding: '7px 14px', fontSize: 12, fontWeight: 600,
            cursor: 'pointer', flexShrink: 0,
          }}
        >
          {isCompleted || isFailed ? '← Close' : '↓ Minimize'}
        </button>
      </div>

      {/* ── Pipeline stages ─────────────────────────────────────────────────── */}
      <div style={{
        padding: '24px 28px 20px',
        borderBottom: '1px solid rgba(255,255,255,.05)',
        flexShrink: 0,
      }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#2D4A6B', letterSpacing: '.08em', textTransform: 'uppercase', marginBottom: 14 }}>
          Pipeline
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 0, overflowX: 'auto', paddingBottom: 4 }}>
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={stage.id} style={{ display: 'flex', alignItems: 'center' }}>
              <PipelineStage
                stage={stage}
                stageState={stages[stage.id]}
                detectorIndex={stage.id === 'leakage_detection' ? detectorIndex : 0}
                totalDetectors={totalDetectors}
              />
              {i < PIPELINE_STAGES.length - 1 && (
                <FlowConnector
                  status={connectorStatus(stage.id, stages)}
                  width={36}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── Two-column: Event Log + Leakage Feed ────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 20, padding: '20px 28px',
        flex: 1, minHeight: 0,
      }}>
        {/* Event log */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#2D4A6B', letterSpacing: '.08em', textTransform: 'uppercase', marginBottom: 10 }}>
            Engine Log
          </div>
          <EventLog events={eventLog} />
        </div>

        {/* Leakage feed */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#2D4A6B', letterSpacing: '.08em', textTransform: 'uppercase' }}>
              Leakage Detected
            </div>
            {leakageEvents.length > 0 && (
              <span style={{
                background: 'rgba(232,52,74,.2)', color: '#E8344A',
                borderRadius: 10, padding: '1px 7px', fontSize: 10, fontWeight: 700,
              }}>
                {leakageEvents.length}
              </span>
            )}
          </div>
          <LeakageEventFeed events={leakageEvents} />
        </div>
      </div>

      {/* ── Metrics bar ─────────────────────────────────────────────────────── */}
      <div style={{
        padding: '0 28px 24px',
        flexShrink: 0,
      }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#2D4A6B', letterSpacing: '.08em', textTransform: 'uppercase', marginBottom: 10 }}>
          Financial Summary
        </div>
        <ProcessingMetrics metrics={metrics} status={status} />
      </div>

      {/* ── Completion banner ────────────────────────────────────────────────── */}
      <AnimatePresence>
        {isCompleted && (
          <motion.div
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 80, opacity: 0 }}
            style={{
              position: 'sticky', bottom: 0,
              padding: '16px 28px',
              background: 'linear-gradient(to top, #0D1F35 80%, transparent)',
              display: 'flex', justifyContent: 'center', gap: 12,
            }}
          >
            <button onClick={onClose} style={{
              padding: '10px 28px', borderRadius: 10, fontWeight: 700, fontSize: 14,
              background: 'linear-gradient(135deg,#0ABFCA,#088F99)',
              color: '#fff', border: 'none', cursor: 'pointer',
            }}>
              View Full Report →
            </button>
          </motion.div>
        )}
        {isFailed && (
          <motion.div
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            style={{
              position: 'sticky', bottom: 0,
              padding: '16px 28px',
              background: 'linear-gradient(to top, #0D1F35 80%, transparent)',
              display: 'flex', justifyContent: 'center',
            }}
          >
            <div style={{ color: '#E8344A', fontSize: 13, fontWeight: 600 }}>
              ⚠ {state.error || 'Reconciliation failed'}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function StatusPill({ status }) {
  const MAP = {
    idle:      { label: 'Starting',  bg: 'rgba(10,191,202,.15)',  color: '#0ABFCA' },
    running:   { label: 'Running',   bg: 'rgba(233,147,13,.15)',  color: '#E9930D' },
    completed: { label: 'Complete',  bg: 'rgba(16,185,129,.15)',  color: '#10B981' },
    failed:    { label: 'Failed',    bg: 'rgba(232,52,74,.15)',   color: '#E8344A' },
  }
  const s = MAP[status] || MAP.idle
  return (
    <span style={{
      ...s, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700,
    }}>
      {s.label}
    </span>
  )
}
