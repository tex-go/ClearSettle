/**
 * useReconEvents — React hook that manages a ReconEventBus lifecycle.
 *
 * Opens the SSE stream on mount, dispatches events into the pipeline
 * state machine, and cleans up on unmount.
 */
import { useEffect, useRef } from 'react'
import { ReconEventBus } from './ReconEventBus'

/**
 * @param {string|null} jobId   - recon job UUID; null means "not running"
 * @param {string}      token   - JWT auth token
 * @param {function}    onEvent - called with every event object from the stream
 */
export function useReconEvents(jobId, token, onEvent) {
  const busRef    = useRef(null)
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    if (!jobId || !token) return

    const bus = new ReconEventBus(jobId, token)
    busRef.current = bus

    bus.onAny(event => handlerRef.current(event))

    // connect() is async — it returns when the stream ends or is destroyed
    bus.connect().catch(err => {
      handlerRef.current({ type: 'connection_error', error: err.message })
    })

    return () => {
      bus.destroy()
      busRef.current = null
    }
  }, [jobId, token])
}
