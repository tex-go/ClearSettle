# Escalation Matrix
**Version:** 1.0 | **Owner:** `architect-agent`

When an agent cannot resolve a conflict, decision, or blocker independently, it escalates using this matrix. Escalation is not failure — it is the correct response to ambiguity or authority gaps.

---

## Escalation Levels

| Level | Scope | Response Time | Authority |
|---|---|---|---|
| L1 — Self-resolve | Within agent mandate | Immediate | Implementing agent |
| L2 — Peer consult | Cross-agent clarification | Same session | Peer agent |
| L3 — Architecture | Architectural decision needed | Next session | `architect-agent` |
| L4 — Product | Priority or scope question | Same day | `product-manager-agent` |
| L5 — Security | Security risk identified | Immediate | `security-agent` |
| L6 — Executive | Business or legal risk | Immediate | `ceo-agent` |

---

## Escalation Table

| Situation | From | To | Level | Action |
|---|---|---|---|---|
| API contract ambiguous | `backend-agent` | `architect-agent` | L3 | Request contract clarification before coding |
| Feature scope unclear | Any agent | `product-manager-agent` | L4 | Request PRD clarification before starting |
| Two valid technical approaches | `backend-agent` / `frontend-agent` | `architect-agent` | L3 | Request ADR decision |
| Migration risk (data loss possible) | `database-agent` | `architect-agent` + `ceo-agent` | L3+L6 | Halt migration, document risk |
| Security vulnerability discovered | Any agent | `security-agent` | L5 | Immediate report, halt related code |
| Production incident | `devops-agent` | `release-manager-agent` | L4 | Activate incident protocol |
| Production incident (critical) | `devops-agent` + `release-manager-agent` | `ceo-agent` | L6 | CEO alert within 15 min |
| Financial calculation error in prod | `data-quality-agent` | `ceo-agent` | L6 | Immediate halt + incident |
| Release blocked by gatekeeper | `release-gatekeeper-agent` | `release-manager-agent` | L4 | Fix identified issues |
| Release override requested | Any agent | `ceo-agent` | L6 | CEO must document override with risk |
| Design conflict (mobile vs web) | `flutter-agent` / `frontend-agent` | `uiux-agent` | L3 | Design authority decides |
| Design override requested | `uiux-agent` | `architect-agent` | L3 | Architect may approve with documented rationale |
| Coverage threshold waiver | `qa-agent` | `qa-manager-agent` | L3 | Manager may approve for non-CRITICAL modules only |
| Dependency with security risk | Any agent | `security-agent` | L5 | Immediate review before use |
| Tech debt blocks feature | Any agent | `architect-agent` | L3 | Architect prioritizes in backlog |
| Cross-marketplace rule conflict | `ecommerce-agent` | `product-manager-agent` | L4 | PM decides rule precedence |

---

## Emergency Protocol (P0 — Production Down)

```
T+0:00  devops-agent detects outage
T+0:05  devops-agent notifies release-manager-agent
T+0:10  release-manager-agent activates rollback if deploy-related
T+0:15  ceo-agent alerted
T+0:20  security-agent engaged if breach suspected
T+0:30  All agents on standby pending root cause
T+1:00  Root cause preliminary report
T+4:00  Full incident report + remediation plan
T+24:00 Post-mortem in .ai/memory/decisions.md
```

---

## Escalation Is Blocked If

- Escalating agent has not tried to resolve within their own mandate first (L1)
- The issue is clearly documented in existing standards — RTFM before escalating
- The escalation is being used to avoid making a decision within existing authority

---

## Anti-Pattern: Do Not Escalate For

- Routine technical choices within your mandate
- Questions answered in the standards files
- Personal preference (prefer → document preference, implement what's specified)
