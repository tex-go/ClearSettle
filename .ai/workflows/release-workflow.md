# Release Workflow
**Version:** 2.0 | **Owner:** `release-manager-agent`

This is the mandatory release workflow for every ClearSettle production deployment. No deployment occurs outside this workflow.

---

## Stage 1 — Feature Complete (T-5 days)

```
release-manager-agent:
  1. Create release branch: git checkout -b release/vX.Y.Z from dev
  2. Announce to all agents: release scope and timeline
  3. Freeze feature scope with product-manager-agent
  4. Identify high-risk changes (migrations, auth, new integrations)

architect-agent:
  5. Final architecture review of all changes in scope
  6. Sign: "No unresolved architectural issues"

security-agent:
  7. Begin security review + dependency vulnerability scan
```

## Stage 2 — Validation (T-2 days)

```
database-agent:      Validate all migrations (upgrade + downgrade)
qa-manager-agent:    Run full test suite, verify coverage thresholds
playwright-agent:    Run E2E suite on staging
data-quality-agent:  Run financial fixture validation (if financial logic changed)
uiux-agent:          Cross-platform parity check (if visual changes)
devops-agent:        Deploy to staging, document rollback plan
documentation-agent: Update API docs, changelog, VERSION file
```

## Stage 3 — Sign-Off Collection (T-1 day)

```
release-manager-agent collects explicit sign-offs from:
  ✅/❌ architect-agent
  ✅/❌ security-agent
  ✅/❌ qa-manager-agent
  ✅/❌ database-agent
  ✅/❌ devops-agent (staging healthy + rollback documented)
  ✅/❌ documentation-agent
  ✅/❌ uiux-agent (if visual changes)
  ✅/❌ data-quality-agent (if financial changes)

Any ❌ → return to responsible agent. No deployment until all ✅.
```

## Stage 4 — Release Gate (T-0)

```
release-manager-agent submits all sign-offs to release-gatekeeper-agent.

release-gatekeeper-agent runs full 10-gate checklist:
  IF ALL PASS → "RELEASE APPROVED — vX.Y.Z" → proceed to Stage 5
  IF ANY FAIL → "RELEASE BLOCKED — vX.Y.Z" → return with failure details
```

## Stage 5 — Production Deployment

```
devops-agent (on release-manager-agent instruction):
  1. Merge release branch to main (--no-ff)
  2. Tag: git tag vX.Y.Z && git push origin main --tags
  3. Run deploy.sh (see deployment-standards.md)
  4. Monitor 30 minutes: error rate, health checks, smoke tests

IF DEPLOYMENT FAILS: immediate rollback → release-manager-agent → ceo-agent
```

## Stage 6 — Post-Release

```
release-manager-agent: close branch, post release notes, update memory
devops-agent: confirm 24-hour metrics within baseline
architect-agent: review post-deploy issues → tech debt backlog
```

---

## Hotfix Protocol (P0 — Production Down)

```
T+0:00  devops-agent detects → alerts release-manager-agent
T+0:10  release-manager-agent: rollback vs hotfix decision
T+0:15  ceo-agent alerted

IF ROLLBACK: devops-agent executes immediately (no gates required)

IF HOTFIX: create hotfix/vX.Y.Z+1 branch
  Minimum gates: Security (if applicable), Migration (if applicable),
                 Health checks, Smoke tests
  Skipped: Linting, Coverage, Design, full Docs
  Coverage/docs debt logged for next regular release
  ceo-agent documents override + risk acknowledgment
```

---

## Anti-Patterns (Forbidden)

- Deploying directly from `dev` branch to production
- Skipping `release-gatekeeper-agent` gate without `ceo-agent` written override
- Marking sign-offs without running the actual validation
- Deploying during night hours without on-call coverage
- Not documenting rollback plan before deploying
