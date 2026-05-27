/**
 * usePipelineState — the orchestration layer between SSE events and
 * the animation/render layer.
 *
 * Receives raw events from useReconEvents and produces a structured
 * pipeline state that all visualization components consume.
 * Contains zero rendering logic — pure state machine.
 *
 * Platform portability: this hook only depends on React.
 * On React Native / Electron the same logic applies unchanged.
 */
import { useCallback, useReducer } from 'react'
import { DETECTOR_META, STAGE_STATUS, initialStageState } from '../states/pipelineStages'

// ── State shape ────────────────────────────────────────────────────────────────
const INITIAL = {
  stages:          initialStageState(),
  activeStage:     null,
  status:          'idle',          // idle | running | completed | failed
  eventLog:        [],              // [{id, message, ts, type}]
  leakageEvents:   [],              // [{detector, label, found, amount, color}]
  detectorIndex:   0,
  totalDetectors:  10,
  metrics: {
    totalLeakage:   0,
    disputable:     0,
    recoveryTotal:  0,
    expectedPayout: 0,
    actualPayout:   0,
    variance:       0,
    variancePct:    0,
    totalRows:      0,
  },
  error: null,
}

function reducer(state, action) {
  switch (action.type) {

    case 'STAGE_STARTED': {
      const { stage, message } = action
      const stages = {
        ...state.stages,
        [stage]: { ...state.stages[stage], status: STAGE_STATUS.ACTIVE, message },
      }
      return {
        ...state,
        stages,
        activeStage: stage,
        status:      'running',
        eventLog: _appendLog(state.eventLog, { message, type: 'stage_start' }),
      }
    }

    case 'STAGE_COMPLETED': {
      const { stage, metric, message } = action
      const stages = {
        ...state.stages,
        [stage]: { status: STAGE_STATUS.COMPLETED, metric, message },
      }
      return {
        ...state,
        stages,
        eventLog: _appendLog(state.eventLog, { message, type: 'stage_done' }),
      }
    }

    case 'STAGE_ERROR': {
      const { stage, message } = action
      const stages = {
        ...state.stages,
        [stage]: { ...state.stages[stage], status: STAGE_STATUS.ERROR, message },
      }
      return { ...state, stages, error: message }
    }

    case 'DETECTOR_RUNNING': {
      const { message, detectorIndex, totalDetectors } = action
      return {
        ...state,
        detectorIndex,
        totalDetectors: totalDetectors || state.totalDetectors,
        eventLog: _appendLog(state.eventLog, { message, type: 'detector_run' }),
      }
    }

    case 'DETECTOR_COMPLETED': {
      const { detector, label, found, amount, color, message } = action
      const leakageEvents = found > 0
        ? [...state.leakageEvents, { id: `${detector}-${Date.now()}`, detector, label, found, amount, color }]
        : state.leakageEvents
      const totalLeakage = state.metrics.totalLeakage + (amount || 0)
      return {
        ...state,
        leakageEvents,
        metrics: { ...state.metrics, totalLeakage },
        eventLog: _appendLog(state.eventLog, { message, type: found > 0 ? 'leakage' : 'ok' }),
      }
    }

    case 'RECOVERY_COMPLETED': {
      const { disputable, recoveryTotal, expectedPayout, actualPayout, variance, variancePct } = action
      return {
        ...state,
        metrics: {
          ...state.metrics,
          disputable,
          recoveryTotal,
          expectedPayout,
          actualPayout,
          variance,
          variancePct,
        },
      }
    }

    case 'ROWS_LOADED': {
      return { ...state, metrics: { ...state.metrics, totalRows: action.totalRows } }
    }

    case 'COMPLETED': {
      return {
        ...state,
        status:  'completed',
        metrics: { ...state.metrics, ...action.metrics },
        eventLog: _appendLog(state.eventLog, { message: 'Reconciliation complete', type: 'complete' }),
      }
    }

    case 'FAILED': {
      return {
        ...state,
        status: 'failed',
        error:  action.error,
        eventLog: _appendLog(state.eventLog, { message: action.error, type: 'error' }),
      }
    }

    case 'RESET':
      return INITIAL

    default:
      return state
  }
}

function _appendLog(log, entry) {
  const next = [...log, { id: `${Date.now()}-${Math.random()}`, ts: Date.now(), ...entry }]
  return next.length > 60 ? next.slice(-60) : next   // cap at 60 log entries
}

// ── Hook ───────────────────────────────────────────────────────────────────────
export function usePipelineState() {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  /**
   * handleEvent — processes a raw SSE event from the backend.
   * This is the only entry point; all state transitions go through here.
   */
  const handleEvent = useCallback((event) => {
    const { stage, status, type } = event

    // ── Stage lifecycle ──────────────────────────────────────────────────────
    if (stage && status === 'started') {
      dispatch({ type: 'STAGE_STARTED', stage, message: event.message })
      if (stage === 'ingestion') {
        // no metric yet on start
      }
      return
    }

    if (stage && status === 'completed') {
      let metric = null
      if (stage === 'ingestion')          metric = event.total_rows
      if (stage === 'normalization')      metric = event.settlement_coverage
      if (stage === 'entity_resolution')  metric = event.matched_pos
      if (stage === 'leakage_detection')  metric = event.total_found
      if (stage === 'recovery_analysis')  metric = event.disputable

      dispatch({ type: 'STAGE_COMPLETED', stage, metric, message: event.message })

      if (stage === 'ingestion')   dispatch({ type: 'ROWS_LOADED', totalRows: event.total_rows })
      if (stage === 'recovery_analysis') {
        dispatch({
          type:          'RECOVERY_COMPLETED',
          disputable:    event.disputable,
          recoveryTotal: event.recovery_total,
          expectedPayout: event.expected_payout,
          actualPayout:   event.actual_payout,
          variance:       event.variance,
          variancePct:    event.variance_pct,
        })
      }
      return
    }

    // ── Per-detector events (leakage_detection sub-events) ───────────────────
    if (stage === 'leakage_detection' && status === 'detector_running') {
      dispatch({
        type:           'DETECTOR_RUNNING',
        message:        event.message,
        detectorIndex:  event.detector_index,
        totalDetectors: event.total_detectors,
      })
      return
    }

    if (stage === 'leakage_detection' && status === 'detector_completed') {
      const meta  = DETECTOR_META[event.detector] || { label: event.detector_label, color: '#8FA5BD' }
      dispatch({
        type:     'DETECTOR_COMPLETED',
        detector: event.detector,
        label:    meta.label,
        found:    event.found,
        amount:   event.amount,
        color:    meta.color,
        message:  event.message,
      })
      return
    }

    // ── Terminal events ──────────────────────────────────────────────────────
    if (type === 'completed') {
      dispatch({
        type:    'COMPLETED',
        metrics: {
          totalLeakage:   event.total_leakage,
          disputable:     event.disputable,
          recoveryTotal:  event.recovery_total,
          expectedPayout: event.expected_payout,
          actualPayout:   event.actual_payout,
          variance:       event.variance,
          variancePct:    event.variance_pct,
        },
      })
      return
    }

    if (type === 'failed') {
      dispatch({ type: 'FAILED', error: event.error || event.message })
    }
  }, [])

  const reset = useCallback(() => dispatch({ type: 'RESET' }), [])

  return { state, handleEvent, reset }
}
