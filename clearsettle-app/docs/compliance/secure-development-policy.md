# Secure Development Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-SDEV-POL-012 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Engineering Lead / CTO |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Secure Development Policy establishes the security standards, practices, and controls that all ClearSettle engineers must follow throughout the software development lifecycle (SDLC). It ensures that security is integrated into development from design through deployment rather than added as an afterthought.

This policy applies to all ClearSettle engineers, contractors, and third-party developers contributing code to ClearSettle repositories.

---

## 2. Secure Development Lifecycle (SDL)

### 2.1 Design Phase

**Threat Modeling:**
- All new features that handle financial data, authentication, or marketplace credentials require a threat model before implementation begins
- Threat models use the STRIDE methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
- Threat model outcomes are documented as a comment in the GitHub issue or PR description

**Security Requirements:**
- Every feature specification must include explicit security requirements
- New API endpoints must specify: authentication requirements, authorization scope, input validation rules, and rate limiting requirements
- Third-party integrations require a vendor security assessment before implementation (see CLS-VSEC-POL-005)

### 2.2 Development Phase

**Coding Standards:**

All ClearSettle production code must adhere to the following:

**Python / FastAPI backend:**
- Use Pydantic v2 models for all input validation; never trust unvalidated input
- Use SQLAlchemy ORM for all database queries; raw SQL is prohibited
- Use `httpx.AsyncClient` with explicit timeout for all external HTTP calls (30-second maximum)
- Never log sensitive data: no passwords, tokens, Fernet keys, or PII in log statements
- Use `secrets.token_urlsafe()` or `uuid4()` for all random token/ID generation
- Async functions must not block the event loop; use `asyncio.to_thread()` for blocking I/O

**Flutter / Dart mobile:**
- Use `flutter_secure_storage` for all on-device credential storage; never SharedPreferences for secrets
- Certificate pinning must be implemented for all production API connections
- All network calls must go through the repository layer; no direct HTTP in UI code
- Biometric authentication must be offered for sensitive operations (export, account management)

**React / JavaScript frontend:**
- JSX templating is used exclusively; `dangerouslySetInnerHTML` is prohibited
- All API calls use the centralized `apiClient` service; no direct `fetch()` in components
- No secrets or API keys in frontend code; environment variables are for build-time configuration only
- Content Security Policy (CSP) headers are enforced at the Nginx layer

### 2.3 Code Review Phase

**Mandatory Code Review:**
- All code changes require at least one peer review before merging to `main` or `dev`
- Security-sensitive changes (authentication, authorization, marketplace credentials, encryption) require review by the Engineering Lead or Security Lead
- Reviewers must check the security review checklist before approving

**Security Review Checklist for PRs:**

- [ ] No secrets, credentials, or API keys committed in code or configuration
- [ ] Input validation present for all new API endpoints
- [ ] Authorization check (`require_permission` or equivalent) applied to all new endpoints
- [ ] No new raw SQL queries introduced
- [ ] No new `dangerouslySetInnerHTML` or equivalent unsafe patterns
- [ ] Sensitive data is not logged
- [ ] External HTTP calls have explicit timeouts
- [ ] New dependencies have been security-reviewed and approved

### 2.4 Testing Phase

**Security Testing Requirements:**

| Test Type | Requirement | Tooling |
|---|---|---|
| Unit tests | All security-critical functions (auth, encryption, validation) | pytest |
| Integration tests | All API endpoints including error/edge cases | pytest + httpx |
| Authentication tests | Unauthenticated access returns 401; unauthorized access returns 403 | pytest |
| Input validation tests | Boundary values, injection strings, oversized payloads | pytest |
| Dependency vulnerability scan | Before every release | pip-audit / Dependabot |
| Static analysis | Before every release | bandit (Python), eslint security plugin (JS) |

**Prohibited Test Shortcuts:**
- Production credentials must not be used in test environments
- Test databases must not contain real seller financial data
- Mocking of authentication/authorization in integration tests is prohibited; tests must use real JWT flows

### 2.5 Deployment Phase

**Pre-Deployment Checklist:**

- [ ] All tests pass in CI
- [ ] Dependency vulnerability scan passed with no Critical or High findings
- [ ] Static analysis (bandit/eslint) passed with no new High findings
- [ ] Alembic migration reviewed and tested on staging database
- [ ] Manual backup of production database taken (for migrations)
- [ ] Secrets are in GCP Secret Manager; no new secrets added to codebase
- [ ] Feature reviewed on staging environment by at least one engineer other than the implementer
- [ ] Rollback plan documented if migration is irreversible

**Deployment Procedure:**
1. Merge to `main` branch via PR (no direct pushes to main)
2. CI pipeline runs tests and scans automatically
3. Deploy to staging: `docker compose pull && docker compose up -d` on staging server
4. Run smoke tests on staging
5. Deploy to production during business hours only (not on Fridays or day before Indian public holidays)
6. Monitor production error rates and latency for 30 minutes post-deployment

---

## 3. Secrets Management in Development

### 3.1 Local Development

- Local development uses `.env` files (gitignored) with non-production credentials
- `.env.example` with placeholder values is maintained in the repository for onboarding
- Production secrets are never used in local development environments
- Development database uses a separate PostgreSQL instance with synthetic or anonymized data

### 3.2 Pre-commit Hooks

All engineers must install the pre-commit hooks defined in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    hooks:
      - id: detect-secrets
  - repo: https://github.com/PyCQA/bandit
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
```

Bypassing pre-commit hooks (`git commit --no-verify`) is prohibited without Security Lead approval.

### 3.3 CI/CD Pipeline Security

- GitHub Actions workflows run in isolated environments
- Production deployment secrets are stored in GitHub Secrets (linked to GCP Secret Manager)
- No CI workflow may expose secrets in logs (`::add-mask::` applied to all secret values)
- Branch protection rules require PR reviews and CI passage before merge to `main` or `dev`

---

## 4. Third-Party Dependencies

### 4.1 Approval Process

Before adding any new dependency to production code:

1. Check for known CVEs: `pip-audit` (Python) or `npm audit` (Node)
2. Review the dependency's maintenance status: last release within 12 months, active issue tracker
3. Review the dependency's license: GPL dependencies require Legal approval
4. Obtain Engineering Lead approval for new production dependencies

### 4.2 Pinning Policy

- All Python dependencies in `requirements.txt` must be pinned to exact versions (`package==1.2.3`)
- All Flutter dependencies in `pubspec.yaml` must specify version ranges compatible with security updates (`^1.2.3`)
- Dependabot or equivalent is enabled for automated security update PRs

### 4.3 Vulnerability Response

| Severity | Action | Timeline |
|---|---|---|
| Critical | Emergency patch or remove dependency | 24 hours |
| High | Patch in next deployment | 7 days |
| Medium | Patch in next planned release | 30 days |
| Low | Track; patch at convenience | 90 days |

---

## 5. Security Training

- All engineers complete OWASP Top 10 awareness training within 30 days of joining
- Annual security awareness training for all staff
- Developers working on authentication or marketplace integration code complete additional training on OAuth 2.0 security and API security best practices
- Security incidents and near-misses are shared as learning events in monthly engineering retrospectives

---

## 6. Exceptions

Any exception to this policy requires:
1. Written justification explaining why the standard cannot be met
2. Documented compensating controls
3. Engineering Lead and Security Lead sign-off
4. Time-limited approval with defined remediation date

All exceptions are tracked in `docs/compliance/exceptions-register.md`.

---

*This policy is reviewed every 6 months. Next review: December 2026. Questions: security@clearsettle.app*
