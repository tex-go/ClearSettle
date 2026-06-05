# Flipkart Security and Compliance Framework

| Field | Value |
|---|---|
| **Document ID** | CLS-MKT-FLK-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Marketplace Compliance Officer / CTO |
| **Classification** | Internal — Confidential |
| **Applicable Agreement** | Flipkart Seller API Developer Agreement (when applicable) |

---

## 1. Purpose and Overview

This document defines ClearSettle's compliance and security framework for the Flipkart marketplace integration. ClearSettle currently processes Flipkart seller data via manual file uploads and is preparing for direct Flipkart Seller API integration.

This framework covers:
1. Manual report upload security (current implementation)
2. OAuth and API integration security (planned implementation)
3. Data protection for Flipkart seller data
4. Audit logging requirements
5. Incident reporting procedures

---

## 2. Current Integration — Manual Report Upload

### 2.1 Overview

Sellers download their Flipkart settlement reports (P&L reports, payment reports) from the Flipkart Seller Hub and upload them to ClearSettle via the secure file upload interface.

### 2.2 Upload Security Controls

**File Validation:**
- Accepted file types: XLSX, XLS, XLSM, CSV only
- File type verified by content inspection (magic bytes), not filename extension alone
- Maximum file size: 100MB enforced at both Nginx and application layer
- Files are scanned for parsing anomalies before processing
- Duplicate detection: SHA-256 hash comparison prevents reprocessing identical files

**Transmission Security:**
- Files transmitted exclusively over HTTPS (TLS 1.2 minimum)
- File upload endpoint uses the same JWT authentication as all other ClearSettle API endpoints
- Multi-part form data is validated against expected schema before processing

**Storage Security:**
- Uploaded files are stored in Google Cloud Storage (GCS) in the `asia-south1` region
- GCS bucket has no public access; files are accessible only via authenticated application API calls
- Files are encrypted at rest using AES-256 (GCP managed keys)
- File storage path uses `{company_id}/{year}/{month}/{uuid}.{ext}` format to prevent path traversal

**Processing Security:**
- File parsing is executed in a background task isolated from the HTTP request lifecycle
- The parsing worker runs in a Docker container with read-only filesystem mounts
- Malformed files are rejected with an error logged; the original file is preserved for audit

### 2.3 Data Handling After Upload

1. File contents are parsed into normalized `ingestion_ledger` records by the Flipkart parser
2. The original file is retained in GCS for audit and reprocessing purposes
3. Parsed records are associated with the uploading seller's `company_id` — no cross-seller data access
4. The ETL service (`ledger_etl.py`) populates `settlements` and `payout_events` from the ledger records
5. The original uploaded file is retained for the duration specified in the Data Retention Policy

---

## 3. Planned API Integration — Flipkart Seller API

### 3.1 OAuth 2.0 Flow

When Flipkart API integration is implemented, ClearSettle will use the Flipkart Seller API's OAuth 2.0 authorization flow:

1. Seller initiates connection from ClearSettle platform settings
2. ClearSettle generates a cryptographic CSRF state token and stores it in the seller's session
3. ClearSettle redirects the seller to the Flipkart authorization endpoint with:
   - `client_id` (ClearSettle's registered Flipkart app ID)
   - `redirect_uri` (ClearSettle's registered callback URL)
   - `scope` (required API permissions: `seller_read`, `financials_read`)
   - `state` (CSRF token)
   - `response_type=code`
4. Seller approves the authorization on Flipkart Seller Hub
5. Flipkart redirects to ClearSettle callback with authorization code and state
6. ClearSettle validates the `state` parameter — requests with invalid state are rejected
7. ClearSettle exchanges the authorization code for access and refresh tokens
8. Tokens are immediately Fernet-encrypted and stored in `marketplace_credentials`

### 3.2 Token Storage and Security

Flipkart API tokens are protected under the same standards as Amazon credentials:

- All tokens Fernet-encrypted before database storage
- Encryption key in GCP Secret Manager
- Token values never logged or included in API responses
- Refresh token rotation: new refresh token stored on each refresh, old token invalidated
- Token revocation: immediate deletion on seller request, account deletion, or security incident

### 3.3 API Data Access Scope

ClearSettle will request only the minimum Flipkart API permissions required for reconciliation:
- Financial settlement data (payment reports)
- Order summary data (for reconciliation matching)
- Fee breakdown data

ClearSettle will not request:
- Listing management permissions
- Inventory management permissions
- Customer data beyond what is included in settlement reports
- Any permission not required for the stated reconciliation purpose

---

## 4. Flipkart Data Protection

### 4.1 Data Types Processed

| Data Type | Source | Classification | Use |
|---|---|---|---|
| Settlement payment reports | File upload / API | Level 1 — HC | Reconciliation |
| P&L reports | File upload | Level 1 — HC | Profit analysis |
| Order-level data | Embedded in reports | Level 2 — C | Settlement matching |
| SKU-level data | Embedded in reports | Level 2 — C | Product analytics |
| TCS/TDS data | Embedded in reports | Level 1 — HC | Tax compliance |
| Flipkart seller ID | API / upload metadata | Level 2 — C | Account association |
| Flipkart OAuth tokens | OAuth flow | Level 1 — HC | API authorization |

### 4.2 Data Isolation

- All Flipkart data is isolated by `company_id` in the ClearSettle database
- No seller's Flipkart data is accessible by any other seller
- All database queries include `WHERE company_id = ?` filter enforced at the ORM layer

### 4.3 Data Minimization

- Only settlement and financial data is processed; buyer personal information embedded in detailed order reports is not extracted or indexed
- Seller wallet redemption data (special financial transactions) is processed as transaction data only
- No Flipkart customer PII is retained beyond what is required for the specific reconciliation record

---

## 5. Audit Logging

### 5.1 Flipkart-Specific Audit Events

| Event | Logged Fields |
|---|---|
| Flipkart report uploaded | company_id, file_id, file_hash, timestamp, IP |
| Flipkart report parsed | file_id, parser_name, records_count, timestamp |
| Flipkart OAuth authorized (future) | company_id, connection_id, timestamp, IP |
| Flipkart OAuth revoked (future) | company_id, connection_id, revocation_source, timestamp |
| Flipkart API sync triggered (future) | connection_id, sync_type, date_range, timestamp |
| Flipkart credential stored | connection_id, timestamp (no token value) |
| Flipkart credential deleted | connection_id, deletion_reason, timestamp |

### 5.2 Log Retention

Flipkart audit logs are retained for 3 years per the Data Retention Policy.

---

## 6. Access Controls

### 6.1 Seller Data Access

- A seller's Flipkart data is accessible only by:
  1. The authenticated seller themselves (via authorized ClearSettle user accounts)
  2. ClearSettle team members with explicit emergency access authorization (logged and time-limited)
- Flipkart marketplace credentials (OAuth tokens, in future) are accessible only by the application service account's database connection

### 6.2 ClearSettle Team Access

- No ClearSettle team member has routine access to individual seller Flipkart data
- Support team members can view settlement summary data (not raw records) when assisting a seller, with the seller's consent
- All team access to seller data is logged in `marketplace_audit_logs`

---

## 7. Data Retention

| Data Type | Retention | Deletion Trigger |
|---|---|---|
| Uploaded Flipkart files (GCS) | 3 years | Account deletion |
| Parsed settlement records (DB) | 3 years | Account deletion or seller request |
| Flipkart OAuth tokens | Duration of authorization | Revocation or account deletion |
| Processing logs | 12 months | Automatic rotation |
| Audit logs | 3 years | Automatic archive rotation |

---

## 8. Security Controls

### 8.1 Upload Security Controls

| Control | Implementation |
|---|---|
| HTTPS enforcement | TLS 1.2+ enforced at Nginx; HSTS enabled |
| Authentication | JWT required on all upload endpoints |
| File type validation | Content inspection (magic bytes) + extension check |
| File size limits | 100MB at Nginx and application layer |
| Duplicate detection | SHA-256 hash comparison |
| Malware scanning | Parser rejection of malformed/unexpected content |
| Access logging | All uploads logged with file_id, company_id, timestamp |

### 8.2 Storage Security Controls

| Control | Implementation |
|---|---|
| Encryption at rest | AES-256 (GCP managed keys) |
| Bucket access policy | Private; no public access; IAM-controlled |
| Data residency | GCP asia-south1 (Mumbai) |
| Backup | Versioning enabled on GCS bucket |
| Path security | UUID-based paths prevent enumeration |

---

## 9. Incident Reporting

### 9.1 Flipkart Incident Notification

If a security incident affects Flipkart seller data:

1. ClearSettle Security Lead assesses scope within 6 hours of incident declaration
2. If Flipkart data is confirmed affected:
   - Seller whose data was affected is notified within 72 hours
   - ClearSettle's Flipkart partner contact is notified if the incident involves Flipkart API credentials or integration (for future API integration)
3. Incident documented in the security incident log per Incident Response Policy

### 9.2 Flipkart Security Contact

Flipkart security notifications are directed to:
- Flipkart Seller Hub support (for future API integration incidents)
- ClearSettle security@clearsettle.app (for internal reporting)

---

## 10. Future Marketplace API Integration Security Checklist

Before Flipkart API integration goes live, the following security requirements must be satisfied:

- [ ] Flipkart Developer Agreement reviewed and signed
- [ ] OAuth 2.0 flow implemented per Section 3 specifications
- [ ] FlipkartConnector implements `IngestionConnector` interface with `external_event_id` for idempotency
- [ ] CSRF state validation implemented and tested
- [ ] Token encryption and storage implemented and reviewed by Security Lead
- [ ] Rate limiting implemented per Flipkart API documentation
- [ ] Audit logging implemented for all token and API events
- [ ] Incident reporting contact for Flipkart established
- [ ] Seller authorization flow reviewed for clear consent language
- [ ] Deauthorization webhook (if available) implemented
- [ ] Security review of FlipkartConnector code by Security Lead
- [ ] Penetration test of OAuth flow

---

*This framework is reviewed every 6 months. Next review: December 2026. Security contact: security@clearsettle.app*
