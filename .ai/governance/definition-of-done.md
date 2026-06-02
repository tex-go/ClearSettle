# Definition of Done
**Version:** 1.0 | **Owner:** `qa-manager-agent` + `architect-agent`

Work is **Done** only when ALL of the following criteria are met. No exceptions. The `release-gatekeeper-agent` enforces this at deploy time.

---

## Checklist

### Code Completeness
- [ ] Feature is fully implemented per acceptance criteria
- [ ] No TODO/FIXME/placeholder code in production paths
- [ ] No demo-mode or mock data in production code paths
- [ ] All edge cases from acceptance criteria handled
- [ ] Error states handled (network, validation, server error, empty state)
- [ ] Loading states implemented for all async operations

### Code Quality
- [ ] File size ≤ 300 lines (exceptions require ADR justification)
- [ ] Linting passes with zero errors
- [ ] No new linting warnings without documented justification
- [ ] Code reviewed by at least one other agent (architecture changes: `architect-agent`)
- [ ] No duplicate code — shared utilities extracted
- [ ] Naming is clear and self-documenting

### Testing
- [ ] Unit tests written for all new functions/methods/components
- [ ] Integration tests written for all new API endpoints
- [ ] Coverage meets threshold for this feature's risk level (see `qa-manager-agent.md`)
- [ ] All tests pass locally and in CI
- [ ] No skipped tests without documented justification
- [ ] Regression test added for any bug fix

### Database (if applicable)
- [ ] Alembic migration created and tested (`upgrade head` + `downgrade -1`)
- [ ] Migration reviewed by `database-agent`
- [ ] No data-destructive operations without rollback plan
- [ ] Indexes added for any new foreign keys or query patterns
- [ ] `database-agent` sign-off obtained

### Security (if applicable)
- [ ] No hardcoded secrets, tokens, or credentials
- [ ] RBAC enforced on all new endpoints
- [ ] `security-agent` sign-off for auth/permission/upload changes
- [ ] Input validation on all user-facing inputs
- [ ] Parameterized queries (no string-formatted SQL)

### Design (if UI changes)
- [ ] `uiux-agent` sign-off obtained
- [ ] Design tokens used — no hardcoded colors or spacing
- [ ] Responsive design verified
- [ ] Accessibility requirements met (contrast, touch targets, labels)
- [ ] Loading, error, and empty states implemented
- [ ] Mobile/web visual parity verified

### Financial Accuracy (if financial logic)
- [ ] `data-quality-agent` validation complete
- [ ] Calculation unit tests cover all known edge cases
- [ ] Financial fixture test suite passes without regression
- [ ] Audit trail implemented (every state change logged)

### Documentation
- [ ] API documentation updated (if endpoint changed)
- [ ] `documentation-agent` has updated relevant docs
- [ ] Changelog entry added
- [ ] `folder-ownership.md` updated if new files created

### Deployment Readiness
- [ ] Docker build succeeds
- [ ] Environment variables documented in `.env.prod.example`
- [ ] `devops-agent` notified of any infrastructure changes
- [ ] Health check still passes with this change

---

## NOT Done If

- Tests are commented out
- Linting errors present
- Coverage below threshold
- Any sign-off missing
- Documentation not updated
- Demo/mock code remains in production paths
- Financial calculations not validated by `data-quality-agent`

---

## Enforcement

Implementing agents self-certify against this checklist before requesting merge.
`architect-agent` validates during PR review.
`release-gatekeeper-agent` enforces at deploy time — any DoD failure blocks release.
