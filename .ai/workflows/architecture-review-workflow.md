# Architecture Review Workflow

Purpose: Ensure major changes preserve system integrity, scalability and adherence to standards.

Steps
1. `product-manager-agent` submits feature requiring architecture review.
2. `architect-agent` drafts ADR and tradeoffs.
3. `database-agent` and `fastapi-agent` provide compatibility notes and migration plan.
4. `security-agent` completes threat model.
5. Review board (automated: `architect-agent`, `security-agent`, `devops-agent`) approves or requests changes.

Outcome
- Approved ADR with measurable non-functional requirements or a blocked state with required changes.
