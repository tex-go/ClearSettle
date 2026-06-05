# Marketplace Security Framework

| Field | Value |
|---|---|
| **Document ID** | CLS-MKT-FRM-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Chief Security Officer / CTO |
| **Classification** | Internal — Confidential |

---

## 1. Purpose

This framework defines the security architecture, integration patterns, and compliance requirements for all marketplace integrations in ClearSettle. It serves as the single reference for implementing new marketplace connectors securely and consistently.

The framework ensures that adding a new marketplace (Shopify, WooCommerce, Meesho, Myntra, Ajio, Jiomart, eBay, Walmart, or any future marketplace) requires no changes to the security architecture, ETL pipeline, dashboard, or analytics layers.

---

## 2. Marketplace Provider Model

ClearSettle classifies all marketplaces into four provider types based on their integration method:

### 2.1 OAuth Providers

Marketplaces using standard OAuth 2.0 authorization code flow.

**Current:** Amazon SP-API (LWA), Flipkart (planned), Instagram (social auth)

**Characteristics:**
- Short-lived access tokens (minutes to hours)
- Long-lived refresh tokens
- User-authorized scope
- Token refresh required

**Security Requirements:**
- CSRF state token mandatory
- PKCE required where supported by the provider
- Refresh token encrypted with Fernet before storage
- Access token held in application memory only; never persisted

---

### 2.2 API Key Providers

Marketplaces using long-lived API keys for authentication.

**Current:** Meesho (planned), WooCommerce (planned)

**Characteristics:**
- Long-lived API keys
- No user-facing OAuth flow
- API key provided by seller in platform settings

**Security Requirements:**
- API keys encrypted with Fernet before storage
- API keys never displayed in plaintext after initial entry (masked: `*****abc123`)
- API key transmitted only over TLS 1.2+
- API key rotation mechanism provided to seller in platform settings

---

### 2.3 Manual Upload Providers

Marketplaces where sellers download reports and upload to ClearSettle.

**Current:** Flipkart (primary), Myntra, Ajio, Jiomart (planned)

**Characteristics:**
- No direct API integration
- Seller manually downloads report from marketplace
- Seller uploads file to ClearSettle
- ClearSettle parses the file and runs reconciliation

**Security Requirements:**
- File validation (magic bytes, size, format)
- SHA-256 deduplication
- Secure GCS storage (encrypted, private)
- Parser isolation in background worker

---

### 2.4 Partner API Providers

Marketplaces using a dedicated partner/seller API with its own authentication model.

**Planned:** Myntra Partner API, Ajio Seller API, Jiomart Seller API, eBay Partner Network, Walmart Marketplace API

**Characteristics:**
- May use API keys, OAuth 2.0, or HMAC-signed requests
- Credentials provided via marketplace's seller/partner portal
- Often requires marketplace approval before API access

**Security Requirements:**
- Credentials encrypted with Fernet before storage
- Credential storage in `marketplace_credentials` table with `provider` field identifying the marketplace
- API requests signed or authenticated per marketplace requirements
- Credential rotation when API credentials expire or on compromise

---

## 3. Unified Connector Architecture

All marketplace integrations implement the `IngestionConnector` interface (see `app/connectors/base.py`). The interface enforces:

```
IngestionConnector
├── authenticate()          — credential validation and token refresh
├── validate_connection()   — health check against marketplace API
├── discover_available_data() — find available data ranges
└── fetch_canonical_events() — yield CanonicalLedgerEvent objects
```

The `LedgerSyncExecutor` handles all database writes using `ON CONFLICT (uploaded_file_id, external_event_id) DO NOTHING` for idempotency. This means:

- A marketplace connector's security properties are determined by the `IngestionConnector` implementation
- The ETL, dashboard, analytics, and reconciliation layers are never changed for new marketplace integrations
- Security controls for data storage, encryption, and access are implemented once in `LedgerSyncExecutor` and apply to all marketplaces

---

## 4. Security Requirements by Marketplace

### 4.1 Amazon

| Security Control | Implementation |
|---|---|
| Authorization | LWA OAuth 2.0 with CSRF state |
| Token storage | Fernet-encrypted in marketplace_credentials |
| Access logging | All SP-API calls logged with connection_id |
| Data use | Settlement reconciliation only per DPP |
| Incident notification | 24-hour Amazon notification obligation |
| Token revocation | Immediate on seller request or compromise |
| Data retention | 3 years per Amazon DPP |

See [Amazon SP-API Compliance](amazon-sp-api-compliance.md) for full details.

---

### 4.2 Flipkart

| Security Control | Implementation |
|---|---|
| Authorization | OAuth 2.0 (planned); manual upload (current) |
| Token storage | Fernet-encrypted in marketplace_credentials |
| File storage | GCS private bucket, AES-256 encrypted |
| Access logging | All upload and API events logged |
| Data use | Settlement reconciliation and P&L analysis |
| Token revocation | Immediate on seller request or compromise |
| Data retention | 3 years |

See [Flipkart Security Compliance](flipkart-security-compliance.md) for full details.

---

### 4.3 Shopify

| Security Control | Implementation |
|---|---|
| Authorization | Shopify OAuth 2.0 (HMAC validation on callback) |
| Token storage | Fernet-encrypted in marketplace_credentials |
| Webhook security | HMAC-SHA256 signature validation |
| API scope | `read_orders`, `read_finances` (minimum required) |
| Data use | Order and settlement reconciliation |
| Token revocation | Immediate on seller request |
| Data retention | 3 years |
| Implementation status | Planned (Phase 5 per roadmap) |

**Shopify-specific requirement:** Shopify OAuth callbacks include an `hmac` parameter that must be validated against the Shopify client secret before processing. ClearSettle implements this validation in the `ShopifyConnector` to prevent callback forgery.

---

### 4.4 WooCommerce

| Security Control | Implementation |
|---|---|
| Authorization | OAuth 1.0a or API Key pair (consumer key + secret) |
| Credential storage | Fernet-encrypted in marketplace_credentials |
| Connection | HTTPS required; HTTP connections rejected |
| Data use | Order and settlement reconciliation |
| Data retention | 3 years |
| Implementation status | Planned (Phase 5 per roadmap) |

**WooCommerce note:** WooCommerce REST API supports two authentication methods. ClearSettle implements the API Key pair method (consumer key + consumer secret) as it is simpler to manage securely than OAuth 1.0a.

---

### 4.5 Meesho

| Security Control | Implementation |
|---|---|
| Authorization | API Key (X-API-KEY header) |
| Credential storage | Fernet-encrypted in marketplace_credentials |
| API scope | Minimum required for settlement data |
| Data use | Settlement reconciliation |
| Data retention | 3 years |
| Implementation status | Skeleton connector ready (Phase 4 per roadmap) |

---

### 4.6 Myntra

| Security Control | Implementation |
|---|---|
| Authorization | File upload (current); Partner API (planned) |
| Credential storage | Fernet-encrypted in marketplace_credentials |
| Data use | Settlement reconciliation |
| Data retention | 3 years |
| Implementation status | Manual upload (skeleton), API planned |

---

### 4.7 Ajio

| Security Control | Implementation |
|---|---|
| Authorization | File upload (current); Seller API (planned) |
| Credential storage | Fernet-encrypted in marketplace_credentials |
| Data use | Settlement reconciliation |
| Data retention | 3 years |
| Implementation status | Manual upload (skeleton), API planned |

---

### 4.8 Jiomart

| Security Control | Implementation |
|---|---|
| Authorization | Seller API credentials (planned) |
| Credential storage | Fernet-encrypted in marketplace_credentials |
| Data use | Settlement reconciliation |
| Data retention | 3 years |
| Implementation status | Planned |

---

### 4.9 eBay

| Security Control | Implementation |
|---|---|
| Authorization | eBay OAuth 2.0 |
| Token storage | Fernet-encrypted in marketplace_credentials |
| API scope | `https://api.ebay.com/oauth/api_scope/sell.finances` (minimum) |
| Data use | Settlement reconciliation |
| Data retention | 3 years |
| Implementation status | Planned |

---

### 4.10 Walmart Marketplace

| Security Control | Implementation |
|---|---|
| Authorization | Walmart Marketplace API — signature-based (Consumer ID + Private Key) |
| Credential storage | Fernet-encrypted in marketplace_credentials |
| Data use | Settlement reconciliation |
| Data retention | 3 years |
| Implementation status | Planned |

---

## 5. Marketplace Credential Storage Schema

All marketplace credentials are stored in the `marketplace_credentials` table:

```sql
marketplace_credentials:
  id                  UUID PRIMARY KEY
  connection_id       UUID FK → marketplace_connections.id
  credential_type     VARCHAR(50)  -- oauth_token | api_key | api_key_pair | private_key
  access_token_enc    TEXT         -- Fernet-encrypted access token
  refresh_token_enc   TEXT         -- Fernet-encrypted refresh token
  api_key_enc         TEXT         -- Fernet-encrypted API key
  api_secret_enc      TEXT         -- Fernet-encrypted API secret
  token_expiry        TIMESTAMP    -- UTC expiry of access token
  token_scope         VARCHAR(500) -- granted OAuth scopes
  created_at          TIMESTAMP
  updated_at          TIMESTAMP
```

The `credential_type` field determines which encrypted columns are used. ClearSettle's `token_service.py` handles encryption/decryption transparently.

---

## 6. Security Review Checklist for New Marketplace Integration

Before any new marketplace integration is deployed to production, the following security checklist must be completed and signed off by the Security Lead:

**Authorization and Authentication:**
- [ ] OAuth flow implements CSRF state token validation
- [ ] PKCE implemented if supported by the marketplace
- [ ] API key/secret stored Fernet-encrypted; never in plaintext
- [ ] Token refresh logic tested and handles token expiry gracefully

**Data Handling:**
- [ ] `external_event_id` set on all canonical events for idempotency
- [ ] Settlement ID populated on all PAYOUT events (required for ETL grouping)
- [ ] Data minimization: only required scopes requested
- [ ] PII stripping applied before data sent to Anthropic API

**Logging and Monitoring:**
- [ ] All authorization events logged in `marketplace_audit_logs`
- [ ] All API call events logged with connection_id and response code
- [ ] Token creation and deletion events logged

**Error Handling:**
- [ ] API errors do not expose credential values in error messages or logs
- [ ] Rate limit handling implemented with exponential backoff
- [ ] Marketplace downtime handled gracefully (connector returns error, sync marked failed)

**Incident Response:**
- [ ] Marketplace security contact identified and documented
- [ ] Token revocation procedure documented and tested
- [ ] Incident response playbook updated for new marketplace

**Code Review:**
- [ ] Connector code reviewed by Security Lead
- [ ] No hardcoded credentials or secrets
- [ ] No sensitive data in log statements
- [ ] Unit tests for authorization and error handling paths

---

## 7. Marketplace Data Use Restrictions

Regardless of the marketplace, ClearSettle commits to the following universal data use restrictions:

1. **Purpose limitation:** Marketplace data is used only for settlement reconciliation, financial analytics, and dispute support as disclosed to the seller
2. **No competitive use:** Data is not used to build or improve products that compete with any marketplace
3. **No resale:** Marketplace data is never sold, licensed, or monetized beyond the ClearSettle subscription service
4. **No data aggregation for external use:** Anonymized or aggregated marketplace data is not shared externally without the explicit written consent of ClearSettle's legal team
5. **Deletion on request:** All marketplace data is deleted within 30 days of seller account deletion

---

*This framework is reviewed every 6 months. Next review: December 2026. Security contact: security@clearsettle.app*
