# Security Hardening Standards
**Version:** 1.0 | **Owner:** `security-agent`

Financial SaaS is a high-value attack target. These standards define the security posture ClearSettle must maintain. `security-agent` enforces these in every PR review and every release gate.

---

## Authentication Security

### JWT Standards
```python
# Access token: 30 minutes (short-lived)
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ALGORITHM = "HS256"

# Refresh token: 7 days (stored as opaque hash in DB, not decoded)
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Secret key: minimum 256-bit entropy
SECRET_KEY must be >= 32 random bytes, not a human-readable string

# Token validation: always verify signature, expiry, and user existence
```

### Brute Force Protection
```python
# Lock account after 5 failed attempts
# Lockout duration: 15 minutes
# Track by: IP address + email combination
# Never reveal whether email exists (same error for unknown email + wrong password)
```

### Session Management
- Refresh tokens must be stored as bcrypt hash in `refresh_tokens` table
- Refresh token rotation: issue new refresh token on every use, invalidate old
- Logout must invalidate all active refresh tokens for the user
- `remember_me` is NOT a valid feature for financial software — all sessions expire

---

## Authorization (RBAC)

### Roles and Permissions Matrix
```
superadmin: full platform access (internal use only, never exposed to customers)
admin:      full company access (account owner)
member:     standard access (can view, upload, trigger reconciliation)
finance:    read-only financial dashboards
ca:         chartered accountant — read financial data, export only
viewer:     read-only, no sensitive data
```

### Enforcement Rules
- Every protected endpoint must call `get_current_user()` and check `current_user.role`
- Multi-tenant: every query must include `WHERE company_id = current_user.company_id`
- Admin endpoints must additionally check `current_user.is_superadmin`
- Cross-company data access must raise 403, never 404 (prevent enumeration)
- Missing role check on new endpoint = `security-agent` blocks PR

---

## Input Validation

### API Inputs
```python
# Pydantic validators required on all user-facing models
class SettlementImportRequest(BaseModel):
    marketplace: Literal["flipkart", "amazon", "meesho", "myntra"]  # whitelist
    period_start: date  # typed, not string
    period_end: date
    
    @field_validator('period_end')
    def end_after_start(cls, v, info):
        if v <= info.data.get('period_start'):
            raise ValueError("end must be after start")
        return v

# Max string lengths enforced
# Numeric ranges validated
# Date ranges validated (no future dates on historical reports)
```

### File Upload Security
```python
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_CONTENT_TYPES = ["application/vnd.ms-excel", 
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          "text/csv"]
ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]

# Validate content type from file header, not filename extension
# Parse in sandboxed subprocess or memory-limited context
# Never execute uploaded content
# Scan for malicious content before processing
# Store with randomized filename, not original
```

---

## Secret Management

### What Must NEVER Be In Code
```bash
# Run this check before every commit
git secrets --scan
trufflehog filesystem . --only-verified

# Forbidden in code:
SECRET_KEY = "my-secret-key"          # FORBIDDEN
DATABASE_URL = "postgresql://user:password@host" # FORBIDDEN (hardcoded password)
API_KEY = "sk_live_..."               # FORBIDDEN
ENCRYPTION_KEY = "..."                # FORBIDDEN
```

### What Must Be In Environment Variables
```bash
# Required in .env.prod (never committed to repo)
SECRET_KEY=         # 32+ random bytes, URL-safe
DATABASE_URL=       # constructed from POSTGRES_* vars (no special chars in password)
ENCRYPTION_KEY=     # Fernet key (32 URL-safe base64 bytes)
REDIS_PASSWORD=     # 32+ chars, no URL-special chars
POSTGRES_PASSWORD=  # 32+ chars, no URL-special chars
SUPER_ADMIN_PASSWORD=  # 16+ chars, changed before first deploy
```

### Password Generation Standard
```bash
# CORRECT — generates URL-safe password
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# WRONG — may generate URL-unsafe chars (@ / # in base64)
openssl rand -base64 32
```

---

## Data Protection

### Credential Encryption
All marketplace API credentials (SP-API tokens, OAuth tokens) must be encrypted at rest:
```python
# Use Fernet symmetric encryption
from cryptography.fernet import Fernet
fernet = Fernet(settings.ENCRYPTION_KEY)

encrypted = fernet.encrypt(credential.encode())  # store this
decrypted = fernet.decrypt(encrypted).decode()    # retrieve this
```

### PII Handling
- Email addresses: stored in plaintext (needed for login/communication)
- Phone numbers: stored in plaintext (needed for communication)
- Passwords: bcrypt with cost factor 12, never plaintext
- API keys/tokens: Fernet-encrypted, never logged
- Financial data: not PII, but subject to audit requirements

### Data Minimization
- Don't store what you don't need
- Marketplace credentials: store encrypted, rotation encouraged
- Log files: mask email after @, never log full auth tokens

---

## Rate Limiting

```python
# Auth endpoints (strict — brute force target)
/auth/login:       10 requests/minute per IP
/auth/register:    5 requests/minute per IP
/auth/refresh:     30 requests/minute per user

# Upload endpoints (resource-intensive)
/*/upload:         5 requests/minute per user
/*/parse:          5 requests/minute per user

# API endpoints (standard)
/api/*:            100 requests/minute per user

# Admin endpoints (restrict)
/admin/*:          30 requests/minute per superadmin
```

---

## OWASP Top 10 Controls

| Threat | Control |
|---|---|
| A01 Broken Access Control | RBAC on every endpoint, company_id isolation |
| A02 Cryptographic Failures | Fernet for credentials, bcrypt for passwords, TLS 1.2+ |
| A03 Injection | Parameterized queries, Pydantic validation |
| A04 Insecure Design | Threat model per feature, security review gate |
| A05 Security Misconfiguration | Env var validation, no defaults in production |
| A06 Vulnerable Components | pip-audit + npm audit in CI |
| A07 Auth Failures | JWT + refresh rotation, brute force lockout |
| A08 Software Integrity | Docker image signing (future), dependency pinning |
| A09 Logging Failures | Structured audit logs, never log secrets |
| A10 SSRF | Whitelist external URLs, no user-controlled redirect targets |

---

## Security Review Trigger List

`security-agent` must review any PR that touches:
- `app/core/auth.py` or any auth-related file
- RBAC role definitions or permission checks
- File upload paths
- External API integrations (OAuth, SP-API)
- Encryption/decryption code
- New database tables containing user PII or credentials
- Environment variable handling
- Nginx configuration (SSL, headers)
- New third-party dependency with network access
