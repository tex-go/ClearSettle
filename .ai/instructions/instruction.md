# ClearSettle AI Operating System
**Version:** 2.0 | **Effective:** 2026-06-01

---

## Project

ClearSettle is a production-grade eCommerce reconciliation SaaS for Indian marketplace sellers. It detects settlement discrepancies, automates disputes, recovers commission overcharges, and provides GST/TCS/TDS reconciliation.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.111+, Python 3.11, SQLAlchemy 2.x async, asyncpg, Alembic, Pydantic v2 |
| Frontend | React 18.3+, Vite 5+, Zustand 4+, React Router v6, Recharts 2+, Vitest |
| Mobile | Flutter 3.x, Riverpod 2.x, Hive, Dio, go_router |
| Database | PostgreSQL 15, Redis 7.2 |
| Infrastructure | Docker Compose, Nginx 1.27, GCP, Terraform, GitHub Actions |
| Auth | JWT HS256 (30min) + Refresh tokens (7 days), bcrypt rounds=12 |
| Encryption | Fernet AES-128 for marketplace credentials |

---

## Active Agents

| Agent | Role | Status |
|---|---|---|
| `ceo-agent` | Ultimate business authority | ACTIVE |
| `product-manager-agent` | Requirements, backlog, PRDs | ACTIVE |
| `orchestrator-agent` | Task coordination, delegation | ACTIVE |
| `architect-agent` | Technical authority, PR review | ACTIVE |
| `backend-agent` | FastAPI, services, tests | ACTIVE |
| `frontend-agent` | React, components, state | ACTIVE |
| `flutter-agent` | Flutter mobile app | ACTIVE |
| `database-agent` | Schema, migrations, queries | ACTIVE |
| `uiux-agent` | Design system, tokens, parity | ACTIVE |
| `qa-manager-agent` | Quality strategy, test governance | ACTIVE |
| `qa-agent` | Test execution, coverage | ACTIVE |
| `playwright-agent` | E2E tests, smoke tests | ACTIVE |
| `security-agent` | Security review, threat model | ACTIVE |
| `devops-agent` | Docker, CI/CD, infrastructure | ACTIVE |
| `git-agent` | Developer commit workflow | ACTIVE |
| `release-manager-agent` | Release planning, sign-offs | ACTIVE |
| `release-gatekeeper-agent` | Quality gate enforcement | ACTIVE |
| `data-quality-agent` | Financial accuracy, data integrity | ACTIVE |
| `documentation-agent` | API docs, changelogs, runbooks | ACTIVE |
| `parser-agent` | Marketplace report parsing | ACTIVE |
| `reconciliation-agent` | Discrepancy detection algorithms | ACTIVE |
| `ecommerce-agent` | Marketplace domain expertise | ACTIVE |
| `optimization-agent` | Performance profiling | ACTIVE |
| `bugfix-agent` | Bug investigation, regression | ACTIVE |
| `ai-agent` | Anomaly detection (Phase 7) | PLANNED |

---

## Orchestrator Startup Protocol

When starting any session, `orchestrator-agent` must:
1. Read `.ai/memory/current-progress.md`
2. Read `.ai/memory/decisions.md`
3. Read `.ai/context/architecture.md`
4. Load the relevant agent definitions for the task
5. Verify the task meets `Definition of Ready` criteria
6. Delegate to implementing agents with full context

---

## Core Invariants (Never Violate)

### Code Quality
- No business logic in route handlers — service layer required
- No blocking I/O in async paths
- No file exceeds 300 lines without ADR justification
- No duplicate code — extract shared utilities
- No `SELECT *` queries
- No string-formatted SQL — parameterized only

### Financial Integrity
- All monetary values use `Decimal`, never `float`
- All financial records are immutable once confirmed
- All financial operations produce an audit log entry
- Settlement discrepancy tolerance: ±₹0.01 only

### Security
- No hardcoded secrets — environment variables only
- No plaintext passwords anywhere in the system
- RBAC enforced on every protected endpoint
- Multi-tenant isolation: `company_id` filter on every query
- File uploads: size limit, type whitelist, sandboxed parsing

### Architecture
- Feature-based module structure
- Repository pattern for all DB access
- Dependency injection for sessions, config, current user
- All new modules declared in `folder-ownership.md`

### Mobile/Web Parity
- Mobile colors must match web palette exactly (see `design-tokens.md`)
- No hardcoded colors in mobile — use `AppColors` constants
- API tokens stored in `flutter_secure_storage` only

### Testing
- Backend minimum: 85% coverage (CRITICAL modules: 95%)
- Frontend minimum: 80% coverage
- Mobile minimum: 70% coverage
- Every migration tested in both directions

### Release Safety
- No code reaches production without passing `release-gatekeeper-agent`
- No release without `release-manager-agent` coordination
- No merge approval without `architect-agent` review
- Rollback plan documented before every production deploy

---

## Git Workflow

```
feature/your-feature → dev (PR + CI) → release/vX.Y.Z → main (tagged deploy)
```

Commit message format:
```
type(scope): description

feat(reconciliation): add commission overcharge detection for Meesho
fix(migration-033): correct users table column names
chore(ci): add migration validation to CI pipeline
docs(api): update settlement endpoint docs
```

---

## Forbidden Patterns

| Pattern | Why Forbidden |
|---|---|
| TailwindCSS | Not in approved stack — use CSS custom properties |
| External UI kits (MUI, Ant Design) | Brand consistency requires custom components |
| Nested template literals | Readability — use explicit string construction |
| `float` for money | Precision loss — use `Decimal` |
| Hardcoded colors in mobile | Design system violation |
| Demo-mode in production paths | Silent failures in production |
| Architecture rewrites without ADR | Breaks ownership model |
| `git push --force` to `main` or `dev` | Data loss risk |
| Skipping `release-gatekeeper-agent` | Non-negotiable quality gate |

---

## Review Gate Sequence

Every feature must pass (in order):
1. **Definition of Ready** → `architect-agent` validates before implementation
2. **Architecture Review Gate** → `architect-agent` approves design
3. **Security Review Gate** → `security-agent` approves auth/security changes
4. **Migration Review Gate** → `database-agent` approves schema changes
5. **Quality Review Gate** → `qa-manager-agent` confirms coverage and testing
6. **Release Gate** → `release-gatekeeper-agent` validates all signs-off before deploy

---

## Escalation Path

Agent blocker → Peer agent → `architect-agent` → `product-manager-agent` → `ceo-agent`

Security blocker → `security-agent` (immediate)
Financial blocker → `data-quality-agent` + `ceo-agent` (immediate)
Production incident → `devops-agent` → `release-manager-agent` → `ceo-agent`
