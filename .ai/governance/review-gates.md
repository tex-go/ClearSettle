# Review Gates
**Version:** 1.0 | **Owner:** `architect-agent`

Every feature must pass through the applicable review gates in sequence. A gate cannot be skipped. A gate can only be marked PASSED by the gate owner. `release-gatekeeper-agent` verifies all gates before any production deploy.

---

## Gate 1 — Architecture Review Gate

**When:** Before any implementation begins on a new feature or significant change.
**Owner:** `architect-agent`
**Trigger:** Any of the following: new service, new API endpoint, new database table, new integration, refactor affecting module boundaries.

### Checklist
- [ ] Feature aligns with ClearSettle domain model
- [ ] Service boundaries are not violated
- [ ] Data flow documented (who produces, who consumes)
- [ ] API contract defined (endpoints, request/response, auth requirements)
- [ ] Database schema change plan reviewed by `database-agent`
- [ ] No circular dependencies introduced
- [ ] File ownership declared in `folder-ownership.md`
- [ ] Estimated complexity/effort reviewed
- [ ] Non-functional requirements (performance, scale) addressed

**Output:** ADR entry + signed "Architecture Approved" in task description

---

## Gate 2 — Security Review Gate

**When:** Before merge of any code touching auth, permissions, file upload, external APIs, encryption, or user data.
**Owner:** `security-agent`
**Trigger:** Changes to auth.py, RBAC, file upload paths, new external API integration, encryption keys, session management.

### Checklist
- [ ] Authentication mechanism unchanged or reviewed
- [ ] Authorization (RBAC) enforced on all new endpoints
- [ ] Multi-tenant isolation (company_id) applied to all queries
- [ ] No SQL injection vectors (parameterized queries only)
- [ ] Input validation on all user inputs
- [ ] File uploads: size limit, type whitelist, sandboxed parsing
- [ ] No secrets hardcoded in any file
- [ ] Dependency security scan passes for new packages
- [ ] Rate limiting applied to new heavy endpoints
- [ ] Audit log entry created for all sensitive operations

**Output:** "Security Sign-Off: APPROVED" + any required remediations logged

---

## Gate 3 — Migration Review Gate

**When:** Before any Alembic migration is merged or deployed.
**Owner:** `database-agent`
**Trigger:** Any new file in `alembic/versions/`.

### Checklist
- [ ] Migration is idempotent where possible (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`)
- [ ] No column/table drops without deprecation period (minimum 1 release cycle)
- [ ] Column names match ORM model (no `full_name` when model uses `name`)
- [ ] Migration tested: `alembic upgrade head` succeeds on clean DB
- [ ] Migration tested: `alembic downgrade -1` succeeds (rollback works)
- [ ] Seed data uses correct column names
- [ ] Foreign key constraints do not violate existing data
- [ ] Index added for new FK columns and frequently queried columns
- [ ] Migration does not exceed 30-second execution time (else: batching required)
- [ ] `alembic current` correctly reflects state after upgrade

**Output:** "Migration Approved: [revision ID]" + test results logged

---

## Gate 4 — Quality Review Gate

**When:** Before any feature is marked complete.
**Owner:** `qa-manager-agent`
**Trigger:** Feature implementation complete, PR ready for merge.

### Checklist
- [ ] Test coverage meets threshold for feature's risk level (see `qa-manager-agent.md`)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] E2E tests pass for affected user flows
- [ ] Financial accuracy tests pass (if applicable)
- [ ] No skipped tests without documented justification
- [ ] Regression suite includes test for this feature
- [ ] Performance baseline not regressed

**Output:** "QA Sign-Off: APPROVED" + coverage metrics attached

---

## Gate 5 — Release Gate

**When:** Before any production deployment.
**Owner:** `release-gatekeeper-agent`
**Trigger:** Release branch merged to main, deployment initiated.

This is the comprehensive gate — all of the above plus:
- [ ] All sign-offs collected (Architecture, Security, Migration, QA, Design, Financial)
- [ ] Docker builds pass
- [ ] Health checks pass in staging
- [ ] Smoke tests pass in staging
- [ ] `release-manager-agent` has produced release plan and notes
- [ ] Rollback plan documented

**Output:** "Release Approved / Blocked" report (see `release-gatekeeper-agent.md` for format)

---

## Gate Flow Diagram

```
Feature Request
      │
      ▼
[Gate 1: Architecture] ← architect-agent
      │ PASS
      ▼
 Implementation
      │
      ▼
[Gate 2: Security] ← security-agent (if applicable)
[Gate 3: Migration] ← database-agent (if applicable)
      │ PASS
      ▼
[Gate 4: Quality] ← qa-manager-agent
      │ PASS
      ▼
  PR Merge
      │
      ▼
[Gate 5: Release] ← release-gatekeeper-agent
      │ PASS
      ▼
 Production Deploy
```

Any gate returning FAIL sends the work back to the implementing agent with a detailed failure report.
