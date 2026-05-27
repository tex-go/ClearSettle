/**
 * RiveAdapter — interface contract for Rive state machine integration.
 *
 * When Rive assets are ready, swap this stub for the real adapter
 * using @rive-app/react-canvas.  The component API (inputs, events)
 * is identical — no changes needed in ReconciliationPipeline or PipelineStage.
 *
 * Expected Rive state machine inputs (match when building the .riv file):
 *   Boolean: stage_active, stage_completed, error_state, leakage_detected
 *   Number:  confidence_score (0–1), detector_progress (0–10)
 *
 * Usage (future):
 *   import { RiveStageAnimation } from './RiveAdapter'
 *   <RiveStageAnimation src="/rive/pipeline-stage.riv" inputs={{ stage_active: true }} />
 */

/**
 * Stub component — renders nothing, logs in dev.
 * Replace with real Rive component when assets are ready.
 */
export function RiveStageAnimation({ src, inputs = {}, className }) {
  if (process.env.NODE_ENV === 'development') {
    // eslint-disable-next-line no-console
    console.debug('[RiveAdapter] stub — replace with @rive-app/react-canvas when .riv assets are ready', { src, inputs })
  }
  return null
}

export const RIVE_INPUTS = {
  STAGE_ACTIVE:       'stage_active',
  STAGE_COMPLETED:    'stage_completed',
  ERROR_STATE:        'error_state',
  LEAKAGE_DETECTED:   'leakage_detected',
  CONFIDENCE_SCORE:   'confidence_score',
  DETECTOR_PROGRESS:  'detector_progress',
}
