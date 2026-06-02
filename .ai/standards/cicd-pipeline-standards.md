# CI/CD Pipeline Standards
**Version:** 1.0 | **Owner:** `devops-agent`

The CI/CD pipeline is the automated enforcement of quality standards. Every push to `dev` and `main` must pass all pipeline stages. Pipeline failures block merges — they are not warnings.

---

## Pipeline Stages (Ordered — each must pass before next runs)

### Stage 1 — Code Quality

```yaml
backend-lint:
  run: ruff check . --select E,W,F,C90 --output-format=github
  fail-on: any error
  
backend-typecheck:
  run: python -m mypy app/ --ignore-missing-imports
  fail-on: any error on critical modules (auth, reconciliation, settlements)

frontend-lint:
  run: npm run lint (eslint src/)
  fail-on: any error

frontend-typecheck:
  run: npm run type-check (if TypeScript added)
  fail-on: any error

secret-scan:
  run: trufflehog filesystem . --only-verified
  fail-on: any verified secret found
```

### Stage 2 — Unit Tests

```yaml
backend-unit-tests:
  run: pytest tests/unit/ -v --tb=short
  fail-on: any test failure

frontend-unit-tests:
  run: npm run test (vitest --run)
  fail-on: any test failure

mobile-unit-tests:
  run: flutter test test/unit/
  fail-on: any test failure
```

### Stage 3 — Coverage Enforcement

```yaml
backend-coverage:
  run: pytest --cov=app --cov-report=xml --cov-fail-under=85
  fail-on: coverage below 85% global, below 95% for auth/reconciliation/settlements

frontend-coverage:
  run: vitest --run --coverage --coverage.thresholds.lines=80
  fail-on: coverage below 80%

coverage-report:
  action: upload coverage reports to artifact storage
  always-runs: true
```

### Stage 4 — Integration Tests

```yaml
backend-integration-tests:
  requires: test-postgres-db (started as service container)
  run: pytest tests/integration/ -v --tb=short
  fail-on: any test failure

migration-validation:
  requires: test-postgres-db (clean database)
  run: |
    alembic upgrade head
    alembic downgrade -1
    alembic upgrade head
  fail-on: any migration error in any direction
```

### Stage 5 — Security Scanning

```yaml
dependency-audit-backend:
  run: pip-audit --requirement requirements.txt --severity high
  fail-on: HIGH or CRITICAL vulnerabilities

dependency-audit-frontend:
  run: npm audit --audit-level=high
  fail-on: HIGH or CRITICAL vulnerabilities

sast-scan:
  run: bandit -r app/ -ll (or semgrep with python ruleset)
  fail-on: HIGH severity findings

container-scan:
  run: trivy image clearsettle-backend:$TAG --severity HIGH,CRITICAL
  fail-on: CRITICAL vulnerabilities
```

### Stage 6 — Docker Build Verification

```yaml
build-backend:
  run: docker build ./backend --tag clearsettle-backend:$SHA
  fail-on: any build error

build-frontend:
  run: docker build ./frontend --tag clearsettle-frontend:$SHA
  fail-on: any build error

build-verify:
  run: |
    docker run --rm clearsettle-backend:$SHA python -c "from app.main import app; print('OK')"
  fail-on: import errors
```

### Stage 7 — E2E Tests (staging only — on push to `dev` and `main`)

```yaml
e2e-tests:
  requires: full docker-compose stack running
  run: npx playwright test --reporter=html
  fail-on: any test failure
  artifacts: playwright-report/
```

### Stage 8 — Mobile Build Verification (on mobile changes)

```yaml
flutter-build:
  condition: files-changed in mobile/
  run: |
    flutter pub get
    flutter analyze
    flutter build apk --dart-define=API_BASE_URL=https://api.clearsettle.in
  fail-on: analyze errors, build failure
```

---

## Branch Policies

| Branch | Required Checks | Protection |
|---|---|---|
| `main` | ALL stages pass | Protected — no direct push. PR + all checks + reviewer approval |
| `dev` | Stages 1-6 pass | Protected — no direct push. PR + all checks |
| `release/*` | ALL stages pass | Created by `release-manager-agent` only |
| `feature/*` | Stages 1-3 pass | No protection — developer branch |
| `hotfix/*` | Stages 1-6 minimum | Created by `devops-agent` + `release-manager-agent` |

---

## Environment Variables in CI

Required secrets (set in GitHub Secrets or equivalent):
```
POSTGRES_PASSWORD     — test database password
SECRET_KEY            — test JWT secret
ENCRYPTION_KEY        — test Fernet key
SUPER_ADMIN_EMAIL     — seed admin email
SUPER_ADMIN_PASSWORD  — seed admin password
```

Never:
- Pass production secrets to CI
- Log secret values in CI output
- Store secrets in `.env` files committed to repo

---

## Artifacts

Every pipeline run produces:
- Coverage reports (XML + HTML)
- Test results (JUnit XML)
- Playwright report (HTML)
- Security scan results
- Docker image digest (for traceability)

Retain artifacts for 90 days minimum.

---

## Failure Notification

When any stage fails:
- Implementing agent is notified with: stage name, error summary, log link
- `qa-manager-agent` is notified if coverage drops
- `security-agent` is notified if security scan finds issues
- `devops-agent` is notified if Docker build fails

---

## Pipeline Performance Targets

| Stage | Target Duration |
|---|---|
| Stage 1 (lint) | < 2 minutes |
| Stage 2 (unit tests) | < 5 minutes |
| Stage 3 (coverage) | < 3 minutes |
| Stage 4 (integration) | < 10 minutes |
| Stage 5 (security) | < 5 minutes |
| Stage 6 (build) | < 10 minutes |
| Stage 7 (E2E) | < 15 minutes |
| **Total** | **< 50 minutes** |

If pipeline exceeds 60 minutes, `devops-agent` must optimize.
