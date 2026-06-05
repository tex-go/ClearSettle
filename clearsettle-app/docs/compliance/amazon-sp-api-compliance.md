# Amazon SP-API Compliance Framework

| Field | Value |
|---|---|
| **Document ID** | CLS-MKT-AMZ-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Marketplace Compliance Officer / CTO |
| **Classification** | Internal — Confidential |
| **Applicable Agreement** | Amazon Selling Partner API Developer Agreement |

---

## 1. Purpose and Overview

This document defines ClearSettle's compliance framework for the Amazon Selling Partner API (SP-API). ClearSettle operates as an Amazon Solution Provider, connecting sellers to ClearSettle's settlement reconciliation platform via the SP-API.

ClearSettle's obligations include the Amazon Data Protection Policy (DPP), the Acceptable Use Policy (AUP), and the Selling Partner API Developer Agreement. This framework documents how ClearSettle fulfills each obligation.

---

## 2. Application Information

| Field | Value |
|---|---|
| **Application Name** | ClearSettle — Settlement Reconciliation Platform |
| **Application Type** | Solution Provider |
| **Primary API Usage** | Finances API (ListFinancialEventGroups, ListFinancialEvents) |
| **Data Types Processed** | Financial settlement data, order summaries, fee breakdowns |
| **Developer Country** | India |
| **Support Contact** | support@clearsettle.app |
| **Security Contact** | security@clearsettle.app |

---

## 3. OAuth Flow and Seller Authorization

### 3.1 Authorization Flow

ClearSettle uses Amazon's OAuth 2.0 flow for seller authorization:

1. **Initiation:** Seller clicks "Connect Amazon" in ClearSettle platform settings
2. **Authorization URL:** ClearSettle redirects the seller to Amazon's authorization endpoint:
   ```
   https://sellercentral.amazon.com/apps/authorize/consent
   ?application_id={ClearSettle_App_ID}
   &state={csrf_state_token}
   &version=beta
   ```
3. **State Parameter:** A cryptographically random 32-byte CSRF state token is generated per authorization request, stored in the ClearSettle session, and validated on callback. Requests with mismatched state values are rejected.
4. **Callback:** Amazon redirects to ClearSettle's registered callback URI with the authorization code and state parameter
5. **Code Exchange:** ClearSettle exchanges the authorization code for a refresh token via Amazon's LWA (Login with Amazon) token endpoint
6. **Token Storage:** The refresh token is immediately Fernet-encrypted and stored in the `marketplace_credentials` table; the authorization code is discarded
7. **Seller Notification:** The seller receives an in-app confirmation that Amazon has been connected

### 3.2 Seller Deauthorization

When a seller revokes ClearSettle's authorization in Seller Central:

1. Amazon sends a deauthorization notification to ClearSettle's registered endpoint
2. ClearSettle immediately sets the marketplace connection status to `revoked`
3. The refresh token and access token are deleted from `marketplace_credentials`
4. No further API calls are made for this seller
5. Existing historical settlement data is retained per the seller's account settings
6. The seller is notified by email of the deauthorization

### 3.3 Multiple Marketplace Authorization

ClearSettle supports sellers operating across multiple Amazon marketplaces. Each marketplace authorization (Amazon.in, Amazon.com, etc.) is managed as a separate connection with its own credentials.

---

## 4. Refresh Token Handling

### 4.1 Token Storage

- Amazon SP-API refresh tokens are stored exclusively in the `marketplace_credentials` table in ClearSettle's Cloud SQL PostgreSQL database
- Tokens are Fernet-encrypted (AES-128-CBC) before database storage
- The encryption key is stored in GCP Secret Manager; it is never stored in the database or application code
- Token values never appear in:
  - Application logs or error messages
  - API response bodies
  - Error notifications
  - Monitoring dashboards

### 4.2 Token Access

- Decrypted token values exist in application memory only during the specific API call that requires them
- Tokens are accessed via the `token_service.py` module which enforces encryption/decryption
- Only the application service account has `SELECT` access on the `marketplace_credentials` table
- No direct database access for individual engineers without documented emergency procedures

### 4.3 Token Rotation

- Refresh tokens are rotated upon any indication of compromise
- ClearSettle honors Amazon's token expiration windows and does not cache tokens beyond their validity period
- Access tokens (short-lived, ~1 hour) are not persisted; they are retrieved at API call time and discarded after use

### 4.4 Token Revocation

ClearSettle can revoke Amazon tokens in the following circumstances:

- Seller request: token is immediately deleted from the database
- Security incident: Incident Commander authorizes emergency token deletion
- Account deletion: all marketplace credentials including Amazon tokens are deleted
- Compromise detection: automated monitoring triggers token revocation if anomalous API usage is detected

---

## 5. Audit Logging

### 5.1 Amazon-Specific Audit Events

All the following events are logged in the `marketplace_audit_logs` table and in Cloud Logging:

| Event | Fields Logged |
|---|---|
| Seller authorizes Amazon connection | company_id, connection_id, marketplace_slug, timestamp, IP |
| Seller revokes Amazon authorization | company_id, connection_id, revocation_source, timestamp |
| SP-API access token requested | connection_id, timestamp, endpoint_called |
| SP-API call made | connection_id, endpoint, response_code, timestamp, records_returned |
| Settlement data ingested | connection_id, uploaded_file_id, records_count, timestamp |
| Refresh token encrypted and stored | connection_id, timestamp (no token value) |
| Refresh token deleted | connection_id, deletion_reason, timestamp |
| Security incident declared | incident_id, affected_connections, timestamp |

### 5.2 Log Retention

Amazon-related audit logs are retained for 3 years in Cloud Logging (12 months online) and Cloud Storage (3-year archive with immutable retention lock).

### 5.3 Log Access

Amazon audit logs are accessible to:
- The seller whose data is being logged (via audit export on request)
- ClearSettle Security Lead (for incident investigation)
- Amazon (during compliance review or in response to a security incident)

---

## 6. Data Usage Controls

### 6.1 Permitted Uses

ClearSettle uses Amazon SP-API data exclusively for the following permitted purposes:

1. **Settlement Reconciliation:** Comparing Amazon settlement amounts against expected amounts based on orders, fees, and marketplace policies
2. **Financial Analytics:** Providing sellers with aggregated financial insights including gross revenue, net settlement, fee breakdown, and reconciliation variance
3. **Discrepancy Detection:** Identifying potential fee overcharges, missing payouts, and reconciliation anomalies for the seller's review and action
4. **Tax Analysis:** Calculating TCS and TDS deductions from Amazon settlements for tax compliance

### 6.2 Prohibited Uses

ClearSettle does not use Amazon SP-API data for any of the following:

- Advertising, marketing, or promotional targeting of sellers or customers
- Selling, licensing, or transferring data to third parties
- Building competitive products or services that replicate Amazon's marketplace functions
- Training machine learning models without the seller's explicit consent
- Comparing seller performance with other sellers on the platform
- Any purpose not disclosed in ClearSettle's Terms of Service and Privacy Policy

### 6.3 Data Sharing Restrictions

Amazon settlement data is never shared with:
- Other ClearSettle customers or sellers
- Third-party analytics platforms
- Advertising networks
- Any party not listed as an approved sub-processor in ClearSettle's Privacy Policy

The only approved sub-processors with potential access to Amazon data are:
1. **Google Cloud Platform** — for infrastructure, database, and log storage
2. **Anthropic** — for AI analysis of settlement patterns (with data minimization applied)

---

## 7. Security Controls

### 7.1 API Security

- All SP-API calls use HTTPS/TLS 1.2 minimum
- SP-API endpoint URLs are not logged (only the endpoint category is logged: `finances`, `orders`, etc.)
- SP-API rate limits are respected; ClearSettle implements exponential backoff on 429 responses
- SP-API responses are validated for expected format before processing; unexpected formats trigger alerts

### 7.2 Infrastructure Security

All SP-API integrations operate within the security controls defined in the ClearSettle [Security Policy](security-policy.md) including:
- Application running in isolated Docker containers within GCP VPC
- No public internet access to the application server directly
- All external traffic through Nginx reverse proxy with Cloud Armor WAF

### 7.3 Access Controls

- SP-API credentials are accessible only by the authenticated seller who owns the connection
- ClearSettle team members cannot access a seller's Amazon connection details without a documented emergency access procedure
- Service account credentials for SP-API are managed per the Secrets Management section of the Security Policy

---

## 8. Data Retention — Amazon

| Data Type | Retention Period | Deletion Trigger |
|---|---|---|
| Settlement financial data (ingestion_ledger) | 3 years | Account deletion or seller request |
| SP-API access logs | 3 years | Automatic archive rotation |
| SP-API refresh tokens | Duration of authorization | Revocation, account deletion, or security incident |
| Raw API response data | 3 years | Automatic archive rotation |
| Audit logs for Amazon events | 3 years | Automatic archive rotation |

Upon account deletion, Amazon data deletion follows the procedure in the [Data Retention Policy](data-retention-policy.md).

---

## 9. Incident Reporting to Amazon

### 9.1 Mandatory Reporting Triggers

ClearSettle must report to Amazon if:
- A security incident results in unauthorized access to Amazon seller data or credentials
- ClearSettle's SP-API credentials or seller refresh tokens are compromised
- Amazon Seller Personally Identifiable Information is exposed
- Any breach of the Amazon Data Protection Policy obligations occurs

### 9.2 Reporting Process

1. **Internal declaration:** Incident Commander declares a Severity 1 incident
2. **Scope confirmation:** Security Lead confirms Amazon data was affected within 6 hours
3. **Amazon notification:** Notification sent via Seller Central support case within **24 hours** of confirmed incident
4. **Notification contents:**
   - Incident description and timeline
   - Amazon data types affected
   - Number of sellers affected
   - Immediate actions taken (token revocation, system isolation)
   - Investigation status and ongoing remediation
5. **Follow-up:** Updated notification provided to Amazon within 5 business days with RCA findings

### 9.3 Reporting Contact

Amazon SP-API security incidents are reported via:
- Seller Central > Help > Contact Amazon
- Amazon Security (security@amazon.com for critical incidents)
- Amazon Solution Provider Network support portal (if applicable)

---

## 10. Acceptable Use Policy Compliance

ClearSettle commits to compliance with Amazon's Acceptable Use Policy:

| AUP Requirement | ClearSettle Control |
|---|---|
| Authorized purpose only | Documented permitted use in this framework; technical controls prevent data export to non-approved destinations |
| No spam or unsolicited contact | ClearSettle does not use Amazon data for any outbound communications |
| No system abuse | SP-API rate limits enforced; monitoring alerts on anomalous call volumes |
| No unauthorized data access | RBAC enforced; sellers can only access their own Amazon data |
| No data manipulation | Settlement data stored as received; any calculated fields are stored separately from source data |
| Security incident reporting | 24-hour Amazon notification requirement documented and drilled in incident response exercises |

---

## 11. Solution Provider Agreement Compliance

ClearSettle acknowledges and operates under the Amazon Selling Partner API Developer Agreement. Key compliance commitments:

1. **Registration accuracy:** ClearSettle's developer registration information is accurate and kept current
2. **Application approval:** ClearSettle only calls SP-API endpoints approved for its registered application
3. **Change notification:** ClearSettle notifies Amazon of material changes to its application or data practices before implementation
4. **Security review:** ClearSettle participates in Amazon security reviews on request
5. **Audit cooperation:** ClearSettle cooperates with Amazon audits of compliance with the Developer Agreement and Data Protection Policy
6. **Agreement updates:** ClearSettle reviews and acknowledges updates to the Developer Agreement within the required timeframe

---

## 12. Data Protection Policy Compliance

ClearSettle's Amazon Data Protection Policy compliance is documented as follows:

| DPP Requirement | Implementation |
|---|---|
| Data encryption at rest | AES-256 (GCP) + Fernet for credentials |
| Data encryption in transit | TLS 1.2+ enforced on all connections |
| Access controls | RBAC with company_id isolation; no cross-seller access |
| Audit logging | All Amazon data access logged with 3-year retention |
| Incident response | 24-hour Amazon notification; IR Policy CLS-SEC-IRP-001 |
| Data deletion | Deletion within 30 days of account closure; credential deletion immediate on revocation |
| Sub-processor disclosure | GCP and Anthropic disclosed; DPA in place with GCP |
| No data sharing | Technical and contractual controls prohibiting unauthorized sharing |

---

*This framework is reviewed every 6 months. Next review: December 2026. Security contact: security@clearsettle.app*
