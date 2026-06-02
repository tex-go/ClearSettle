# Bug Fix Workflow

Flow: QA → Root Cause Analysis → Architect → Responsible Agent → Security → QA Retest → Docs Update

Steps
1. `qa-agent` files bug with logs, failing tests and reproducible repro steps.
2. Root-cause analysis assigned to `architect-agent` (if cross-cutting) or to relevant agent (e.g., `fastapi-agent`).
3. Responsible agent implements fix with tests and migration plan if needed.
4. `security-agent` reviews fix for regressions.
5. `qa-agent` retests and updates regression suite.
6. `documentation-agent` updates release notes and postmortem if critical.

Rules
- Critical P0 requires immediate hotfix branch and `devops-agent` involvement for emergency deploys.
