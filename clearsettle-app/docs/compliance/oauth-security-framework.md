# OAuth Security Framework

| Field | Value |
|---|---|
| **Document ID** | CLS-SEC-OAF-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Chief Security Officer / CTO |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This framework defines the OAuth 2.0 security architecture for all ClearSettle integrations that use OAuth authorization flows, including:

- Amazon SP-API (LWA — Login with Amazon)
- Flipkart Seller API (planned)
- Google OAuth 2.0 (social authentication)
- Instagram/Meta OAuth 2.0 (social authentication)
- Future marketplace OAuth providers (Shopify, eBay, and others)

This framework covers the complete OAuth lifecycle: authorization, token management, refresh, revocation, session security, and audit logging.

---

## 2. OAuth State Validation and CSRF Protection

### 2.1 State Token Generation

For every OAuth authorization request initiated by ClearSettle:

1. A cryptographically secure random state token is generated: `secrets.token_urlsafe(32)` (Python) yielding 256 bits of entropy
2. The state token is stored server-side associated with the user's authenticated session
3. The state token is included in the `state` parameter of the authorization URL
4. State tokens expire after **10 minutes** (enforced by the `oauth_states` table with TTL)

### 2.2 State Validation on Callback

On every OAuth callback received by ClearSettle:

1. The `state` parameter is extracted from the callback URL
2. ClearSettle looks up the state token in the `oauth_states` table
3. If the state token is not found or has expired: **reject the callback with HTTP 400**
4. If the state token matches: mark it as consumed (deleted) and proceed with the code exchange
5. If no `state` parameter is present: **reject the callback with HTTP 400**

This prevents Cross-Site Request Forgery (CSRF) attacks where an attacker tricks a seller into authorizing access with a forged callback URL.

### 2.3 State Token Binding

For marketplace OAuth flows (not social auth), the state token is additionally bound to:
- The authenticated ClearSettle user's session ID
- The intended marketplace (e.g., `amazon`, `flipkart`)
- The ClearSettle company ID

This prevents state fixation attacks and ensures the authorization is applied to the correct seller account.

---

## 3. PKCE Support

### 3.1 What is PKCE

Proof Key for Code Exchange (PKCE, RFC 7636) prevents authorization code interception attacks, particularly important for mobile applications.

### 3.2 ClearSettle PKCE Implementation

**Mobile App (Flutter):**
- PKCE is implemented for all OAuth flows initiated from the Flutter mobile application
- `code_verifier`: cryptographically random 64-byte string
- `code_challenge`: BASE64URL(SHA256(code_verifier))
- `code_challenge_method=S256`
- The `code_verifier` is stored in `flutter_secure_storage` for the duration of the authorization flow

**Web Application:**
- PKCE is used for all OAuth flows where the provider supports it
- Amazon SP-API LWA supports PKCE; ClearSettle implements it when available
- Social authentication (Google, Instagram) handled via `id_token` verification rather than code flow on web, so PKCE is not applicable

**Provider Support:**

| Provider | PKCE Support | ClearSettle Implementation |
|---|---|---|
| Amazon LWA | Yes | Implemented |
| Google OAuth | Yes | Implemented on mobile |
| Instagram OAuth | Yes | Implemented on mobile |
| Flipkart OAuth | TBD | Will implement when available |
| Shopify OAuth | No (standard flow) | N/A |

---

## 4. Refresh Token Rotation

### 4.1 Rotation Strategy

ClearSettle implements refresh token rotation for all marketplace OAuth integrations:

1. When a new access token is obtained using a refresh token, the new refresh token (if provided by the IdP) replaces the old one immediately
2. The old refresh token is deleted from the `marketplace_credentials` table within the same database transaction as storing the new token
3. If the IdP does not issue a new refresh token with each access token refresh (one-time rotation), the original refresh token is retained

### 4.2 Token Rotation for Social Auth

For ClearSettle user authentication (Google, Instagram):
- ClearSettle issues its own short-lived JWT access tokens (30 minutes) and long-lived opaque refresh tokens (7 days)
- Refresh tokens are rotated on every use: each call to `POST /auth/refresh` issues a new refresh token and invalidates the old one
- Rotated tokens are stored in the `refresh_tokens` table with SHA-256 hash; plaintext tokens are never stored
- Refresh token rotation is atomic: the old token is invalidated in the same transaction as the new token being issued

### 4.3 Rotation Failure Handling

If a token rotation operation fails (e.g., database error):
- The system errs on the side of security: the operation is rejected rather than issuing tokens in an inconsistent state
- The user is returned an authentication error and must authenticate again
- The failure is logged for investigation

---

## 5. Token Encryption

### 5.1 Encryption Method

All OAuth tokens stored in ClearSettle's database are encrypted using **Fernet symmetric encryption** (from the `cryptography` Python library):
- Algorithm: AES-128 in CBC mode with PKCS7 padding
- Authentication: HMAC-SHA256
- Key size: 256 bits (32 bytes)

### 5.2 Key Management

- The active Fernet key is stored exclusively in **GCP Secret Manager**
- The key is loaded into application memory at startup via the Secret Manager API
- The key is never stored in the database, application configuration files, or environment variable files committed to source control
- Key rotation follows an annual schedule minimum; emergency rotation on any suspicion of compromise

### 5.3 What is Encrypted

| Token Type | Encrypted Column | Table |
|---|---|---|
| Amazon SP-API refresh token | `refresh_token_enc` | `marketplace_credentials` |
| Amazon SP-API access token | Not persisted | N/A |
| Flipkart OAuth refresh token | `refresh_token_enc` | `marketplace_credentials` |
| Flipkart OAuth access token | `access_token_enc` | `marketplace_credentials` |
| Google social auth token | `access_token_enc` | `social_accounts` |
| Instagram social auth token | `access_token_enc` | `social_accounts` |
| ClearSettle refresh tokens | SHA-256 hash (not encrypted) | `refresh_tokens` |

**Note:** ClearSettle's own JWT access tokens are signed but not encrypted — they are bearer tokens verified on each request by the JWT signing key.

### 5.4 Token Handling in Code

All token encryption and decryption is handled by `app/core/crypto.py`:
- `encrypt(value: str) -> str` — encrypts and returns Fernet ciphertext
- `decrypt(ciphertext: str) -> str` — decrypts and returns plaintext; raises on invalid token
- Both functions are the exclusive entry points for token encryption operations
- Decrypted token values must not be assigned to variables with longer scope than the API call in which they are used

---

## 6. Token Revocation

### 6.1 Revocation Triggers

OAuth tokens are revoked in the following circumstances:

| Trigger | Action | Timing |
|---|---|---|
| Seller disconnects marketplace | Delete from marketplace_credentials; call IdP revocation endpoint if available | Immediate |
| Seller deletes account | Delete all marketplace credentials | Within 30 days (immediate for credentials) |
| Security incident (Severity 1) | Emergency deletion of affected tokens | Within 1 hour of incident declaration |
| Security incident (Severity 2+) | Investigation; revoke if compromise confirmed | Within 24 hours of confirmation |
| Unusual API activity detected | Temporary suspension; notify seller | Within 1 hour of detection |
| Token expiry (no refresh available) | Delete expired token | Automatic on detection |

### 6.2 IdP Revocation

Where the identity provider offers a token revocation endpoint, ClearSettle calls it:
- Amazon: Token revocation handled by seller revoking access in Seller Central
- Google: `https://oauth2.googleapis.com/revoke?token={access_token}`
- Instagram: Token invalidation via Meta App Dashboard
- Flipkart: Token revocation via Flipkart API (when implemented)

### 6.3 Database Revocation

Regardless of IdP revocation status, ClearSettle deletes all OAuth tokens from its database immediately upon revocation trigger. This ensures that even if an IdP revocation call fails, the token cannot be used through ClearSettle's systems.

---

## 7. Session Security

### 7.1 JWT Access Token Properties

| Property | Value |
|---|---|
| Algorithm | HS256 (HMAC-SHA256) |
| Expiry | 30 minutes |
| Claims | sub (user ID), email, jti (unique token ID), exp, iat |
| Storage (mobile) | flutter_secure_storage (iOS Keychain / Android Keystore) |
| Storage (web) | In-memory (React state); NOT in localStorage or cookies |

### 7.2 Refresh Token Properties

| Property | Value |
|---|---|
| Format | Cryptographically random 64 bytes, base64url-encoded |
| Storage (database) | SHA-256 hash only; plaintext discarded after issuance |
| Expiry | 7 days |
| Rotation | Rotated on every use |
| Storage (mobile) | flutter_secure_storage |
| Storage (web) | HttpOnly Secure SameSite=Strict cookie |

### 7.3 Session Invalidation

Sessions are invalidated when:
- Refresh token expires (7 days)
- User explicitly logs out (refresh token deleted)
- User changes password (all refresh tokens deleted)
- Security incident requires session invalidation (all refresh tokens for affected user deleted)
- JWT signing secret is rotated (all existing JWTs immediately invalid)

---

## 8. Account Linking

### 8.1 Linking Rules

When a user authenticates via an OAuth provider and an account already exists in ClearSettle:

**Scenario 1: Same email address, existing email/password account**
- ClearSettle links the social account to the existing account
- The `social_accounts` table receives a new row for the provider
- The user is notified by email that a new social login method was added
- Both authentication methods (email/password and social) remain valid

**Scenario 2: Same provider + provider_user_id (returning social user)**
- ClearSettle identifies the existing social account record
- The existing user account is returned
- Token fields in `social_accounts` are updated with the latest tokens

**Scenario 3: New email, no existing account**
- A new ClearSettle user account is created
- A new `social_accounts` record is created
- The user is onboarded to ClearSettle

**Scenario 4: Conflict — provider_user_id already linked to a different ClearSettle account**
- This should not occur due to the UNIQUE constraint on `(provider, provider_user_id)`
- If detected (database constraint violation), return an error to the user
- Log the incident for review

### 8.2 Account Unlinking Security

- A user cannot unlink their last authentication method if they have no password set
- Unlinking requires the user to be currently authenticated
- Unlink actions are logged in `marketplace_audit_logs`
- The user is notified by email when a social authentication method is unlinked

---

## 9. Audit Logging

### 9.1 OAuth Audit Events

All OAuth events are logged in the `marketplace_audit_logs` table and in Cloud Logging:

| Event | Logged Fields |
|---|---|
| OAuth authorization initiated | user_id, provider, state_token (hashed), timestamp, IP |
| OAuth callback received | provider, state_valid, timestamp, IP |
| OAuth code exchanged for tokens | connection_id, provider, success, timestamp |
| Token refresh | connection_id, provider, success, timestamp |
| Token revoked | connection_id, provider, revocation_reason, timestamp |
| Account linked | user_id, provider, is_new_user, timestamp |
| Account unlinked | user_id, provider, timestamp |
| Unusual activity detected | connection_id, provider, activity_type, timestamp |

**What is NOT logged:**
- Token values (access tokens, refresh tokens) in any log
- Authorization codes
- PKCE code verifiers
- Decrypted credential values

### 9.2 Log Retention

OAuth audit logs are retained per the Data Retention Policy:
- Active logs in Cloud Logging: 12 months
- Archived logs in Cloud Storage: 3 years

---

## 10. Security Testing Requirements

OAuth implementation security must be verified before production deployment:

**Automated Testing:**
- CSRF state token validation tested: verify that callbacks without valid state are rejected
- PKCE validation tested: verify that code challenges are validated correctly
- Token encryption tested: verify that tokens are encrypted before storage and cannot be read in plaintext from the database
- Token rotation tested: verify old token is invalidated after rotation

**Manual Security Review:**
- OAuth flow reviewed by Security Lead before new provider integration goes live
- Penetration test of authorization flow for any new marketplace or social provider

---

*This framework is reviewed every 6 months. Next review: December 2026. Security contact: security@clearsettle.app*
