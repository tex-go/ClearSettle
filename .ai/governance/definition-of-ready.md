# Definition of Ready
**Version:** 1.0 | **Owner:** `architect-agent` + `product-manager-agent`

A feature, bug fix, or task is **Ready** to enter implementation only when ALL of the following criteria are met. Orchestrator-agent must verify this checklist before delegating any implementation task.

---

## Checklist

### Business Requirements
- [ ] User story written: "As a [role], I want [action] so that [outcome]"
- [ ] Acceptance criteria defined — measurable, testable, unambiguous
- [ ] Business priority confirmed by `product-manager-agent`
- [ ] Scope is bounded — no open-ended "improve" or "refactor" without specific target
- [ ] Dependencies on other features identified and resolved (or explicitly deferred)

### Technical Requirements
- [ ] Architecture review complete (`architect-agent` has approved design)
- [ ] API contract defined — request/response shapes documented
- [ ] Database schema changes identified — migration plan produced by `database-agent`
- [ ] File ownership assigned — implementing agent declared in `folder-ownership.md`
- [ ] No unresolved technical questions remain

### Design Requirements (if UI changes)
- [ ] `uiux-agent` has reviewed and approved visual design
- [ ] Design tokens confirmed — no new hardcoded values
- [ ] Mobile/web consistency assessed
- [ ] Accessibility requirements documented

### Security Requirements
- [ ] Security implications assessed
- [ ] If auth/permissions change: `security-agent` pre-approval obtained
- [ ] If file upload changes: `security-agent` pre-approval obtained
- [ ] Data sensitivity classified

### Quality Requirements
- [ ] Test plan produced by `qa-manager-agent`
- [ ] Minimum coverage threshold confirmed for this feature's risk level
- [ ] Test types required listed (unit/integration/E2E/financial)
- [ ] `data-quality-agent` engaged if financial calculations are involved

### Definition of Done (Pre-Awareness)
- [ ] Implementing agent has read and confirmed understanding of `definition-of-done.md`

---

## NOT Ready If

- Acceptance criteria are vague or missing
- Architecture not approved
- API contract not defined
- Security review skipped for auth-touching code
- No test plan for CRITICAL/HIGH risk changes
- Scope is larger than can be completed in one session

---

## Enforcement

`orchestrator-agent` must refuse to delegate implementation tasks until DoR is complete.
`architect-agent` is the final arbiter of technical readiness.
