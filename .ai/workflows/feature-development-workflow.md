# Feature Development Workflow

Flow: Product Manager → Architect → Database → FastAPI → React/Flutter → Security → QA → Documentation → Approval

Steps
1. `product-manager-agent` writes feature PRD and success metrics.
2. `architect-agent` produces technical design and approves or suggests changes.
3. `database-agent` designs schema, migration plan and test fixtures.
4. `fastapi-agent` implements API, service & repository layers and tests.
5. `react-agent` (or `flutter-agent`) implements UI with mocks and integration tests.
6. `security-agent` performs threat model and code review for sensitive paths.
7. `qa-agent` runs full test suite and verifies coverage thresholds.
8. `documentation-agent` creates feature docs, API reference and rollout notes.
9. `ceo-agent` / `product-manager-agent` approve for release.

Automations
- PR template enforces required signoffs from `architect-agent`, `security-agent`, and `qa-agent` before merge.
