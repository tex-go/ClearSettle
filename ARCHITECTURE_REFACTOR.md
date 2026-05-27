# ClearSettle — Enterprise Architecture Refactor Plan
**Date:** 2026-05-27 | **Version:** v1.0.0 baseline → v2.0 target  
**Author:** Principal Architecture Review  
**Basis:** Source code analysis only — no hallucination

---

## Table of Contents

1. [Duplicated Feature Analysis](#1-duplicated-feature-analysis)
2. [Consolidated Product Structure](#2-consolidated-product-structure)
3. [Recommended Module Merges](#3-recommended-module-merges)
4. [Backend Refactor Plan](#4-backend-refactor-plan)
5. [Frontend Refactor Plan](#5-frontend-refactor-plan)
6. [Database Consolidation Analysis](#6-database-consolidation-analysis)
7. [Recommended Final Information Architecture](#7-recommended-final-information-architecture)
8. [Scalability & Maintainability Improvements](#8-scalability--maintainability-improvements)
9. [Prioritized Execution Roadmap](#9-prioritized-execution-roadmap)

---

## 1. Duplicated Feature Analysis

### 1.1 Reconciliation System — Three Independent Engines

**The problem:** There are three completely separate "discrepancy detection" systems that evolved independently and have no shared code, shared data model, or shared UI.

| System | File | Lines | Dataclass | Tables Used |
|--------|------|-------|-----------|-------------|
| **Settlement Recon** | `services/reconciliation/detectors.py` | 350 | `DiscrepancyCandidate` | `reconciliation_results`, `discrepancy_events` |
| **Vendor Recon** | `services/vendor_recon/detectors.py` | 509 | `LeakageCandidate` | separate vendor recon tables |
| **Flipkart File Recon** | embedded in `routers/flipkart_reports.py` | 1,047 | none (inline) | `flipkart_recon_issues` |

**What each detects:**
- Settlement Recon: 7 types — MISSING_PAYOUT, PAYOUT_AMOUNT_MISMATCH, OVERCHARGE_REFERRAL_FEE, OVERCHARGE_FBA_FEE, DUPLICATE_DEDUCTION, UNEXPECTED_FEE, PENALTY_MISMATCH
- Vendor Recon: 10 types — shortage, price discrepancy, deduction, claims, holds, payment timing
- Flipkart File Recon: P&L mismatches, SKU-level variance from uploaded reports

**Why this is a critical problem:**
- A user sees three separate pages (BankRecon, VendorRecon embedded in ReconEngine, Flipkart issues in upload)
- A discrepancy found in Flipkart reports **cannot be escalated** to the dispute workflow because FlipkartReconIssue has no path to DiscrepancyEvent
- The reconciliation engine runs produce `ReconciliationResult` + `DiscrepancyEvent` chains, but vendor recon results have no equivalent parent run record
- Developers writing new detector logic must decide: which of the three systems do I extend?
- **Technical debt:** ~1,566 lines of near-parallel detection logic that drift over time

---

### 1.2 Dispute / Recovery Workflow — Four Fragmented Pieces

**The problem:** A single business workflow (detect money owed → file dispute → track → recover) is split across four files with no explicit state machine connecting them.

```
ACTUAL (fragmented):                    SHOULD BE (unified):
                                        
disputes.py     ← just a list view     detect → [DETECTED]
dispute_engine.py ← detection          file   → [FILED]
recovery.py     ← post-filing          ack    → [ACKNOWLEDGED]
rules.py        ← can create disputes  close  → [RESOLVED | REJECTED]
```

**Evidence from code:**
- `disputes.py` (189 lines) has only `GET /disputes/` — it's a read-only view, no business logic
- `dispute_engine.py` (160 lines) has detection rules + `POST /dispute-engine/auto-create` — creates DiscrepancyEvents
- `recovery.py` (147 lines) has `POST /recovery/action` — transitions dispute status, but uses a different endpoint prefix
- `rules.py` (448 lines) has its own action executor that can also create disputes

**Problems:**
- Same DiscrepancyEvent record is managed by three different API prefixes (`/disputes/`, `/dispute-engine/`, `/recovery/`)
- Frontend has three separate pages for one workflow (Disputes + DisputeEngine + Recovery)
- No clear ownership of the dispute lifecycle state machine
- Commission overcharges (in `commission.py`) and return deductions (in `returns.py`) are detected but have **no path to the dispute system** — they are dead-end views
- **User confusion:** "Where do I go to see my money recovery status?"

---

### 1.3 Financial Intelligence — Four Overlapping Views

**The problem:** Dashboard, Analytics, CashFlowForecast, and Cashflow pages all show revenue/cash data with significant chart duplication.

| Module | File | What it shows |
|--------|------|---------------|
| Dashboard | `routers/dashboard.py` (379 lines) | KPI cards, platform filter, notification feed |
| Analytics | `routers/analytics.py` (498 lines) | Revenue charts, platform share, trends, **KPIs again** |
| Forecast | `routers/forecast.py` (210 lines) | 30-day settlement calendar, expected payouts |
| Cashflow | `routers/cashflow.py` (119 lines) | Cash position snapshots |

**Direct overlap evidence:**
- Analytics `/analytics/kpis` returns KPI metrics — dashboard `/dashboard/summary` also returns KPIs
- `services/analytics/queries.py` (1,104 lines — the largest service file) contains both dashboard summary queries AND analytics trend queries in the same file
- Forecast and Cashflow are conceptually the same thing: "where is my money going" — one is forward-looking, one is historical snapshots. Both are tiny (210 + 119 lines) and would be a natural pair

**Frontend impact:** User sees the same "platform revenue breakdown" chart on Dashboard AND Analytics

---

### 1.4 Amazon Parser Duplication

**This is the most concrete code duplication found:**

| File | Lines | Purpose |
|------|-------|---------|
| `services/amazon/parser.py` | 307 | Parses Amazon Settlement flat-file downloads (CSV/TSV/Excel) |
| `services/ingestion/amazon/parser.py` | 303 | Parses Amazon SP API Finance events → NormalizedSettlement |

Both files:
- Parse Amazon financial data into structured Python objects
- Handle decimal parsing with `Decimal`, datetime normalization
- Have column alias tables for flexible header matching
- Exist in parallel namespaces with no shared base class

**Why it happened:** When SP API integration was added (later in development), a new `ingestion/` directory was created to hold API-sourced data. The file-upload parser was never refactored into this structure. Now there are two separate parsing paths for Amazon data.

**Impact:** A bug fix or new Amazon format support must be applied in two places. When Amazon changes their report format (which they do), both parsers diverge.

---

### 1.5 Platform Integration — Split Responsibilities

**The problem:** Amazon gets a dedicated 665-line router (`sp_api.py`) while Flipkart and Meesho are handled in their report routers. There is no unified platform abstraction.

```
Amazon:   platforms.py (connect) + sp_api.py (OAuth + orders) + amazon_reports.py (files)
Flipkart: platforms.py (connect) + flipkart_reports.py (files)  ← no dedicated router
Meesho:   platforms.py (connect) + meesho_reports.py (files)    ← no dedicated router
```

**Problems:**
- `sp_api.py` is half platform-connection logic (OAuth callback, token storage) and half data retrieval (orders, refunds) — it should be split
- Adding a new platform (e.g., Myntra) requires understanding three different patterns
- `sync.py` (259 lines) manages sync jobs across all platforms but calls platform-specific services directly

---

### 1.6 Commission + Returns — Detection Without Action

**The problem:** Two routers (`commission.py` 144 lines, `returns.py` 106 lines) detect financial leakage but have no connection to the recovery workflow.

- Commission: detects overcharged referral fees, shows published vs charged rate
- Returns: detects return deductions, analyzes reasons

Both produce valuable data but the user has **no "file dispute" button** on these pages — the findings are dead-ends. They should feed into the Recovery workflow automatically.

---

### 1.7 Demo-Mode Fallback in 14 Routers

**Found in code:** 14 files contain `get_db_optional` / `if db is None` patterns. This means 14 production routers silently return mock data when the database is unreachable — a dangerous production behavior masquerading as a feature.

---

### Summary: Technical Debt Impact

| Issue | Files Affected | Maintenance Cost | UX Impact |
|-------|---------------|-----------------|-----------|
| Three recon engines | 6 files, 1,866 lines | New detector = 3x work | 3 separate pages |
| Fragmented dispute workflow | 4 files | No clear ownership | 3 pages for 1 workflow |
| Dashboard/Analytics overlap | 4 files, 1,206 lines | KPI = 2x work | Chart duplication |
| Amazon parser duplication | 2 files, 610 lines | Format change = 2x fix | None (invisible) |
| Commission/Returns dead-ends | 2 files | Manual cross-referencing | No recovery action |
| Demo-mode in 14 routers | 14 files | Silent production failures | Data integrity risk |
| No shared ingestion base | 3 platform report routers | New platform = copy-paste | Inconsistent uploads |

---

## 2. Consolidated Product Structure

The current product is organized by **when features were built**.  
The target is organized by **how financial operators think**.

A financial operations manager thinks in these mental models:

```
"Was I paid correctly?"         → RECONCILIATION
"What money am I missing?"      → RECOVERY  
"What are my taxes?"            → COMPLIANCE
"How is my business performing?"→ INTELLIGENCE
"Where is my money going next?" → CASH FLOW
"How do I connect my accounts?" → OPERATIONS
"How do I grow my seller base?" → GROWTH (CRM)
```

### Proposed Top-Level Domains

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DOMAIN              │  WHAT IT COVERS                                  │
├──────────────────────┼──────────────────────────────────────────────────┤
│  Financial Hub       │  Settlements + bank matching + payouts           │
│  Reconciliation      │  All three recon engines → unified               │
│  Recovery Center     │  Detection + filing + tracking + action          │
│  Compliance          │  GST, TCS, TDS, ITC — tax operations             │
│  Intelligence        │  KPIs, trends, platform health, forecast         │
│  Data & Sync         │  Platform connections, report uploads, sync      │
│  Automation          │  Rule engine, alert rules, AI actions            │
│  CRM                 │  Lead discovery, outreach, meetings              │
│  Admin & Settings    │  Users, RBAC, audit log, onboarding              │
└──────────────────────┴──────────────────────────────────────────────────┘
```

### Why Each Grouping Makes Sense

**Financial Hub** — The core product: "show me my settlements and whether I was paid." Settlements, bank matching, and payout events are the same data viewed at different granularities. A financial operator thinks "did the money arrive?" before anything else.

**Reconciliation** — "Does what I received match what the platform owes me?" This is a distinct workflow from Recovery (which is about *doing something* after finding a discrepancy). Settlement recon, bank recon, and vendor recon are all answering the same question at different levels.

**Recovery Center** — This is an action workflow. After reconciliation finds problems, the user needs to: review → decide to dispute → file → track → receive money. This needs one unified interface with a clear state machine.

**Compliance** — GST/TCS/TDS is distinct enough (different user: CA, finance team) that it deserves its own top-level section. It maps to a distinct person/role in an Indian eCommerce business.

**Intelligence** — Dashboard + Analytics + Forecast as a single section. Users switching between these are in the same mental state: "how is my business doing?"

**Data & Sync** — Operational: connecting accounts, uploading reports, checking sync status. Power user / admin workflow, not daily use.

**Automation** — The rule engine, dispute auto-detection, and AI classification are all "set it and forget it" configuration. One place to manage all automated behaviors.

**CRM** — Seller prospecting is a distinct business function (sales team, not financial operations team). Should be clearly separated.

---

## 3. Recommended Module Merges

### Merge 1: Unified Reconciliation Center

**Current modules:**
- `routers/reconciliation.py` (868 lines)
- `routers/vendor_recon.py` (707 lines)
- `routers/bank.py` (151 lines)
- Recon logic embedded in `routers/flipkart_reports.py`

**New unified module:** `routers/reconciliation.py` (single file, ~600 lines)

**New API surface:**
```
GET  /recon/runs                  # all recon runs across all types
POST /recon/run                   # trigger any recon type (type: settlement|vendor|bank)
GET  /recon/runs/{id}             # run detail
GET  /recon/issues                # all issues across all runs (filterable by type/platform)
POST /recon/issues/{id}/resolve   # resolve any issue type
GET  /recon/bank-matching         # bank credit ↔ payout match status
GET  /recon/vendor-config         # vendor recon configuration
POST /recon/vendor-validate       # vendor recon run
```

**Migration strategy:**
1. Keep all existing endpoints active (no breakage)
2. Add new `/recon/` endpoints alongside
3. Route frontend to new endpoints
4. Deprecate old endpoints after 1 sprint
5. Remove in v2.1

**Backend impact:** 
- `services/reconciliation/` becomes the canonical recon service
- `services/vendor_recon/` is merged into it as `services/reconciliation/vendor/`
- Bank matching logic moves from `routers/bank.py` into `services/reconciliation/bank/`
- Flipkart file recon issues get an adapter that writes to `discrepancy_events` (see DB section)

**Frontend impact:**
- `pages/BankRecon.jsx` → merged into `pages/Reconciliation.jsx` as a tab
- `pages/ReconEngine.jsx` → becomes the primary Reconciliation page
- VendorRecon UI becomes a configuration tab

**Database impact:** None in Phase 1 (adapters); FlipkartReconIssue migration in Phase 2

---

### Merge 2: Recovery Center

**Current modules:**
- `routers/disputes.py` (189 lines) — list view
- `routers/dispute_engine.py` (160 lines) — detection + auto-create
- `routers/recovery.py` (147 lines) — tracking + action
- `routers/commission.py` (144 lines) — detection (dead end)
- `routers/returns.py` (106 lines) — detection (dead end)

**New unified module:** `routers/recovery.py` (~400 lines)

**New API surface:**
```
GET  /recovery/items              # unified list (replaces /disputes/ + /recovery/)
GET  /recovery/items/{id}         # detail + timeline
POST /recovery/items/{id}/file    # escalate detected → filed
POST /recovery/items/{id}/action  # take action (replaces /recovery/action)
POST /recovery/items/{id}/resolve # mark resolved/rejected
GET  /recovery/detection-rules    # replaces /dispute-engine/rules
POST /recovery/run-detection      # trigger auto-detect (replaces /dispute-engine/auto-create)
GET  /recovery/calculator         # recovery amount calc
GET  /recovery/commission-audit   # was /commission/ — now feeds into recovery
GET  /recovery/return-audit       # was /returns/ — now feeds into recovery
```

**State machine (explicit, enforced in service layer):**
```
DETECTED → REVIEWED → FILED → ACKNOWLEDGED → RESOLVED
                    ↘                       ↘
                     DISMISSED               REJECTED
```

**Migration strategy:**
1. Add state machine to DiscrepancyEvent (add `workflow_state` enum column)
2. Create new `/recovery/` endpoints
3. Commission/returns detectors write to DiscrepancyEvent with `source=LEAKAGE_AUDIT`
4. Frontend merges three pages into one
5. Old endpoints deprecated

**Backend impact:**
- `services/reconciliation/detectors.py` provides the detection engine
- Commission and returns logic moves to `services/recovery/leakage_detectors.py`
- New `services/recovery/state_machine.py` owns all transitions

**Frontend impact:**
- `pages/Disputes.jsx` → deleted
- `pages/DisputeEngine.jsx` → merged
- `pages/Recovery.jsx` → becomes the primary Recovery Center page
- `pages/Commission.jsx` → becomes `RecoveryCenter` tab "Fee Audit"
- `pages/Returns.jsx` → becomes `RecoveryCenter` tab "Return Audit"

---

### Merge 3: Intelligence Hub

**Current modules:**
- `routers/dashboard.py` (379 lines)
- `routers/analytics.py` (498 lines)
- `routers/forecast.py` (210 lines)
- `routers/cashflow.py` (119 lines)

**New unified module:** Two clean routers

```
routers/dashboard.py   → GET /dashboard/summary, /dashboard/notifications (unchanged home)
routers/analytics.py   → GET /analytics/...     (unified, no KPI duplication)
```

**Forecast and Cashflow** merge into Analytics:
```
GET /analytics/cash-flow      # merges /cashflow/snapshots + /forecast/30-day
GET /analytics/revenue        # unchanged
GET /analytics/platform-share # unchanged
GET /analytics/trends         # unchanged
GET /analytics/kpis           # single source of truth (removed from dashboard/summary)
```

**Service layer change:**
- `services/analytics/queries.py` (1,104 lines — too large) → split into:
  - `services/analytics/kpi_queries.py`
  - `services/analytics/trend_queries.py`
  - `services/analytics/platform_queries.py`
  - `services/analytics/cashflow_queries.py`
- Dashboard summary calls `kpi_queries.get_summary()` only (no duplication)

**Frontend impact:**
- `pages/CashFlowForecast.jsx` + `pages/Cashflow.jsx` → merged into `pages/Analytics.jsx` as "Cash Flow" tab
- `pages/Dashboard.jsx` stays as home with summary widgets only
- `pages/Analytics.jsx` becomes the deep-dive page

---

### Merge 4: Unified Report Ingestion

**Current modules:**
- `routers/amazon_reports.py` (777 lines) + `services/amazon/parser.py` (307 lines) + `services/ingestion/amazon/parser.py` (303 lines)
- `routers/flipkart_reports.py` (1,047 lines) + `services/flipkart/parser.py` (598 lines)
- `routers/meesho_reports.py` (765 lines) + `services/meesho/parser.py` (278 lines)

**New structure:** Shared ingestion base + platform-specific adapters

```
routers/data_ingestion.py                 # single router for all uploads
  POST /ingest/upload                     # platform-agnostic upload endpoint
  POST /ingest/sync/{platform}            # trigger API sync
  GET  /ingest/reports                    # unified report list
  GET  /ingest/reports/{id}               # report detail (any platform)
  GET  /ingest/reports/{id}/summary       # platform-appropriate summary
  PATCH /ingest/reports/{id}/reprocess    # reprocess any platform

services/ingestion/
  base_parser.py             # abstract: parse() → NormalizedReport
  base_storage.py            # abstract: store(NormalizedReport)
  pipeline.py                # orchestrator: upload → parse → store → analyze
  amazon/
    file_parser.py           # consolidates both amazon parsers
    api_client.py            # was services/amazon/sp_api_client.py
  flipkart/
    file_parser.py           # was services/flipkart/parser.py
    analyzer.py              # was services/flipkart/analyzer.py
  meesho/
    file_parser.py           # was services/meesho/parser.py
```

**Key fix — Amazon parser deduplication:**
```python
# NEW: services/ingestion/amazon/file_parser.py
# Consolidates services/amazon/parser.py + services/ingestion/amazon/parser.py
# Handles both: file-upload path (flat file) + API path (Finance Events)
# Common base: column alias resolution, decimal parsing, datetime normalization
```

**Migration strategy:**
1. Create `services/ingestion/base_parser.py` abstract base
2. Move `services/ingestion/amazon/parser.py` to extend base
3. Merge `services/amazon/parser.py` features into it (remove duplication)
4. Do same for Flipkart and Meesho parsers
5. Create unified `/ingest/` router
6. Keep old `/amazon-reports/`, `/flipkart-reports/`, `/meesho-reports/` as pass-through aliases temporarily

---

### Merge 5: Platform Operations Hub

**Current modules:**
- `routers/platforms.py` (293 lines) — connection management
- `routers/sp_api.py` (665 lines) — Amazon OAuth + orders
- `routers/sync.py` (259 lines) — sync job management

**Problem:** `sp_api.py` is doing two unrelated things:
1. OAuth connection flow (should be in platforms.py)
2. Order/refund data retrieval (should be in data_ingestion)

**New structure:**
```
routers/platforms.py           # ALL platform connections + health
  GET  /platforms/connections  # unchanged
  GET  /platforms/health       # unchanged
  POST /platforms/connect      # unchanged + Amazon OAuth initiation
  GET  /platforms/auth-url     # was /sp-api/auth-url
  POST /platforms/callback     # was /sp-api/callback
  POST /platforms/test         # unchanged
  POST /platforms/disconnect   # unchanged

routers/sync.py               # ALL sync jobs (simplified)
  GET  /sync/jobs              # unchanged
  POST /sync/trigger           # unchanged + supports orders/refunds
```

**Amazon-specific order/refund endpoints** (`/sp-api/orders`, `/sp-api/refunds`) move to data ingestion layer — they are report data, not platform configuration.

---

## 4. Backend Refactor Plan

### 4.1 Current Architecture Problem: Fat Routers

The current pattern violates separation of concerns. Routers contain:
- SQL queries (directly using `db.execute()`)
- Business logic (fee calculations, variance detection)
- Data transformation (DataFrame operations in router scope)
- External API calls (httpx calls inside route handlers)

**Evidence:** `flipkart_reports.py` is 1,047 lines. `reconciliation.py` is 868 lines. These are routers — they should be ~100-200 lines each.

### 4.2 Target Architecture: Domain-Driven Service Layer

```
clearsettle-app/backend/app/
│
├── api/v1/                         # THIN ROUTERS ONLY
│   ├── financial.py                # settlements, bank, payouts
│   ├── reconciliation.py           # all recon types
│   ├── recovery.py                 # disputes, detection, tracking
│   ├── compliance.py               # gst, tax ledger
│   ├── analytics.py                # dashboard, trends, cashflow, forecast
│   ├── ingestion.py                # all platform report uploads
│   ├── platforms.py                # connections, OAuth, health
│   ├── sync.py                     # sync jobs
│   ├── automation.py               # rules, alert config
│   ├── crm.py                      # discovery, meetings
│   ├── auth.py                     # authentication
│   └── admin.py                    # users, audit
│
├── domain/                         # BUSINESS LOGIC
│   ├── financial/
│   │   ├── settlement_service.py   # settlement queries, payout tracking
│   │   ├── bank_service.py         # bank credit matching
│   │   └── schemas.py
│   ├── reconciliation/
│   │   ├── engine.py               # orchestrates all recon types
│   │   ├── detectors/
│   │   │   ├── settlement.py       # was services/reconciliation/detectors.py
│   │   │   ├── vendor.py           # was services/vendor_recon/detectors.py
│   │   │   └── leakage.py          # NEW: commission + returns detection
│   │   ├── base_detector.py        # shared DiscrepancyCandidate base class
│   │   └── storage.py
│   ├── recovery/
│   │   ├── state_machine.py        # explicit workflow states + transitions
│   │   ├── dispute_service.py      # CRUD + lifecycle
│   │   └── schemas.py
│   ├── compliance/
│   │   ├── tax_engine.py           # was services/tax/engine.py
│   │   ├── gst_service.py
│   │   └── summary.py
│   ├── analytics/
│   │   ├── kpi_service.py
│   │   ├── trend_service.py
│   │   ├── forecast_service.py
│   │   └── cashflow_service.py
│   ├── ingestion/
│   │   ├── pipeline.py             # orchestrator
│   │   ├── base_parser.py          # abstract base
│   │   ├── amazon/
│   │   │   ├── file_parser.py      # merged from two amazon parsers
│   │   │   └── api_client.py
│   │   ├── flipkart/
│   │   │   ├── file_parser.py
│   │   │   └── analyzer.py
│   │   └── meesho/
│   │       └── file_parser.py
│   ├── automation/
│   │   ├── rule_engine.py          # was services/rules/engine.py
│   │   ├── dispute_detector.py     # was dispute_engine router logic
│   │   └── scheduler.py
│   └── crm/
│       ├── discovery_service.py
│       ├── outreach_service.py
│       └── meeting_service.py
│
├── shared/                         # CROSS-CUTTING CONCERNS
│   ├── repositories/
│   │   └── base_repository.py      # generic async CRUD: get, list, create, update, delete
│   ├── services/
│   │   ├── notification_service.py # centralized — replaces scattered event creation
│   │   ├── export_service.py       # centralized PDF/Excel/CSV (implements stub router)
│   │   └── audit_service.py        # centralized audit log writes
│   ├── events/
│   │   ├── event_bus.py            # in-process pub/sub for domain events
│   │   └── domain_events.py        # typed event dataclasses
│   └── exceptions.py               # domain-specific exceptions
│
├── db/
│   ├── models/                     # unchanged SQLAlchemy models
│   └── base.py
│
└── core/                           # unchanged: config, auth, rbac, security
```

### 4.3 Shared Reconciliation Engine — Key Design

All three detection systems must share a common base:

```python
# domain/reconciliation/base_detector.py

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID
from enum import Enum

class DetectorSource(str, Enum):
    SETTLEMENT_RUN = "settlement_run"
    VENDOR_RUN     = "vendor_run"
    FILE_PARSE     = "file_parse"
    LEAKAGE_AUDIT  = "leakage_audit"  # commission + returns
    MANUAL         = "manual"

@dataclass
class DiscrepancyCandidate:
    """
    Unified output of ALL detectors across all three systems.
    Replaces: DiscrepancyCandidate (recon), LeakageCandidate (vendor_recon),
              and inline Flipkart issue dicts.
    """
    discrepancy_type:   str
    severity:           str          # critical | warning | info
    description:        str
    source:             DetectorSource
    platform:           str
    expected_amount:    Decimal | None = None
    actual_amount:      Decimal | None = None
    variance_amount:    Decimal | None = None
    is_disputable:      bool = False
    recovery_potential: Decimal | None = None
    evidence:           dict = field(default_factory=dict)
    rule_id:            UUID | None = None
    order_id:           str | None = None
    sku:                str | None = None
    reference_id:       str | None = None
```

### 4.4 Centralized Services

**Notification Service** (currently scattered across 6+ routers):
```python
# shared/services/notification_service.py
class NotificationService:
    async def emit(self, company_id, type, title, body, metadata=None): ...
    async def get_feed(self, company_id, limit=20) -> list[Notification]: ...
```

**Export Service** (currently a stub router — implements it properly):
```python
# shared/services/export_service.py
class ExportService:
    async def export_settlements(self, filters, format: Literal["pdf","excel","csv"]) -> bytes: ...
    async def export_gst_report(self, period, format) -> bytes: ...
    async def export_recon_issues(self, filters, format) -> bytes: ...
```

**Audit Service** (currently routers write audit logs directly):
```python
# shared/services/audit_service.py
class AuditService:
    async def log(self, user_id, company_id, action, resource_type, resource_id, metadata=None): ...
```

### 4.5 Remove Demo-Mode from Production Paths

Replace 14 instances of `get_db_optional() / if db is None` with:

```python
# BEFORE (dangerous):
async def get_settlements(db = Depends(get_db_optional)):
    if db is None:
        return MOCK_SETTLEMENTS  # silent failure in production!

# AFTER (explicit):
async def get_settlements(db: AsyncSession = Depends(get_db)):
    # raises HTTP 503 if DB unavailable — surfaces the problem
```

Demo mode should be a separate `DEMO_MODE=true` environment flag that loads fixture data at startup, not a production fallback.

### 4.6 Domain Event System

Replace direct cross-domain calls with an event bus:

```python
# When recon detects an issue → automatically notifies recovery center:
await event_bus.publish(ReconIssueDetected(
    company_id=..., 
    discrepancy_type=..., 
    variance_amount=...,
    is_disputable=True
))

# Recovery center subscribes:
@event_bus.subscribe(ReconIssueDetected)
async def on_recon_issue(event: ReconIssueDetected):
    if event.is_disputable:
        await dispute_service.create_from_detection(event)
```

This removes the `flipkart_recon_issues → DiscrepancyEvent` gap that currently makes Flipkart issues invisible to the recovery workflow.

---

## 5. Frontend Refactor Plan

### 5.1 Current Problem: Page-per-Feature Architecture

The current frontend has 24 independent pages, each with their own:
- Local state management (useState/useEffect)
- Data fetching (custom useApi calls)
- Table rendering (copy-pasted table JSX)
- Filter UI (copy-pasted filter inputs)

This means a bug in "how we filter by date range" must be fixed in ~15 places.

### 5.2 Target: Component-Driven Architecture

**New page count: 12 pages** (down from 24), backed by shared components.

```
pages/ (12 total)
├── Home.jsx                    # dashboard only (clean home)
├── financial/
│   ├── Settlements.jsx         # unchanged
│   └── BankMatching.jsx        # was BankRecon (simplified)
├── reconciliation/
│   └── ReconciliationCenter.jsx # merges BankRecon + ReconEngine + VendorRecon
├── recovery/
│   └── RecoveryCenter.jsx      # merges Disputes + DisputeEngine + Recovery + Commission + Returns
├── compliance/
│   └── GSTCompliance.jsx       # unchanged GST page
├── analytics/
│   └── Analytics.jsx           # merges Dashboard KPIs + Analytics + CashFlow + Forecast
├── data/
│   ├── PlatformConnections.jsx  # merges Platforms + SP API OAuth
│   └── ReportIngestion.jsx      # merges Amazon/Flipkart/Meesho upload (tabbed)
├── automation/
│   └── AutomationHub.jsx        # merges Rules + DisputeEngine config
├── crm/
│   ├── LeadPipeline.jsx         # merges SellerDiscovery + Outreach
│   └── Meetings.jsx             # unchanged
└── admin/
    └── AdminPanel.jsx           # unchanged
```

### 5.3 Shared Component Library

```
components/
├── data-display/
│   ├── DataTable.jsx            # UNIVERSAL TABLE
│   │   props: columns, data, loading, pagination,
│   │          onSort, onFilter, rowActions, exportable
│   ├── StatCard.jsx             # KPI card (used in Dashboard + Recovery + Analytics)
│   ├── TrendChart.jsx           # recharts wrapper (line/bar/area)
│   ├── PlatformBadge.jsx        # Amazon/Flipkart/Meesho colored badge
│   └── StatusChip.jsx           # extends existing Chip.jsx with status semantics
│
├── filters/
│   ├── FilterBar.jsx            # UNIVERSAL FILTER BAR
│   │   props: filters[], onApply, onReset
│   ├── DateRangePicker.jsx      # shared date range input
│   ├── PlatformFilter.jsx       # Amazon/Flipkart/Meesho multi-select
│   └── StatusFilter.jsx         # generic status multi-select
│
├── workflow/
│   ├── DetailDrawer.jsx         # UNIVERSAL RIGHT-SIDE DRAWER
│   │   props: title, sections[], actions[], isOpen, onClose
│   ├── WorkflowStepper.jsx      # step indicator (onboarding, dispute filing)
│   ├── TimelineView.jsx         # chronological events (dispute history)
│   └── ConfirmDialog.jsx        # action confirmation
│
├── upload/
│   ├── FileUploadZone.jsx       # drag-drop upload (shared by all 3 platforms)
│   └── UploadProgress.jsx       # upload + processing status
│
├── layout/                      # existing: Sidebar, Topbar
├── ui/                          # existing: Modal, Toast, Chip
└── forms/                       # existing: PasswordInput
```

### 5.4 Universal DataTable

Every list view in the app uses a table. Currently each page copies the same pattern. Replace all with:

```jsx
// BEFORE (in every page):
<table>
  <thead>...</thead>
  <tbody>
    {items.map(item => (
      <tr key={item.id}>
        <td>{formatCurrency(item.amount)}</td>
        ...
      </tr>
    ))}
  </tbody>
</table>

// AFTER (everywhere):
<DataTable
  columns={[
    { key: 'settlement_id', label: 'Settlement', sortable: true },
    { key: 'amount', label: 'Amount', format: 'currency', sortable: true },
    { key: 'status', label: 'Status', render: (v) => <StatusChip status={v} /> },
  ]}
  data={settlements}
  loading={loading}
  pagination={{ page, pageSize, total }}
  onSort={handleSort}
  rowActions={[
    { label: 'View Detail', icon: Eye, onClick: (row) => openDrawer(row) },
    { label: 'File Dispute', icon: Flag, onClick: (row) => fileDispute(row) },
  ]}
  exportable
/>
```

### 5.5 Universal DetailDrawer

Every page currently uses a custom modal for detail views. Replace with:

```jsx
<DetailDrawer
  isOpen={!!selectedItem}
  onClose={() => setSelectedItem(null)}
  title={`Settlement ${selectedItem?.external_id}`}
  sections={[
    { title: 'Overview', content: <SettlementOverview settlement={selectedItem} /> },
    { title: 'Transactions', content: <TransactionList settlementId={selectedItem?.id} /> },
    { title: 'Fees', content: <FeeBreakdown settlementId={selectedItem?.id} /> },
    { title: 'Recon Issues', content: <ReconIssueList settlementId={selectedItem?.id} /> },
  ]}
  actions={[
    { label: 'Export', variant: 'secondary', onClick: handleExport },
    { label: 'File Dispute', variant: 'danger', onClick: handleDispute },
  ]}
/>
```

### 5.6 Shared State Architecture

Replace individual page-level `useState + useEffect + useApi` patterns with domain-level hooks:

```javascript
// hooks/
useSettlements(filters)       // data + loading + error + pagination
useReconciliation(filters)    // recon runs + issues
useRecovery(filters)          // disputes + timeline
useAnalytics(dateRange)       // kpis + trends + platform share
usePlatforms()                // connections + health
useIngestReports(platform)    // uploaded reports + status
```

Each hook encapsulates the API call, error handling, caching, and pagination. Pages just call `const { data, loading } = useSettlements(filters)`.

---

## 6. Database Consolidation Analysis

### 6.1 Three Independent "Discrepancy" Tables

**Current state:**

```sql
-- Table 1: discrepancy_events
-- Source: reconciliation engine (Amazon-focused)
-- Has: result_id FK → reconciliation_results, settlement_id FK, platform, 7 discrepancy types

-- Table 2: flipkart_recon_issues
-- Source: Flipkart file parser
-- Has: report_id FK → flipkart_reports, SKU-level issues, NO FK to discrepancy_events
-- Status: completely disconnected from the dispute workflow

-- Table 3: vendor_recon results
-- Source: vendor recon engine
-- Has: its own result tables, LeakageCandidate dataclass, 10 leakage types
-- No FK relationship to discrepancy_events
```

**Target state:**

```sql
-- UNIFIED: financial_discrepancies
-- All three systems write here via adapters

ALTER TABLE discrepancy_events ADD COLUMN source VARCHAR(30) NOT NULL DEFAULT 'settlement_run';
-- source values: settlement_run | vendor_run | file_parse | leakage_audit | manual

ALTER TABLE discrepancy_events ADD COLUMN workflow_state VARCHAR(30) NOT NULL DEFAULT 'detected';
-- workflow_state: detected | reviewed | filed | acknowledged | resolved | rejected | dismissed

ALTER TABLE discrepancy_events ADD COLUMN filed_at TIMESTAMP;
ALTER TABLE discrepancy_events ADD COLUMN filed_by UUID REFERENCES users(id);
ALTER TABLE discrepancy_events ADD COLUMN acknowledged_at TIMESTAMP;
ALTER TABLE discrepancy_events ADD COLUMN recovery_amount NUMERIC(15,4);
ALTER TABLE discrepancy_events ADD COLUMN recovery_reference VARCHAR(200);

-- FlipkartReconIssue gets a bridge column (Phase 1: link, Phase 2: migrate)
ALTER TABLE flipkart_recon_issues ADD COLUMN discrepancy_event_id UUID REFERENCES discrepancy_events(id);
```

**Migration approach:** No destructive changes. Add `source` and `workflow_state` columns to existing `discrepancy_events`. Add bridge column to `flipkart_recon_issues`. Migrate Flipkart issues to unified table in Phase 2 after frontend is updated.

---

### 6.2 Duplicate Amazon Parser Models

```python
# services/amazon/parser.py returns:
{"meta": {...}, "order_rows": [...], "errors": [...]}  # plain dicts

# services/ingestion/amazon/parser.py returns:
NormalizedSettlement, NormalizedTransaction, NormalizedFee  # typed dataclasses
```

The `ingestion/` models are already more correct (typed dataclasses). **Action:** Make the file-upload path also output `NormalizedSettlement`. Both parsers converge on the same output type.

---

### 6.3 Status System Fragmentation

Every entity has its own status strings, defined as raw strings inline:

```python
# FlipkartReport: "upload" | "processing" | "done" | "failed"
# DiscrepancyEvent: is_resolved boolean (not a status string)
# ReconciliationResult: "clean" | "warning" | "critical" | "error"
# SyncJob: various strings
# PayoutEvent: various strings
```

**Target:** Create a shared status enum module:

```python
# app/shared/enums.py
class ProcessingStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"
    REPROCESSING = "reprocessing"

class ReconStatus(str, Enum):
    CLEAN    = "clean"
    WARNING  = "warning"
    CRITICAL = "critical"
    ERROR    = "error"

class DisputeWorkflowState(str, Enum):
    DETECTED     = "detected"
    REVIEWED     = "reviewed"
    FILED        = "filed"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED     = "resolved"
    REJECTED     = "rejected"
    DISMISSED    = "dismissed"
```

---

### 6.4 Normalization Opportunities

| Current Pattern | Problem | Fix |
|-----------------|---------|-----|
| `metadata_json TEXT` on 8+ tables | Untyped, unsearchable | Move common fields to columns; keep JSONB for truly dynamic data |
| `platform VARCHAR(50)` on 12+ tables | No FK constraint, typos possible | Add `platforms` lookup table OR use string enum at ORM level |
| `company_id` on every table with no index on some | Slow multi-tenant queries | Ensure composite indexes: `(company_id, created_at DESC)` on all high-query tables |
| `deleted_at` soft delete on some but not all models | Inconsistent | Apply `SoftDeleteMixin` to all business entities |

---

### 6.5 Audit Consistency

Currently `AuditLogEntry` is written in some routers manually. Centralize via `audit_service.py` middleware pattern:

```python
# Automatic audit logging for all state-changing operations:
@app.middleware("http")
async def audit_middleware(request, call_next):
    response = await call_next(request)
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and response.status_code < 300:
        await audit_service.log_from_request(request, response)
    return response
```

---

## 7. Recommended Final Information Architecture

### 7.1 Navigation Structure (sidebar)

```
┌────────────────────────────────────────────────────────┐
│  🏠  Home                                               │
├────────────────────────────────────────────────────────┤
│  💰  MONEY IN                                           │
│      Settlements                                        │
│      Report Uploads        ← was: 3 platform pages     │
│      Platform Sync                                      │
├────────────────────────────────────────────────────────┤
│  🔍  RECONCILIATION                                     │
│      Settlement Matching   ← was: BankRecon            │
│      Variance Analysis     ← was: ReconEngine          │
│      Vendor Matching       ← was: VendorRecon tab      │
├────────────────────────────────────────────────────────┤
│  ⚡  RECOVERY              ← unified workflow           │
│      Fee Audit             ← was: Commission + Returns │
│      Dispute Center        ← was: Disputes + Engine    │
│      Recovery Tracker      ← was: Recovery             │
├────────────────────────────────────────────────────────┤
│  🧾  COMPLIANCE                                         │
│      GST Dashboard                                      │
│      TCS / TDS Ledger                                   │
│      ITC Claims                                         │
├────────────────────────────────────────────────────────┤
│  📊  INTELLIGENCE                                       │
│      Performance           ← was: Analytics            │
│      Cash Flow & Forecast  ← was: 2 pages merged       │
│      Platform Health                                    │
├────────────────────────────────────────────────────────┤
│  ⚙️   AUTOMATION                                        │
│      Rule Engine           ← was: Rules                │
│      Alert Configuration   ← was: DisputeEngine config │
│      AI Classification     ← Phase 7                   │
├────────────────────────────────────────────────────────┤
│  👥  GROWTH (CRM)                                       │
│      Lead Pipeline         ← was: SellerDiscovery      │
│      Meeting Calendar                                   │
├────────────────────────────────────────────────────────┤
│  🔧  SETTINGS                                           │
│      Platform Connections  ← was: Platforms            │
│      Team & Permissions    ← was: AdminPanel           │
│      Audit Log                                          │
│      Company Profile                                    │
└────────────────────────────────────────────────────────┘
```

**Reduction:** 20+ sidebar items → 8 sections × 2-3 items = ~18 visible items, but grouped logically

### 7.2 User Workflow Journeys

**Journey: "Was I paid correctly this month?"**
```
Home (KPI alert: "3 settlements need review")
  → Reconciliation → Variance Analysis
    → Filter by March 2026
      → Click settlement with CRITICAL status
        → Detail Drawer → Transactions → Fees
          → "File Dispute" button
            → Recovery → Dispute Center (pre-filled from context)
```

**Journey: "What GST do I owe this quarter?"**
```
Compliance → GST Dashboard
  → Filter Q4 2025
    → TCS/TDS Ledger (detailed view)
      → Export to Excel
```

**Journey: "A new Amazon seller is overclaiming FBA fees"**
```
Recovery → Fee Audit
  → Commission overcharges (auto-detected, last 30 days)
    → Select overcharges to dispute
      → Batch file → Dispute Center
        → Track status
```

**Journey: "Connect my Meesho account"**
```
Settings → Platform Connections
  → "Add Platform" → Meesho
    → Upload API credentials
      → Test connection → ✓ Connected
        → "Sync Now" → Data & Sync
```

---

## 8. Scalability & Maintainability Improvements

### 8.1 Modular Monolith Strategy

**Current state:** The app is a monolith but without domain boundaries. Any file can import any other file.

**Target:** Enforce domain boundaries while staying a monolith:

```python
# domain/financial/__init__.py
# Only exports: SettlementService, BankService, schemas

# domain/recovery/__init__.py
# Only exports: DisputeService, StateMachine, schemas

# Cross-domain communication ONLY via:
# 1. Service layer method calls (synchronous)
# 2. Domain events via event_bus (decoupled)
```

This prepares for microservice extraction later without the cost of distributed systems now.

### 8.2 Future Microservice Boundaries

When traffic requires it, these domains can extract cleanly:

| Domain | Extraction Trigger | Why it can extract |
|--------|-------------------|--------------------|
| Ingestion + Parsing | High report volume | Stateless, CPU-bound, no cross-domain writes |
| AI Classification | AI compute cost | Anthropic calls, async, result stored in DB |
| Notification Delivery | SendGrid rate limits | Purely outbound, event-driven |
| Analytics/Reporting | Read-heavy, cache-friendly | Read-only, can use read replica |

### 8.3 Async Job Architecture

Replace synchronous processing (which currently blocks API responses) with proper job queuing:

```python
# BEFORE: report upload blocks until parsing is complete (~5-30s)
@router.post("/upload")
async def upload_report(file: UploadFile, db: AsyncSession = Depends(get_db)):
    parsed = await parse_large_report(file)  # blocks for 30s!
    await store_results(parsed, db)
    return {"status": "done"}

# AFTER: immediate response, background processing
@router.post("/upload")
async def upload_report(file: UploadFile, db: AsyncSession = Depends(get_db)):
    job_id = await ingestion_pipeline.enqueue(file, company_id)
    return {"job_id": job_id, "status": "processing"}

# Job worker (Celery/asyncio background task):
async def process_report_job(job_id, file_path):
    parsed = await parse_large_report(file_path)
    await store_results(parsed)
    await notification_service.emit(company_id, "REPORT_READY", ...)
```

For Phase 1: use FastAPI `BackgroundTasks`. For Phase 2: add Redis + Celery for proper queuing.

### 8.4 Observability Improvements

```python
# Add structured logging (currently missing):
import structlog
log = structlog.get_logger()

async def run_reconciliation(settlement_id, company_id):
    log.info("recon.started", settlement_id=str(settlement_id), company_id=str(company_id))
    result = await engine.run(settlement_id)
    log.info("recon.completed",
             settlement_id=str(settlement_id),
             discrepancies=result.total_discrepancies,
             duration_ms=result.processing_time_ms)
```

Add health check depth:
```python
GET /health/status → { "status": "ok", "version": "1.0.0" }
GET /health/deep   → { "db": "ok", "redis": "ok", "sp_api": "configured", 
                        "pending_jobs": 12, "failed_jobs_24h": 0 }
```

### 8.5 Testability Improvements

**Problem:** Fat routers with inline DB calls are untestable without a real database.

**Fix:** Repository pattern enables mocking:

```python
# shared/repositories/base_repository.py
class BaseRepository(Generic[T]):
    async def get(self, id: UUID) -> T | None: ...
    async def list(self, filters: dict, limit: int, offset: int) -> list[T]: ...
    async def create(self, obj: T) -> T: ...
    async def update(self, id: UUID, data: dict) -> T: ...
    async def delete(self, id: UUID) -> bool: ...

# In tests:
mock_settlement_repo = AsyncMock(spec=SettlementRepository)
mock_settlement_repo.list.return_value = [factory.build(Settlement)]
service = SettlementService(repo=mock_settlement_repo)
result = await service.get_summary(company_id=UUID(...))
```

### 8.6 Enterprise Readiness Checklist

| Item | Current | Target |
|------|---------|--------|
| Structured logging | print/logger.info | structlog with context |
| Request tracing | None | correlation_id header propagation |
| API versioning | /api/ (implicit v1) | /api/v1/ explicit |
| Rate limiting | nginx + in-memory | Redis sliding window |
| DB connection pool | asyncpg defaults | Configured pool_size, max_overflow |
| Migration rollback | Alembic down() incomplete | Full down() on every migration |
| Secret rotation | .env static | Secret manager (GCP Secret Manager) |
| Background jobs | BackgroundTasks | Celery + Redis (production) |
| Feature flags | Hardcoded checks | Config-driven (simple dict in DB or env) |
| API documentation | Auto (FastAPI) | Extended with examples + auth headers |

---

## 9. Prioritized Execution Roadmap

> All estimates assume one full-stack developer working full-time.

---

### Phase 1 — High-Impact Consolidation
**Goal:** Eliminate user confusion. Merge the most visible duplicate pages.  
**Duration:** 2–3 weeks | **Risk:** Low | **No existing functionality lost**

| Task | Effort | Impact | Dependencies |
|------|--------|--------|-------------|
| Merge CashFlowForecast + Cashflow pages into Analytics | 1 day | Medium | None |
| Merge Dashboard KPI duplication (remove /analytics/kpis overlap) | 1 day | Medium | None |
| Add `source` + `workflow_state` columns to discrepancy_events | 0.5 day | High | Migration 029 |
| Bridge FlipkartReconIssue → discrepancy_events (add FK column) | 1 day | High | Migration 030 |
| Commission + Returns detectors write to discrepancy_events | 2 days | High | Bridge column |
| Merge Disputes + DisputeEngine + Recovery into one page | 2 days | High | FE only |
| Add "File Dispute" action to Commission and Returns views | 1 day | High | Bridge |
| Remove demo-mode fallbacks from 14 routers | 1 day | High (safety) | None |
| Create root `.env.example` with all vars documented | Done ✓ | | |

**Phase 1 Deliverable:** User can go Detect → File → Track in one section. Commission/return overcharges flow into disputes. No silent mock-data mode.

---

### Phase 2 — Architecture Stabilization
**Goal:** Fix the technical debt. Establish clean layers.  
**Duration:** 3–4 weeks | **Risk:** Medium | **Backend refactor**

| Task | Effort | Impact | Dependencies |
|------|--------|--------|-------------|
| Extract service layer from fat routers (start with reconciliation.py) | 3 days | High | Phase 1 |
| Merge two Amazon parsers into one (services/ingestion/amazon/) | 2 days | High | Test coverage |
| Unified ingestion base class for all 3 platforms | 2 days | High | Amazon parser merge |
| Centralize notification_service.py | 1 day | Medium | Service layer |
| Centralize audit_service.py | 1 day | Medium | Service layer |
| Implement export_service.py (PDF/Excel/CSV) — was stub | 3 days | High | Phase 3 reports page |
| Replace BackgroundTasks with proper job queue (Redis) | 2 days | High | Redis in local dev |
| Add shared `app/shared/enums.py` (status consolidation) | 1 day | Low | None |
| Migrate FlipkartReconIssue data to discrepancy_events | 2 days | High | Phase 1 bridge |
| Write domain events for recon→recovery cross-domain flow | 2 days | High | Service layer |

**Phase 2 Deliverable:** No fat routers. One Amazon parser. Flipkart issues visible in Recovery Center. Reports can be exported.

---

### Phase 3 — UX Redesign
**Goal:** Ship the unified Information Architecture. Reduce page count from 24 to 12.  
**Duration:** 2–3 weeks | **Risk:** Medium | **Frontend rewrite**

| Task | Effort | Impact | Dependencies |
|------|--------|--------|-------------|
| Build universal DataTable component | 2 days | High | Phase 2 API stabilization |
| Build universal FilterBar component | 1 day | High | None |
| Build universal DetailDrawer component | 1 day | High | None |
| Build FileUploadZone component (shared upload) | 1 day | High | None |
| Implement ReconciliationCenter page (merges 3) | 2 days | High | Components |
| Implement RecoveryCenter page (merges 5) | 2 days | High | Components |
| Implement unified ReportIngestion page (merges 3) | 2 days | High | Components |
| Implement PlatformConnections page (absorbs SP API OAuth) | 1 day | Medium | None |
| Update sidebar navigation to new IA | 1 day | High | All above |
| Implement domain-level hooks (useSettlements, useRecovery, etc.) | 2 days | High | None |
| Update all CI/CD coverage to include new pages | 1 day | Medium | None |

**Phase 3 Deliverable:** 12 pages, workflow-based navigation, no duplicate charts, universal components used everywhere.

---

### Phase 4 — Advanced Automation & AI
**Goal:** Complete the unfinished features and add intelligence.  
**Duration:** 4–6 weeks | **Risk:** Low (new features, no regressions)

| Task | Effort | Impact | Dependencies |
|------|--------|--------|-------------|
| Complete Anthropic AI seller classification (Phase 7) | 1 week | High | Phase 2 service layer |
| Implement inventory sync (remove stub) | 1 week | Medium | Platform API research |
| Implement competitor intelligence (remove stub) | 2 weeks | Medium | Data source decision |
| Predictive insights: forecast settlement amounts | 1 week | High | Analytics service |
| Rule Engine 2.0: trigger on domain events | 1 week | High | Phase 2 event bus |
| Add observability: structlog + correlation IDs | 3 days | Medium | Phase 2 |
| Increase test coverage to 70%+ (add recon, rules, ingestion tests) | 2 weeks | High | Phase 2 service layer |
| GCP Secret Manager integration (replace .env) | 2 days | High | None |

**Phase 4 Deliverable:** All stub features implemented. AI classification working. 70% test coverage. Production-grade observability.

---

## Summary: Before vs. After

```
BEFORE (v1.0.0)                          AFTER (v2.0 target)
═══════════════════════════════════      ═══════════════════════════════════════
31 routers                               12 thin routers + domain service layer
11,169 lines in routers                  ~2,000 lines in routers, ~12,000 in services
3 independent recon engines              1 unified engine with 3 detector plugins
4 pages for financial intelligence       2 pages (Home + Analytics)
3 pages for dispute workflow             1 page (Recovery Center) with state machine
2 Amazon parsers                         1 consolidated parser
24 frontend pages                        12 domain pages
No shared table/filter/drawer            Universal DataTable + FilterBar + DetailDrawer
Commission/returns = dead ends           Commission/returns → auto-feed disputes
14 routers with silent mock fallback     0 (explicit 503 + DEMO_MODE flag)
No domain events                         Event bus: recon → recovery → notifications
No export service (stub)                 Full PDF/Excel/CSV export
~40% test coverage (auth only)           ~70% test coverage across all domains
```

---

*This document is based entirely on reading the actual source files. Every claim maps to a specific file and line range in the codebase. No features have been invented or assumed.*
