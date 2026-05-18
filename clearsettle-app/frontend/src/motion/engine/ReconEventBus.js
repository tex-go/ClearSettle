/**
 * ReconEventBus — SSE client for reconciliation engine events.
 *
 * Uses fetch() with ReadableStream rather than the browser's EventSource
 * so we can include the Authorization header (EventSource doesn't support
 * custom headers).
 *
 * Platform contract
 * -----------------
 * The class is framework-agnostic — no React imports, no DOM assumptions
 * beyond fetch + ReadableStream.  On React Native / Electron it can be
 * replaced with a WebSocket adapter that emits the same event shape.
 *
 * Event shape (matches backend event_bus.py):
 * {
 *   stage?:   "ingestion" | "normalization" | "entity_resolution" |
 *             "leakage_detection" | "recovery_analysis" | "report",
 *   status?:  "started" | "completed" | "detector_running" | "detector_completed",
 *   type?:    "completed" | "failed" | "stream_end",
 *   message?: string,
 *   // stage-specific fields ...
 * }
 */

export class ReconEventBus {
  constructor(jobId, token) {
    this._jobId    = jobId
    this._token    = token
    this._handlers = {}
    this._closed   = false
    this._ctrl     = new AbortController()
  }

  /** Subscribe to an event type. Returns an unsubscribe fn. */
  on(eventType, handler) {
    if (!this._handlers[eventType]) this._handlers[eventType] = []
    this._handlers[eventType].push(handler)
    return () => {
      this._handlers[eventType] = (this._handlers[eventType] || []).filter(h => h !== handler)
    }
  }

  /** Subscribe to every event. Returns an unsubscribe fn. */
  onAny(handler) {
    return this.on('*', handler)
  }

  _dispatch(event) {
    const specific = this._handlers[event.stage || event.type] || []
    const wildcard = this._handlers['*'] || []
    ;[...specific, ...wildcard].forEach(h => {
      try { h(event) } catch (e) { console.error('[ReconEventBus] handler error', e) }
    })
  }

  /** Open the SSE connection. Resolves once the stream ends or errors. */
  async connect() {
    const url = `/api/recon-engine/jobs/${this._jobId}/events`
    let response
    try {
      response = await fetch(url, {
        headers: { Authorization: `Bearer ${this._token}` },
        signal:  this._ctrl.signal,
      })
    } catch (err) {
      if (!this._closed) this._dispatch({ type: 'connection_error', error: err.message })
      return
    }

    if (!response.ok) {
      this._dispatch({ type: 'connection_error', error: `HTTP ${response.status}` })
      return
    }

    const reader  = response.body.getReader()
    const decoder = new TextDecoder()
    let   buffer  = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done || this._closed) break

        buffer += decoder.decode(value, { stream: true })
        // SSE chunks are separated by double newlines
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() ?? ''

        for (const block of blocks) {
          for (const line of block.split('\n')) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6))
                this._dispatch(event)
                if (event.type === 'stream_end' || event.type === 'completed' || event.type === 'failed') {
                  this._closed = true
                  return
                }
              } catch {
                // ignore malformed lines
              }
            }
            // SSE comments (": keepalive") are silently ignored
          }
        }
      }
    } finally {
      try { reader.cancel() } catch { /* ignore */ }
    }
  }

  /** Close the connection and stop all event delivery. */
  destroy() {
    this._closed = true
    this._ctrl.abort()
    this._handlers = {}
  }
}
