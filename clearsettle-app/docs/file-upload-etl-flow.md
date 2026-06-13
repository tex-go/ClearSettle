# ClearSettle — File Upload ETL Flow

**Owner:** Engineering  
**Last Updated:** 2026-06-04  
**Status:** Active Reference — consult before any upload/dashboard work

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [End-to-End Upload Sequence](#2-end-to-end-upload-sequence)
3. [Stage Detail: Mobile Upload](#3-stage-detail-mobile-upload)
4. [Stage Detail: Backend Ingestion Pipeline](#4-stage-detail-backend-ingestion-pipeline)
5. [Stage Detail: ETL — Ledger → Dashboard Tables](#5-stage-detail-etl--ledger--dashboard-tables)
6. [Storage Map](#6-storage-map)
7. [Database Tables Involved](#7-database-tables-involved)
8. [The Disconnect Problem](#8-the-disconnect-problem)
9. [Parser Selection Logic](#9-parser-selection-logic)
10. [Status State Machine](#10-status-state-machine)
11. [Verification Checklist](#11-verification-checklist)
12. [Common Failure Modes](#12-common-failure-modes)
13. [API Reference](#13-api-reference)

---

## 1. System Overview

ClearSettle processes marketplace settlement Excel files (Flipkart, Amazon, Meesho) uploaded by sellers. The file goes through:

```
Mobile App → Backend Ingestion API → Detection → Parse → Ledger DB
                                                              ↓
                                                  ETL (MISSING — root cause of ₹0 dashboard)
                                                              ↓
                                               Settlements / Dashboard Tables
```

**Three parallel ingestion systems exist — only System B (new ingestion engine) should be used:**

| System | Routes | Storage | DB Tables | Status |
|--------|--------|---------|-----------|--------|
| A — Legacy | `/flipkart/`, `/amazon/`, `/meesho/` | `/tmp/` ❌ ephemeral | `flipkart_reports`, `amazon_settlement_reports`, `meesho_payment_reports` | Deprecated |
| B — New Ingestion | `/ingestion/` | `/app/uploads/ingestion/` ✅ persistent | `uploaded_files`, `ingestion_ledger` | **Active — use this** |
| C — Dashboard model | Read-only by API | PostgreSQL | `settlements`, `payout_events`, `reconciliation_results` | Fed by ETL (P0 work item) |

---

## 2. End-to-End Upload Sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FLUTTER MOBILE APP                                                          │
│                                                                             │
│  ReportsScreen → pickAndUpload(marketplace='flipkart',                      │
│                                reportType='payment_report')                 │
│    │                                                                        │
│    │ FilePicker.pickFiles(type=custom, extensions=[xlsx,xls], withData=true)│
│    │ Reads file bytes into memory                                           │
│    │                                                                        │
│    ▼                                                                        │
│  CsLogger.uploadStarted(fileName, fileSizeBytes, marketplace)               │
│    │                                                                        │
│    ▼                                                                        │
│  POST /ingestion/upload                                                     │
│    multipart: file=<bytes>, platform=flipkart, report_type=payment_report   │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ NGINX (TLS termination, proxy_pass backend:8000)                            │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASTAPI — ingestion.py  upload_report()                                     │
│                                                                             │
│  [SYNC — request handler]                                                   │
│  1. Validate extension (.xlsx/.xls/.xlsm/.csv/.tsv)                        │
│  2. Validate file size (max 100 MB)                                         │
│  3. SHA-256 hash → check uploaded_files for duplicate                      │
│     └── Duplicate? Return existing file_id immediately                     │
│  4. Write bytes → /app/uploads/ingestion/<uuid>.xlsx                       │
│  5. INSERT uploaded_files (status='uploaded')                               │
│  6. background_tasks.add_task(_run_ingestion, ...)                          │
│  7. Return 202 { id: <file_id>, upload_status: 'uploaded' }                │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │ 202 response → mobile
                          │
          ┌───────────────┴────────────────────────────────┐
          │ [MOBILE — poll loop]                           │ [BACKEND — background task]
          │                                               │
          │ pollUntilDone(fileId,                        │ _run_ingestion()
          │   pollInterval=3s, maxWait=5min)             │
          │                                               │ See Section 4 for full detail
          │ every 3s:                                     │
          │   GET /ingestion/files/{id}                   │
          │   check upload_status                         │
          │   log each tick with elapsed_s               │
          │                                               │
          │ terminal statuses:                            │
          │   done | needs_review | failed               │
          └───────────────┬────────────────────────────────┘
                          │ status == 'done' or 'needs_review'
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MOBILE — fetch results (parallel)                                           │
│                                                                             │
│  GET /ingestion/files/{id}/summary                                          │
│    → gross_revenue, unique_orders, payout_total, returns_total              │
│    → ALL aggregated from ingestion_ledger by transaction_type               │
│                                                                             │
│  GET /ingestion/files/{id}/reconciliation                                   │
│    → expected vs actual per order, discrepancy list                         │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MOBILE — update local Hive cache                                            │
│                                                                             │
│  entry.status        = 'parsed'                                             │
│  entry.totalOrders   = summary.totalOrders                                  │
│  entry.grossRevenue  = summary.grossSales                                   │
│  entry.netSettlement = summary.netEarnings                                  │
│                                                                             │
│  CsLogger.hiveUpdated(reportId, status, totalOrders, grossRevenue, netSettlement)
│   └── WARN if all values are zero                                           │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MOBILE — dashboard refresh                                                  │
│                                                                             │
│  dashboardProvider.refresh()                                                │
│    1. GET /dashboard/summary                                                │
│       Queries: settlements, payout_events, reconciliation_results           │
│       ⚠ These tables are EMPTY unless ETL step runs                        │
│    2. If response all-zeros → falls back to buildFromHiveReports()          │
│       Aggregates from Hive local cache                                      │
│    3. Dashboard shows Hive data (may be stale)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Stage Detail: Mobile Upload

**File:** `mobile/lib/features/reports/presentation/providers/reports_provider.dart`

```
pickAndUpload()
  │
  ├─ FilePicker.pickFiles(withData: true)    ← loads bytes into RAM
  │   └─ Allowed: .xlsx, .xls
  │
  ├─ CsLogger.uploadStarted(fileName, fileSizeBytes, marketplace)
  │
  ├─ _upload(marketplace, reportType, fileName, bytes)
  │   └─ ReportRepositoryImpl.uploadReport()
  │       ├─ Try: remoteDataSource.uploadFile()  ← POST /ingestion/upload
  │       └─ Catch NetworkException / ServerException → localDataSource.saveReport()
  │           (local parse fallback when backend unreachable)
  │
  ├─ state.copyWith(parsingReportId: reportId)
  │
  └─ _parseReport(reportId)
      └─ ReportRepositoryImpl.parseReport()
          ├─ If status == 'backend_processing' → _parseFromBackend()
          │     └─ pollUntilDone() → fetchSummary() → fetchReconciliation()
          └─ If local → localDataSource.parseReport()
              └─ FlipkartParser.parseSync() on local bytes
```

**Critical parameters to always pass:**
```dart
pickAndUpload(
  marketplace: 'flipkart',       // Must match platform_hint
  reportType: 'payment_report',  // Must match report_type_hint
  // Wrong value ('payment_ledger') causes GenericCSVParser fallback
)
```

---

## 4. Stage Detail: Backend Ingestion Pipeline

**File:** `backend/app/routers/ingestion.py` — `_run_ingestion()`  
**File:** `backend/app/services/pipeline/router.py` — `run_ingestion_pipeline()`

```
_run_ingestion(uploaded_file_id, file_bytes, file_name, company_id, ...)
│
├─ STEP 1 [INGESTION 1/6] — Receive & validate
│   UPDATE uploaded_files SET upload_status='detecting'
│   Log: file_id, file_name, file_kb, company_id, platform_hint
│
├─ STEP 2 [INGESTION 2/6] — Detect + Parse
│   run_ingestion_pipeline(file_bytes, file_name, ...)
│   │
│   ├─ fingerprint_file()
│   │   → sheet_names, all_column_names, schema_signature (SHA-256 of columns)
│   │
│   ├─ detect_platform(fingerprint)
│   │   → flipkart | amazon | meesho | unknown
│   │   → confidence_score (0.0–1.0)
│   │   → needs_manual_review = confidence < 0.55
│   │   Uses: filename signals, sheet name signals, column signals, content signals
│   │   ⚠ 'tip_top_payment_report_april2026.xlsx' → was 0.74% (fixed in platform_detector.py)
│   │
│   ├─ detect_report_type(platform, fingerprint)
│   │   → pl_report | payment_report | settlement | order_report
│   │
│   ├─ detect_schema_version(platform, report_type, fingerprint)
│   │   → schema_version (e.g., flipkart_payment_v1)
│   │   → parser_name (e.g., FlipkartPaymentParser)
│   │   → drift_alert if columns don't match known schema
│   │
│   ├─ get_parser(parser_name).parse(file_bytes)
│   │   → ParseResult with ledger_records[]
│   │   Each LedgerRecord:
│   │     platform, report_type, order_id, sku, transaction_type,
│   │     amount, tax_amount, currency, transaction_date, settlement_date
│   │
│   └─ Log: confidence, parser, record_count, tx_type_breakdown, sample[0..2]
│
├─ STEP 3 [INGESTION 3/6] — Intelligence Pipeline
│   IntelligencePipeline.run(...)
│   ⚠ Requires ANTHROPIC_API_KEY — skipped (non-fatal) if not set
│   Logs: duration_ms, likely_cause if skipped
│
├─ STEP 4 [INGESTION 4/6] — Persist detection
│   INSERT report_detection_results (platform, confidence, parser, schema_version)
│   INSERT report_processing_logs (per-stage audit trail)
│
├─ STEP 5 [INGESTION 5/6] — Persist ledger records
│   UPDATE uploaded_files SET upload_status='processing'
│   For each LedgerRecord → INSERT ingestion_ledger
│   Log: tx_type_breakdown dict, WARNING if all types are 'sale'
│
└─ STEP 6 [INGESTION 6/6] — Finalise status
    Status logic:
      needs_manual_review AND no records → 'needs_review'
      errors AND no records             → 'failed'
      otherwise                         → 'done'
    UPDATE uploaded_files SET upload_status=<final>, processed_at=NOW()
    Log: final_status, platform, parser, ledger_count, total_duration_ms

    ⚠ MISSING AFTER THIS STEP:
    ETL: ingestion_ledger → settlements + payout_events
    Until this is implemented, dashboard always shows ₹0
```

---

## 5. Stage Detail: ETL — Ledger → Dashboard Tables

**Status:** ⚠ NOT IMPLEMENTED (P0 work item)

This is the missing step that causes the dashboard to show ₹0 even after a successful upload.

### What Needs to Happen

After STEP 5 (ledger persisted), a new STEP 5b must run:

```
ingestion_ledger rows (N rows per file)
    │
    ├─ GROUP by transaction_type:
    │   sale / sold / my_share   → gross_revenue
    │   return / refund          → returns_total
    │   fee / commission         → fees_total
    │   tax / tds / tcs / gst   → tax_total
    │   payout / bank_settlement / neft → payout_total
    │
    ▼
settlements (1 row per file)
    id, company_id, platform, status='closed'
    total_amount = gross_revenue
    fund_transfer_amount = payout_total
    fees_total = fees_total
    source = 'file_upload'
    uploaded_file_id = <trace back to source>
    │
    ▼
payout_events (1 row if payout_total > 0)
    id, company_id, settlement_id
    amount = payout_total
    status = 'transferred'
```

### Implementation Location

Add `_populate_settlements_from_ledger()` to `backend/app/routers/ingestion.py`, called from `_run_ingestion()` after STEP 5 and before STEP 6.

### Transaction Type Mapping Reference

| Raw transaction_type from parser | Maps to | Dashboard field |
|----------------------------------|---------|-----------------|
| `sale`, `sold`, `my_share` | `gross_revenue` | Total GMV |
| `return`, `returned`, `refund` | `returns_total` | Returns deduction |
| `fee`, `commission`, `fixed_fee`, `shipping_fee`, `reverse_shipping`, `collection_fee` | `fees_total` | Marketplace fees |
| `tax`, `tds`, `tcs`, `gst`, `tax_tds`, `tax_tcs` | `tax_total` | Tax deductions |
| `payout`, `settlement`, `transfer`, `bank_settlement`, `net_settlement`, `neft` | `payout_total` | Net settlement received |

> **WARNING:** If `transaction_type = 'sale'` for ALL rows (GenericCSVParser fallback), `payout_total = 0` and `net_settlement` will be calculated as `gross - fees - taxes` (estimated). This is flagged in ingestion logs as:
> ```
> WARNING_if_all_sale: "ALL records have tx_type=sale — verify column mapping"
> ```

---

## 6. Storage Map

```
/opt/clearsettle/
└── uploads/
    └── ingestion/                    ← persistent, host volume → /app/uploads/ingestion
        └── <uuid>.xlsx               ← original uploaded file, retained indefinitely

[DEPRECATED — use above instead]
/tmp/
├── flipkart_uploads/                 ← EPHEMERAL, wiped on container restart
├── amazon_uploads/                   ← EPHEMERAL, wiped on container restart
├── meesho_uploads/                   ← EPHEMERAL, wiped on container restart
└── recon_uploads/                    ← EPHEMERAL, wiped on container restart

PostgreSQL (clearsettle DB)
├── uploaded_files                    ← registry: file_id, hash, status, storage_path
├── report_detection_results          ← platform, confidence, parser chosen
├── report_processing_logs            ← per-stage audit logs (fingerprint/detect/parse)
└── ingestion_ledger                  ← N rows per file, normalized transactions

Mobile (Android app data dir)
└── hive/
    ├── local_reports_box             ← report list with status, grossRevenue, netSettlement
    ├── report_summaries_box          ← aggregated KPIs per report
    └── dashboard_cache_box           ← cached dashboard summary
```

### UPLOAD_DIR Environment Variable

```
docker-compose.prod.yml sets:
  UPLOAD_DIR: /app/uploads/ingestion

ingestion.py reads:
  UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/ingestion_uploads")
                                             ↑ fallback only, never used in prod

Legacy routers HARDCODED (fix needed):
  flipkart_reports.py:58  → UPLOAD_DIR = "/tmp/flipkart_uploads"
  amazon_reports.py:50    → UPLOAD_DIR = "/tmp/amazon_uploads"
  meesho_reports.py:50    → UPLOAD_DIR = "/tmp/meesho_uploads"
  vendor_recon.py:53      → UPLOAD_DIR = "/tmp/recon_uploads"
```

---

## 7. Database Tables Involved

### Upload Pipeline Tables (System B — new ingestion)

| Table | Rows per upload | Purpose | Key columns |
|-------|----------------|---------|-------------|
| `uploaded_files` | 1 | File registry, status tracking | id, file_hash_sha256, upload_status, storage_path |
| `report_detection_results` | 1 | Platform/parser/confidence | detected_platform, confidence_score, parser_name, needs_manual_review |
| `report_processing_logs` | N | Per-stage audit trail | stage, level, message, context (JSONB) |
| `ingestion_ledger` | N (one per transaction row) | Normalized ledger | transaction_type, amount, order_id, sku, platform |

### Dashboard Tables (System C — must be populated by ETL)

| Table | Must be populated by | Currently populated? | Dashboard query |
|-------|---------------------|---------------------|----------------|
| `settlements` | ETL from ingestion_ledger | ❌ No | `/dashboard/summary` → total GMV, platform share |
| `settlement_transactions` | ETL from ingestion_ledger | ❌ No | Analytics queries |
| `payout_events` | ETL from ingestion_ledger | ❌ No | `/dashboard/summary` → net payout |
| `reconciliation_results` | Recon engine | ❌ No (engine never triggered from upload) | Health score |
| `discrepancy_events` | Recon engine or manual | ⚠ Manual only | Disputes screen |

### Migration Status

| Migration | What it adds | Status |
|-----------|-------------|--------|
| 007 | `discrepancy_events`, `reconciliation_results`, `reconciliation_rules` | ✅ Applied |
| 029 | `source`, `workflow_state`, `filed_at`, `filed_by` to `discrepancy_events` | ✅ Applied |
| 031 | `uploaded_files`, `ingestion_ledger`, `report_detection_results`, etc. | ✅ Applied |
| **035** | `sku` column on `discrepancy_events` (was missing, caused crashes) | ✅ Applied |

---

## 8. The Disconnect Problem

```
                    WHAT GETS WRITTEN          WHAT DASHBOARD READS
                    ─────────────────          ────────────────────
After upload:       uploaded_files             settlements           ← EMPTY
                    report_detection_results   payout_events         ← EMPTY
                    report_processing_logs     reconciliation_results ← EMPTY
                    ingestion_ledger (529 rows) discrepancy_events   ← EMPTY

Result:  User uploads file → API says "done" → Dashboard shows ₹0.00
```

### Why Mobile Report Card Shows Non-Zero (Sometimes)

The mobile report card reads from **Hive local cache**, not the dashboard API:

```
Mobile upload completes
  → fetchSummary(/ingestion/files/{id}/summary)    ← reads ingestion_ledger ✅
  → Updates Hive: entry.grossRevenue = X
  → Report card reads from Hive → shows X ✅

Dashboard screen
  → GET /dashboard/summary                         ← reads settlements table ❌
  → settlements table is empty
  → DashboardProvider falls back to buildFromHiveReports()
  → Aggregates from Hive → shows X (from Hive, not DB)
  → Appears to work but is NOT sourced from the live DB
```

This means **deleting the app, reinstalling, or logging in from a different device shows ₹0** because Hive data is lost.

---

## 9. Parser Selection Logic

```
upload(platform_hint='flipkart', report_type_hint='payment_report')
    │
    ▼
fingerprint_file(bytes)
    → sheet_names: ['Orders', 'GST_Details', 'NEFT_Summary', ...]
    → schema_signature: SHA-256 of sorted lowercase column names
    │
    ▼
detect_platform(fingerprint)
    Score signals (substring match, case-insensitive):

    FILENAME signals (e.g., 'tip_top_payment_report_april2026.xlsx'):
      'payment_report' → +8 pts   ← matches 'payment_report' in filename ✅
      'flipkart'       → +9 pts   ← not in filename

    SHEET signals:
      'gst_details'   → +7 pts   ← if sheet name matches
      'neft_summary'  → +8 pts   ← if sheet name matches
      'payment details' → +7 pts

    COLUMN signals (from all sheets):
      'bank settlement value' → +9 pts
      'neft id'               → +8 pts
      'sale amount (rs.)'     → +8 pts
      'tcs (rs.)'             → +7 pts
      'reverse shipping fee'  → +8 pts

    confidence = raw_score / theoretical_max_score
    needs_manual_review = confidence < 0.55
    │
    ▼ flipkart detected (confidence > 0.55)
    │
    ▼
detect_report_type('flipkart', fingerprint)
    → 'payment_report'
    │
    ▼
detect_schema_version('flipkart', 'payment_report', fingerprint)
    → parser_name = 'FlipkartPaymentParser'
    │
    ▼
FlipkartPaymentParser.parse(file_bytes)
    → Reads 3-level merged header (Payment Details / column names / sub-headers)
    → Extracts: order_id, sale_amount, bank_settlement, tcs, tds, commission, etc.
    → Creates LedgerRecord per row:
        transaction_type = 'sale' (or 'return' if return_type column set)
        amount = sale_amount (falls back to my_share if sale_amount = 0)
    → Returns ParseResult with 529 ledger_records (for tip_top April 2026)
```

### Parser Registry

| Platform | Report Type | Parser Class | File |
|----------|------------|-------------|------|
| flipkart | pl_report | FlipkartPLParser | `services/parsers/flipkart/pl_parser.py` |
| flipkart | payment_report | FlipkartPaymentParser | `services/parsers/flipkart/payment_parser.py` |
| amazon | settlement | AmazonSettlementParser | `services/parsers/amazon/settlement_parser.py` |
| meesho | payment_report | MeeshoPaymentParser | `services/parsers/meesho/payment_parser.py` |
| myntra | * | MyntraParser (generic) | `services/parsers/generic_parser.py` |
| ajio | * | AjioParser (generic) | `services/parsers/generic_parser.py` |
| unknown | * | GenericCSVParser | `services/parsers/generic_parser.py` |

> **GenericCSVParser fallback warning:** When this parser runs, `transaction_type` defaults to `"sale"` for ALL rows. `payout_total` will always be 0. Net settlement is estimated as `gross - fees - taxes`, which will be inaccurate.

---

## 10. Status State Machine

### Backend `upload_status` (uploaded_files table)

```
uploaded → detecting → processing → done
                                 ↘ needs_review   (low confidence, no records)
                    ↘ failed                       (parse error + no records)
```

| Status | Meaning | Mobile action |
|--------|---------|---------------|
| `uploaded` | File received, pipeline starting | Continue polling |
| `detecting` | Platform detection running | Continue polling |
| `processing` | Ledger rows being written to DB | Continue polling |
| `done` | All steps complete, data available | Fetch summary |
| `needs_review` | Low confidence but data exists | Fetch summary (data may be partial) |
| `failed` | Pipeline error, no useful data | Show error + retry button |

### Mobile `entry.status` (Hive local_reports_box)

```
backend_processing → parsed
                  ↘ failed
```

| Status | Source | Display |
|--------|--------|---------|
| `backend_processing` | Set on upload | "Processing..." spinner |
| `parsed` | Set after fetchSummary completes | Report card with financials |
| `failed` | Set if poll/fetch fails | Error row + retry button |

---

## 11. Verification Checklist

Use this checklist after any upload-related code change.

### Upload API Verification

```bash
# 1. Upload file and capture file_id
FILE_ID=$(curl -s -X POST https://clearsettle.in/api/ingestion/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tip_top_payment_report_april2026.xlsx" \
  -F "platform=flipkart" \
  -F "report_type=payment_report" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "file_id: $FILE_ID"

# 2. Poll until done
watch -n3 "curl -s https://clearsettle.in/api/ingestion/files/$FILE_ID \
  -H 'Authorization: Bearer $TOKEN' | python3 -c \
  \"import sys,json; d=json.load(sys.stdin); print(d.get('upload_status'), d.get('detection',{}).get('detected_platform'), d.get('detection',{}).get('confidence_score'))\""

# 3. Check summary — verify non-zero values
curl -s https://clearsettle.in/api/ingestion/files/$FILE_ID/summary \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Expected:
# "gross_revenue": 125342.0,   ← must NOT be 0
# "unique_orders": 529,         ← must NOT be 0
# "payout_total": 86925.0      ← must NOT be 0

# 4. Check ledger row count
curl -s "https://clearsettle.in/api/ingestion/files/$FILE_ID/ledger?limit=1" \
  -H "Authorization: Bearer $TOKEN" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('total ledger rows:', d.get('total'))"

# 5. Check dashboard (should reflect upload after ETL is implemented)
curl -s https://clearsettle.in/api/dashboard/summary \
  -H "Authorization: Bearer $TOKEN" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('dashboard gross:', d.get('total_gmv') or d.get('gross_revenue'))"
```

### Database Verification

```sql
-- Check uploaded_files for latest upload
SELECT id, original_file_name, upload_status, processed_at
FROM uploaded_files
ORDER BY uploaded_at DESC LIMIT 5;

-- Check ledger row count and transaction_type breakdown
SELECT transaction_type, COUNT(*), SUM(amount)
FROM ingestion_ledger
WHERE uploaded_file_id = '<file_id>'
GROUP BY transaction_type;

-- WARN: If only 'sale' rows exist with no 'payout' rows,
-- net_settlement will be estimated (not from bank_settlement column)

-- Verify settlements were populated (ETL step)
SELECT COUNT(*), SUM(total_amount), SUM(fund_transfer_amount)
FROM settlements
WHERE source = 'file_upload';
-- Should be non-zero after ETL is implemented

-- Check discrepancy_events.sku exists (migration 035)
SELECT column_name FROM information_schema.columns
WHERE table_name = 'discrepancy_events' AND column_name = 'sku';
```

### Mobile Verification (ADB Logs)

```bash
adb logcat -s ClearSettle flutter 2>&1 | grep -E "INGESTION|summary|Hive|ZERO|confidence"

# Expected log sequence for successful upload:
# [INFO]  Upload  UPLOAD STARTED: tip_top_payment_report_april2026.xlsx
# [INFO]  Upload  Sending to backend API  bytes=245760
# [INFO]  Upload  Backend accepted file  status=uploaded  platform=flipkart  confidence=0.8200
# [INFO]  Poll    Poll #1 response  status=detecting  elapsed_s=3
# [INFO]  Poll    Poll #2 response  status=processing  elapsed_s=6
# [INFO]  Poll    Processing complete  final_status=done  total_seconds=18
# [INFO]  Summary Raw summary response  gross_revenue=125342.0  unique_orders=529
# [INFO]  Hive    Local cache updated  grossRevenue=125342.00  netSettlement=86925.00
```

### Backend Log Verification

```bash
docker logs clearsettle-backend-prod 2>&1 | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        msg = d.get('message', '')
        if 'INGESTION' in msg or 'confidence' in str(d) or 'ledger' in msg.lower():
            print(d.get('severity','?')[:4], '|', msg[:100])
            extra = {k:v for k,v in d.items() if k not in ('severity','message','timestamp','logger','module','line')}
            if extra: print('     ', extra)
    except: pass
" 2>&1 | head -60

# Look for:
# INFO | INGESTION[2/6] Detection complete
#       {'platform': 'flipkart', 'confidence': 0.82, 'parser': 'FlipkartPaymentParser'}
# INFO | INGESTION[5/6] Ledger records written
#       {'records_written': 529, 'tx_type_breakdown': {'sale': 400, 'return': 92, 'payout': 37, ...}}
# WARN | INGESTION[5/6] ...
#       {'WARNING_if_all_sale': 'ALL records have tx_type=sale — verify column mapping'}
```

---

## 12. Common Failure Modes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Dashboard shows ₹0 after upload | ETL not implemented — `settlements` table empty | Implement `_populate_settlements_from_ledger()` |
| `gross_revenue = 0` in summary | All ledger rows have unknown `transaction_type` | Check parser selection; force `platform_hint=flipkart` |
| Platform confidence < 0.55 → GenericCSVParser | Filename doesn't match signals | Add `payment_report` to filename signals (done in platform_detector.py) |
| `summary.payout_total = 0` | Parser didn't find `bank_settlement` column | Add `my_share` fallback (done in payment_parser.py) |
| `asyncpg.exceptions.UndefinedColumnError: sku` | Migration 035 not applied | Run `alembic upgrade head` on GCP |
| `401 Invalid credentials` on admin | SHA-256 hash stored, bcrypt expected | Run `reset_admin_password.py` in backend container |
| Files lost after container restart | Legacy routers use `/tmp/` | Change to `os.environ.get("UPLOAD_DIR", "/app/uploads/<service>")` |
| `status = needs_review` | Platform confidence < 0.55 | Data still available; `fetchSummary` still works |
| Mobile shows "0B" file size | Duplicate upload response missing `file_size_bytes` | Fixed in ingestion.py duplicate response |
| Poll timeout after 5 min | `IntelligencePipeline` hanging (no Anthropic key) | Pipeline continues after intel failure; check logs |

---

## 13. API Reference

### Upload & Processing Endpoints

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| `POST` | `/ingestion/upload` | Upload file, start pipeline | `202 { id, upload_status: 'uploaded' }` |
| `GET` | `/ingestion/files/{id}` | Poll status | `{ upload_status, detection: { detected_platform, confidence_score } }` |
| `GET` | `/ingestion/files/{id}/summary` | Financial KPIs from ledger | `{ gross_revenue, unique_orders, payout_total, ... }` |
| `GET` | `/ingestion/files/{id}/reconciliation` | Discrepancy list | `{ items[], summary: { total_issues, recoverable } }` |
| `GET` | `/ingestion/files/{id}/ledger` | Raw ledger rows | `{ items[], total }` |
| `GET` | `/ingestion/files/{id}/detection` | Parser selection detail | `{ parser_name, confidence_score, ledger_records_count }` |
| `GET` | `/ingestion/files/{id}/logs` | Processing audit trail | `{ items[] }` |
| `POST` | `/ingestion/files/{id}/reprocess` | Re-run pipeline | `202` |
| `DELETE` | `/ingestion/files/{id}` | Delete file + derived data | `204` |
| `GET` | `/ingestion/files/{id}/report` | HTML analytics report | `text/html` |
| `GET` | `/ingestion/files/{id}/export` | Download ledger as CSV | `text/csv` |

### Dashboard Endpoints (reads from settlements — needs ETL)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/dashboard/summary` | Main KPIs (GMV, settlements, disputes) |
| `GET` | `/dashboard/notifications` | Live alert feed |

### Mobile SDK Endpoints (api_endpoints.dart)

```dart
ApiEndpoints.ingestionUpload          → '/ingestion/upload'
ApiEndpoints.ingestionFile(id)        → '/ingestion/files/$id'
ApiEndpoints.ingestionSummary(id)     → '/ingestion/files/$id/summary'
ApiEndpoints.ingestionReconciliation  → '/ingestion/files/$id/reconciliation'
ApiEndpoints.ingestionReport(id)      → '/ingestion/files/$id/report'
```

---

## Related Files

| File | Role |
|------|------|
| `backend/app/routers/ingestion.py` | Upload endpoint + background pipeline task |
| `backend/app/services/pipeline/router.py` | Detection → Parse orchestration |
| `backend/app/services/detection/platform_detector.py` | Platform signal scoring |
| `backend/app/services/parsers/flipkart/payment_parser.py` | Flipkart payment report parser |
| `backend/app/services/parsers/registry.py` | Parser name → class mapping |
| `backend/app/db/models/ingestion.py` | UploadedFile, IngestionLedger ORM models |
| `backend/app/routers/dashboard.py` | Dashboard summary (reads settlements) |
| `backend/alembic/versions/035_add_sku_to_discrepancy_events.py` | Bug fix migration |
| `mobile/lib/features/reports/presentation/providers/reports_provider.dart` | Upload flow orchestration |
| `mobile/lib/features/reports/data/datasources/report_remote_datasource.dart` | API calls + logging |
| `mobile/lib/features/reports/data/repositories/report_repository_impl.dart` | Backend vs local routing |
| `mobile/lib/features/dashboard/presentation/providers/dashboard_provider.dart` | Dashboard data loading + Hive fallback |
| `mobile/lib/core/utils/cs_logger.dart` | Structured upload-flow logger |
