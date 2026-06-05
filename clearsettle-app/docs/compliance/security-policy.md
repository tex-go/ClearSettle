# Security Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-SEC-POL-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Chief Security Officer / CTO |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Security Policy establishes the security standards, controls, and responsibilities for the ClearSettle platform. It covers all technical and operational security controls protecting the confidentiality, integrity, and availability of seller financial data, marketplace integration credentials, and ClearSettle platform infrastructure.

This policy applies to all ClearSettle employees, contractors, service accounts, and automated systems operating within the ClearSettle environment.

---

## 2. Authentication

### 2.1 Multi-Factor Authentication (MFA)

**Requirements:**

- MFA is mandatory for all ClearSettle employee accounts accessing production systems, cloud infrastructure, and administrative tools
- MFA is mandatory for all ClearSettle customer accounts with organization administrator or finance manager roles
- MFA must be enforced for all GCP Console access without exception
- MFA must be enforced for GitHub repository access for all engineers
- MFA-exempt service accounts are not permitted; service accounts must use cryptographic key authentication

**Accepted MFA Methods:**
1. TOTP authenticator apps (Google Authenticator, Authy) — preferred
2. Hardware security keys (FIDO2/WebAuthn) — preferred for administrative access
3. SMS OTP — permitted only where TOTP is unavailable; not permitted for production system access

**MFA Bypass:** Emergency bypass codes are generated only by the system owner, stored in an encrypted password manager, and their use is automatically logged and reviewed at the next security review.

### 2.2 Password Policy

**Customer Account Passwords:**
- Minimum length: 10 characters
- Must contain: uppercase, lowercase, digit, and special character
- Checked against breached password databases (HaveIBeenPwned API or equivalent)
- Bcrypt hashing with cost factor 12 (approximately 300ms on standard hardware)
- Password history: last 5 passwords cannot be reused
- Account lockout: 5 failed attempts triggers 15-minute lockout with progressive backoff

**Employee Account Passwords:**
- Minimum length: 14 characters
- Managed via an approved password manager (LastPass, 1Password, or equivalent)
- Must be unique per service — no password reuse across systems
- Emergency break-glass passwords stored in encrypted vault with dual-control access

**Social Authentication:**
- Users authenticating via Google OAuth or Instagram OAuth are exempt from password requirements for ClearSettle-issued credentials but are subject to the IdP's security policies
- Social accounts without a password must have MFA enabled at the IdP level where supported

### 2.3 Password Rotation

- **Service account keys and API credentials:** 90-day rotation maximum; automated rotation where technically feasible
- **Database credentials:** 90-day rotation; rotated immediately following any security incident
- **Encryption keys (Fernet):** Annual rotation minimum; keys remain valid for decryption of legacy data but new data uses the current key
- **Amazon SP-API refresh tokens:** Handled per Amazon's token lifecycle; rotated immediately upon any suspected compromise
- **JWT signing secrets:** 180-day rotation; invalidates all existing sessions, communicated to customers in advance
- **Employee system passwords:** 180-day rotation enforced by system policy

---

## 3. Authorization

### 3.1 Role-Based Access Control (RBAC)

ClearSettle implements RBAC for all platform resources. The authoritative role definition is maintained in the `roles` and `permissions` tables in the ClearSettle database.

**Platform Roles (enforced at the API layer):**

| Role | Description | Scope |
|---|---|---|
| `company_admin` | Full access to company data and settings | Per company |
| `finance_manager` | Read/write financial data; cannot manage users | Per company |
| `accountant` | Read/write reconciliation; cannot manage settings | Per company |
| `reconciliation_analyst` | Read reconciliation data; limited write | Per company |
| `gst_consultant` | Read GST and tax data | Per company |
| `branch_manager` | Manage assigned branch | Per branch |
| `auditor` | Read-only access to all financial data | Per company |
| `ca_admin` | CA-level access with cross-company visibility | Platform |
| `viewer` | Read-only; no sensitive financial data | Per company |
| `superadmin` | Full platform access | Platform-wide |

**Infrastructure Roles (GCP IAM):**

| Role | Principals |
|---|---|
| `roles/owner` | CEO + CTO only; requires documented justification |
| `roles/editor` | Engineering Lead; reviewed quarterly |
| `roles/viewer` | All engineers; default access level |
| `roles/cloudsql.admin` | Database Administrator only |
| `roles/secretmanager.secretAccessor` | Production service accounts only |
| `roles/logging.admin` | Security Lead only |

### 3.2 Least Privilege

- All service accounts are granted only the minimum GCP IAM permissions required for their function
- Database service accounts are restricted to specific tables and operations (no `DROP`, `TRUNCATE`, or `CREATE` permissions in production)
- Application database user (`clearsettle_app`) has `SELECT`, `INSERT`, `UPDATE` permissions only; `DELETE` is restricted to the data cleanup service account
- No production access for development team members outside of approved maintenance windows
- All elevated access requests require documented approval and are time-limited to 4 hours maximum

### 3.3 Access Reviews

- Quarterly access review of all GCP IAM bindings
- Quarterly review of all active `superadmin` accounts
- Monthly review of users with `company_admin` role
- Immediate access review following any employee offboarding

---

## 4. Infrastructure Security

### 4.1 Network Security

**GCP VPC Architecture:**
- All ClearSettle production infrastructure operates within a dedicated GCP VPC
- Public internet access is restricted to load balancer and Cloud Armor endpoints only
- Backend services (FastAPI, PostgreSQL/Cloud SQL) have no public IP addresses
- VPC firewall rules follow default-deny with explicit allow rules for documented services
- Cloud SQL is accessible only from the application server's service account over Private IP

**Firewall Rules:**

| Source | Destination | Port | Protocol | Purpose |
|---|---|---|---|---|
| 0.0.0.0/0 | Load Balancer | 443 | HTTPS | Customer and API access |
| Load Balancer | App Server | 8000 | TCP | FastAPI application |
| App Server | Cloud SQL | 5432 | TCP | PostgreSQL access |
| App Server | GCS | * | HTTPS | File storage |
| App Server | Secret Manager | * | HTTPS | Credential retrieval |
| VPN/Bastion | App Server | 22 | SSH | Administrative access only |

**Nginx Security Configuration:**
- TLS 1.2 minimum; TLS 1.3 preferred
- HSTS header enforced with max-age 63072000 with includeSubDomains
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`
- Request size limits enforced at Nginx layer (100MB maximum for file uploads)
- Rate limiting: 60 requests/minute per IP for API endpoints; 5 requests/minute for authentication endpoints

### 4.2 Container Security

**Docker Security Standards:**
- All ClearSettle Docker images are based on official Python and Node slim images
- Images run as non-root users (UID 1000) with no privileged capabilities
- Container filesystems are read-only where feasible; writable mounts are limited to required directories
- No secrets in Docker images or Dockerfiles; all secrets loaded from environment variables at runtime sourced from GCP Secret Manager
- Docker images are scanned for vulnerabilities using Trivy or equivalent before deployment to production
- Containers run with `--security-opt no-new-privileges` flag

**Docker Compose Production Security:**
- Production `docker-compose.yml` uses environment variable substitution for all secret values
- All service-to-service communication within Docker Compose uses internal networks
- No service ports are exposed to the host network interface in production beyond the Nginx reverse proxy

### 4.3 Cloud Infrastructure Security

- All GCP resources are tagged with environment (production/staging/development) and owner
- Cloud Asset Inventory is enabled to track all GCP resources
- GCP Security Command Center Standard tier is enabled
- All Cloud SQL instances have automated backups enabled with 7-day retention
- GCP Organization policies enforce:
  - Restrict public IP on Cloud SQL
  - Require OS login for compute instances
  - Restrict resource locations to approved regions (asia-south1 primary)
- VPC Service Controls enabled around sensitive APIs in production

---

## 5. Application Security

### 5.1 Secure Coding Standards

ClearSettle enforces the following secure coding standards for all production code:

**Input Validation:**
- All user input is validated at the API layer using Pydantic v2 models
- SQL queries use SQLAlchemy ORM exclusively — no raw SQL string interpolation
- File upload validation: file type verified by content inspection (magic bytes), not filename extension alone
- Maximum file upload size enforced at both Nginx (100MB) and application layer

**Output Encoding:**
- API responses are JSON-encoded by FastAPI
- React frontend uses JSX which escapes HTML by default; `dangerouslySetInnerHTML` is prohibited
- CSV exports use proper quoting to prevent CSV injection

**Authentication in Code:**
- JWT tokens are validated on every authenticated request using the `get_current_user` dependency
- Token expiry is enforced; expired tokens receive 401 with `WWW-Authenticate: Bearer` header
- JWT signing uses HS256 with a 256-bit secret minimum
- Refresh tokens are opaque 64-byte random values; only their SHA-256 hash is stored in the database

**Secrets in Code:**
- No secrets, API keys, or credentials are committed to the Git repository
- Pre-commit hooks enforce secret scanning using `detect-secrets` or equivalent
- All secrets are loaded from GCP Secret Manager at application startup
- `.env` files are gitignored; `.env.example` files with non-sensitive placeholder values are used for documentation

### 5.2 Dependency Scanning

- All Python dependencies in `requirements.txt` are pinned to exact versions
- All npm dependencies in `package.json` use pinned or range-locked versions
- Dependabot (or Snyk) is enabled on the GitHub repository for automated vulnerability alerts
- Critical and High severity dependency vulnerabilities must be remediated within 7 days
- Medium severity within 30 days
- Low severity within 90 days or at next planned release
- New dependencies require Security Lead approval for production use

### 5.3 Vulnerability Management

**Vulnerability Scanning:**
- Weekly automated scans of all production API endpoints using OWASP ZAP or equivalent
- Monthly dependency vulnerability assessment
- Quarterly manual code security review of authentication, authorization, and marketplace integration code
- Annual penetration test by a qualified third-party security firm

**Vulnerability Remediation SLA:**

| Severity | CVSS Score | Remediation SLA |
|---|---|---|
| Critical | 9.0-10.0 | 24 hours |
| High | 7.0-8.9 | 7 days |
| Medium | 4.0-6.9 | 30 days |
| Low | 0.1-3.9 | 90 days |

---

## 6. Secrets Management

### 6.1 Secret Storage

All production secrets are stored in **GCP Secret Manager** and accessed by the application at startup via the Secret Manager API using Workload Identity or a dedicated service account with `secretmanager.secretAccessor` role.

**Secrets Managed in GCP Secret Manager:**
- Database connection strings and passwords
- JWT signing secret
- Fernet encryption key for marketplace credentials
- Amazon SP-API client ID and client secret
- Flipkart OAuth client ID and client secret
- Instagram/Meta app ID and secret
- Google OAuth client ID and secret
- Anthropic API key
- SMTP credentials for email delivery

### 6.2 Secret Access Controls

- Production secrets are accessible only by the production application service account
- No developer has direct access to production database credentials
- All secret access is logged in Cloud Logging and reviewed quarterly
- Staging and development environments use separate, lower-privilege secrets

### 6.3 Secret Rotation Schedule

| Secret | Rotation Frequency | Automated |
|---|---|---|
| Database password | 90 days | Manual with notification |
| JWT signing secret | 180 days | Manual with session invalidation |
| Fernet encryption key | 365 days | Manual with key versioning |
| Amazon SP-API credentials | Per Amazon requirements or on compromise | Manual |
| Flipkart OAuth credentials | Per Flipkart requirements or on compromise | Manual |
| GCP service account keys | 90 days | Automated via Cloud Functions |
| SMTP password | 90 days | Manual |

### 6.4 Encryption Key Management

ClearSettle uses Fernet symmetric encryption for marketplace credentials stored in the database.

- The active Fernet key is stored in GCP Secret Manager
- Key rotation uses key versioning: the new key encrypts new data; the old key remains available for decryption of legacy data
- Keys are never logged, exported, or stored outside GCP Secret Manager
- Key compromise triggers immediate rotation and re-encryption of all affected records

---

## 7. Audit Logging

### 7.1 What is Logged

ClearSettle logs the following security-relevant events:

**Authentication Events:**
- All successful and failed login attempts (email, IP, user agent, timestamp)
- JWT token issuance and revocation
- Refresh token rotation
- Social authentication events (provider, provider user ID — no tokens)
- MFA events (enable, disable, bypass)

**Authorization Events:**
- All administrative actions
- Role assignment and removal
- Permission escalation requests
- API endpoint access for sensitive operations

**Marketplace Integration Events:**
- Amazon SP-API token requests and responses (excluding token values)
- Flipkart OAuth flow events
- Marketplace credential creation, update, and deletion
- All `marketplace_audit_log` entries per the ORM model

**Data Access Events:**
- Access to seller financial data (ingestion_ledger queries affecting >100 rows)
- Export operations (CSV exports, report downloads)
- Bulk data operations

### 7.2 Log Retention

- Application logs: 12 months in Cloud Logging
- Security audit logs: 3 years minimum in Cloud Storage (immutable)
- Amazon SP-API access logs: 3 years per Data Protection Policy requirements

### 7.3 Log Protection

- Production logs cannot be deleted by application service accounts
- Cloud Logging export to Cloud Storage uses immutable retention locks
- Log access requires `logging.admin` role (Security Lead only)

---

*This policy is reviewed every 6 months. Next review: December 2026. Questions: security@clearsettle.app*
