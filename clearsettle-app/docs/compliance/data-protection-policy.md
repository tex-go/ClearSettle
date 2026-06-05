# Data Protection Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-SEC-DPP-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Chief Security Officer / Compliance Officer |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Data Protection Policy defines how ClearSettle collects, processes, stores, protects, and deletes data obtained from sellers, marketplace integrations, and users of the ClearSettle platform.

ClearSettle processes:
- Seller financial settlement data from Amazon, Flipkart, and other marketplace integrations
- Personally Identifiable Information (PII) of sellers and their business representatives
- Marketplace credential data (OAuth tokens, API keys) used to retrieve settlement reports
- ClearSettle user account data

This policy aligns with Amazon's Data Protection Policy for Selling Partner API developers, applicable Indian data protection law (IT Act 2000 and DPDP Act 2023), and best practices for financial data handling.

---

## 2. Data Classification

### 2.1 Classification Levels

**Level 1 — Highly Confidential (HC)**

Data whose unauthorized disclosure would cause severe financial or reputational harm.

Examples:
- Marketplace OAuth tokens and API credentials (Amazon SP-API refresh tokens, Flipkart OAuth tokens)
- Database credentials and encryption keys
- Seller bank account numbers or financial account details
- Detailed seller financial settlement data

**Level 2 — Confidential (C)**

Data whose unauthorized disclosure would cause material harm.

Examples:
- Seller names, email addresses, phone numbers
- Business registration details (GSTIN, PAN)
- Aggregated settlement summaries
- Platform connection configurations

**Level 3 — Internal (I)**

Data for internal use only; not suitable for public disclosure.

Examples:
- ClearSettle application logs
- Anonymized usage analytics
- Internal audit logs
- System configuration data

**Level 4 — Public (P)**

Data approved for external disclosure.

Examples:
- ClearSettle product documentation
- Public-facing marketing materials
- API documentation

---

## 3. Seller Data Protection

### 3.1 Seller Financial Settlement Data

Seller settlement data (gross revenue, fees, payout amounts, reconciliation results) is classified Level 1 — Highly Confidential.

**Protection Controls:**
- Stored exclusively in the ClearSettle Cloud SQL PostgreSQL database on GCP
- Database encrypted at rest using AES-256 (GCP default encryption)
- All database connections use TLS 1.2 or higher
- Access restricted to authenticated API calls by the account holder or explicitly authorized team members
- Multi-tenant isolation enforced: all data queries include `company_id` filter in `WHERE` clause
- No seller's financial data is accessible to any other seller

**Data Minimization:**
- Only settlement data necessary for reconciliation analysis is ingested
- Raw API response data is stored only where required for audit trail; unnecessary fields are not retained
- Seller PII embedded in settlement reports (customer names, addresses in order data) is not indexed for search and is stored only as part of the raw record

### 3.2 Seller Account Data

Seller account data (email, name, phone, company name) is classified Level 2 — Confidential.

**Protection Controls:**
- Passwords stored as bcrypt hashes (cost factor 12); plaintext passwords are never stored or logged
- Social authentication tokens (Google, Instagram) stored Fernet-encrypted in `social_accounts` table
- Email addresses stored as lowercase normalized strings
- Phone numbers stored without formatting normalization to avoid unnecessary processing

---

## 4. Amazon Data Protection

ClearSettle operates as an Amazon Selling Partner API developer and is bound by the Amazon Data Protection Policy.

### 4.1 Amazon Data Types Processed

ClearSettle processes the following data types received via Amazon SP-API:

| Data Type | SP-API Category | ClearSettle Use | Retention |
|---|---|---|---|
| Settlement financial data | Financial | Reconciliation analysis | 3 years |
| Order summaries (aggregate) | Order | Settlement matching | 3 years |
| Fee breakdowns | Financial | Fee analysis and disputes | 3 years |
| Seller marketplace IDs | Identifier | Account association | Duration of account |
| SP-API access tokens | Credential | API calls during session | Session only; not persisted |
| SP-API refresh tokens | Credential | Token renewal | Fernet-encrypted; rotated on demand |

### 4.2 Amazon Data Use Restrictions

ClearSettle complies with all Amazon Data Protection Policy requirements:

1. **Permitted Use Only:** Amazon data is used exclusively to provide the ClearSettle settlement reconciliation service to the seller who authorized the data access. Amazon data is never used for advertising, marketing, or any purpose not explicitly authorized by the seller.

2. **No Data Sharing:** Amazon settlement data and seller information is never shared with third parties, including other ClearSettle customers, without the explicit written consent of the seller.

3. **No Data Sale:** Amazon data and any data derived from Amazon data is never sold, licensed, or transferred for commercial gain.

4. **Data Aggregation Restrictions:** Aggregate or anonymized data derived from Amazon SP-API data is not used in any form that would allow identification of individual Amazon sellers.

5. **No Competitive Use:** Amazon data is not used to compete with Amazon or to benefit any Amazon competitor.

6. **Data Accuracy:** Settlement and financial data is stored as received from the Amazon SP-API without modification. Calculated fields (reconciliation results, variance amounts) are stored alongside original source data for audit purposes.

### 4.3 Amazon Credential Protection

**Amazon SP-API Refresh Tokens:**
- Never stored in plaintext
- Encrypted using Fernet symmetric encryption before database storage
- Encryption key stored in GCP Secret Manager, not in the database or application code
- Token values never appear in application logs, error messages, or API responses
- Tokens are invalidated immediately upon seller deauthorization or security incident

**Access Token Handling:**
- SP-API access tokens (short-lived, ~1 hour) are held in application memory only during the API call session
- Access tokens are never persisted to any database, cache, or log
- Token refresh uses the encrypted refresh token retrieved from the database at request time; the decrypted value exists in application memory only for the duration of the refresh call

---

## 5. Flipkart Data Protection

### 5.1 Flipkart Data Processed

| Data Type | Use | Retention |
|---|---|---|
| Settlement payment reports (uploaded files) | Reconciliation analysis | 3 years |
| P&L reports (uploaded files) | Profit analysis | 3 years |
| Flipkart OAuth access tokens | API calls | Not persisted (FLOW A: code exchange only) |
| Flipkart OAuth refresh tokens | Token renewal | Fernet-encrypted; per seller authorization |
| Flipkart seller ID | Account association | Duration of account |

### 5.2 Flipkart OAuth Token Protection

Flipkart OAuth tokens are protected under the same standards as Amazon credentials:

- Tokens encrypted with Fernet before storage in `marketplace_credentials` table
- Refresh token rotation: new refresh token stored on each refresh; old token invalidated
- Tokens revoked immediately upon seller request or account deletion
- Token values never logged or included in API responses

---

## 6. Marketplace Data — General Framework

For all marketplace integrations (Shopify, WooCommerce, Meesho, Myntra, Ajio, Jiomart, eBay, Walmart):

### 6.1 Data Collection Principles

1. **Purpose Limitation:** Data collected only for the purpose of settlement reconciliation and financial analysis as disclosed to the seller
2. **Data Minimization:** Only data necessary for reconciliation is requested from marketplace APIs
3. **Accuracy:** Data is stored as received; corrections are tracked with audit records
4. **Storage Limitation:** Data retained only as long as the seller account is active or as required by applicable law

### 6.2 Marketplace Credential Storage

All marketplace API keys, OAuth tokens, and credentials follow the same protection standard regardless of the marketplace provider:
- Fernet-encrypted in the `marketplace_credentials` database table
- Encryption key in GCP Secret Manager
- Accessed only by the specific seller's authenticated API calls
- Rotated per the marketplace's token lifecycle or sooner on any suspected compromise

---

## 7. Encryption Standards

### 7.1 Encryption at Rest

| Data Store | Encryption Method | Key Management |
|---|---|---|
| Cloud SQL PostgreSQL | AES-256 (GCP managed) | Google-managed encryption keys |
| Marketplace credentials in DB | Fernet (AES-128-CBC) | GCP Secret Manager |
| File uploads in GCS | AES-256 (GCP managed) | Google-managed encryption keys |
| Application logs in Cloud Storage | AES-256 (GCP managed) | Google-managed encryption keys |

### 7.2 Encryption in Transit

- All public API endpoints use TLS 1.2 minimum, TLS 1.3 preferred
- TLS certificates are valid, not self-signed, and renewed before expiration
- HTTP to HTTPS redirect enforced at Nginx layer
- HSTS enforced with max-age of 63072000 seconds
- Cloud SQL connections use TLS (enforced by SSL mode configuration)
- All inter-service communication within the GCP VPC uses TLS

### 7.3 Encryption for Mobile Clients

- Flutter mobile app stores JWT tokens using `flutter_secure_storage` which uses the Android Keystore (Android) and iOS Keychain (iOS)
- Hive boxes containing sensitive data are encrypted using AES-256 with a key stored in `flutter_secure_storage`
- No financial data is stored in unencrypted local storage on mobile devices

---

## 8. Data Access Logging

All access to Level 1 and Level 2 data is logged with:
- Timestamp (UTC)
- User ID or service account
- IP address (for user requests)
- Data type and record count accessed
- Operation type (read, write, delete, export)

Access logs are stored in Cloud Logging for 12 months and archived to Cloud Storage for 3 years.

---

## 9. Data Retention

See [Data Retention Policy](data-retention-policy.md) for complete retention schedules.

Summary:
- Seller financial data: 3 years from last activity or account closure
- Marketplace credentials: Deleted within 30 days of authorization revocation
- Access logs and audit logs: 3 years
- Seller account data: 30 days after account deletion request

---

## 10. Data Deletion

### 10.1 Account Deletion

When a seller requests account deletion:

1. All OAuth tokens and marketplace credentials are immediately revoked and deleted from the `marketplace_credentials` and `social_accounts` tables
2. Financial settlement data (ingestion_ledger, settlements, payout_events) is scheduled for deletion within 30 days
3. User account data is scheduled for deletion within 30 days
4. Cloud Storage files (uploaded reports) are deleted within 30 days
5. Backup data containing the account is expired per the backup rotation schedule (maximum 30 additional days after deletion)
6. A deletion confirmation is sent to the seller's registered email address

### 10.2 Data Deletion on API Authorization Revocation

When a seller revokes ClearSettle's Amazon SP-API or Flipkart OAuth authorization:

1. All OAuth refresh tokens for that marketplace are immediately deleted
2. No further data is retrieved from the marketplace API
3. Historical settlement data remains unless the seller requests full account deletion
4. The seller is notified of the revocation by email

---

## 11. Data Subject Rights

Sellers and users have the following rights over their data:

- **Right of Access:** Sellers can request an export of all their data stored by ClearSettle via the account settings page or by contacting privacy@clearsettle.app
- **Right of Correction:** Sellers can update their account information in the ClearSettle platform
- **Right of Deletion:** Sellers can request full account deletion via account settings
- **Right of Portability:** Sellers can export their settlement data in CSV format via the platform

Requests must be processed within 30 days of receipt. Identity verification is required before data export or deletion.

---

*This policy is reviewed every 6 months. Next review: December 2026. Questions: privacy@clearsettle.app*
