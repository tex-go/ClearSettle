/**
 * Pipeline stage definitions — the source of truth for the entire
 * reconciliation visualization.
 *
 * Each stage maps directly to backend event_bus `stage` values.
 * Adding a new detector or stage on the backend only requires adding
 * an entry here; all animation components consume this list.
 */

export const PIPELINE_STAGES = [
  {
    id:          'ingestion',
    label:       'Document Intake',
    shortLabel:  'Ingest',
    description: 'Loading staged documents from database',
    icon:        '📄',
    metricKey:   'total_rows',
    metricLabel: 'rows loaded',
    metricFormat: n => `${Number(n).toLocaleString('en-IN')} rows`,
  },
  {
    id:          'normalization',
    label:       'Data Normalization',
    shortLabel:  'Normalize',
    description: 'Scanning for structural anomalies and null fields',
    icon:        '🔧',
    metricKey:   'settlement_coverage',
    metricLabel: 'lines with amounts',
    metricFormat: n => `${Number(n).toLocaleString('en-IN')} lines`,
  },
  {
    id:          'entity_resolution',
    label:       'Entity Resolution',
    shortLabel:  'Entities',
    description: 'Resolving PO → Invoice → Shipment → Settlement links',
    icon:        '🔗',
    metricKey:   'matched_pos',
    metricLabel: 'POs matched',
    metricFormat: n => `${Number(n).toLocaleString('en-IN')} POs`,
  },
  {
    id:          'leakage_detection',
    label:       'Leakage Detection',
    shortLabel:  'Detect',
    description: 'Running 10 leakage detectors',
    icon:        '🔍',
    metricKey:   'total_found',
    metricLabel: 'events found',
    metricFormat: n => `${Number(n).toLocaleString('en-IN')} events`,
  },
  {
    id:          'recovery_analysis',
    label:       'Recovery Analysis',
    shortLabel:  'Recovery',
    description: 'Computing disputable amounts and recovery potential',
    icon:        '⚖️',
    metricKey:   'disputable',
    metricLabel: 'disputable',
    metricFormat: n => `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
  },
  {
    id:          'report',
    label:       'Report Generation',
    shortLabel:  'Report',
    description: 'Persisting leakage events and reconciliation fact',
    icon:        '📊',
    metricKey:   null,
    metricLabel: 'writing results',
    metricFormat: () => 'Writing…',
  },
]

export const STAGE_IDS = PIPELINE_STAGES.map(s => s.id)

/** Status state machine values */
export const STAGE_STATUS = {
  PENDING:   'pending',
  ACTIVE:    'active',
  COMPLETED: 'completed',
  ERROR:     'error',
}

/** Initial state for all stages */
export function initialStageState() {
  return Object.fromEntries(
    PIPELINE_STAGES.map(s => [s.id, { status: STAGE_STATUS.PENDING, metric: null, message: null }])
  )
}

/** Detector display metadata */
export const DETECTOR_META = {
  SHORT:            { label: 'Shortage Claims',      color: '#E8344A' },
  DUPLICATE:        { label: 'Duplicate Deductions',  color: '#E9930D' },
  OTIF:             { label: 'OTIF Penalties',        color: '#F59E0B' },
  ACCRUAL:          { label: 'Accrual Mismatches',    color: '#8B5CF6' },
  COOP:             { label: 'Unauthorized Co-Op',    color: '#EC4899' },
  RETURN:           { label: 'Return Leakage',        color: '#06B6D4' },
  DAMAGE:           { label: 'Damage Overstatement',  color: '#F97316' },
  TIMING:           { label: 'Payment Timing',        color: '#10B981' },
  TAX:              { label: 'Tax Mismatch',          color: '#3B82F6' },
  DISPUTE_RECOVERY: { label: 'Unrecovered Disputes',  color: '#EF4444' },
}
