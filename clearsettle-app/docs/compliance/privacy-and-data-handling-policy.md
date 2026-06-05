# Privacy and Data Handling Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-PDP-POL-015 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 12 months |
| **Next Review** | 2027-06-05 |
| **Owner** | CEO / Data Protection Officer |
| **Classification** | Internal — Public (summary); Confidential (this document) |

---

## 1. Purpose and Scope

This Privacy and Data Handling Policy describes how ClearSettle collects, uses, stores, protects, and discloses personal data and seller financial data. It establishes ClearSettle's data handling obligations and the rights of data subjects.

This policy applies to all data collected through the ClearSettle platform (web app, mobile app, and API), all third-party integrations (Amazon, Flipkart, Meesho, Google, Meta/Instagram), and all ClearSettle personnel who handle data.

---

## 2. Data Controller

**ClearSettle** acts as the data controller for personal data collected directly from sellers and their staff.

For data obtained through marketplace integrations:
- **Amazon SP-API:** ClearSettle acts as a data recipient under Amazon's Selling Partner API Terms; Amazon is the data controller for Selling Partner data
- **Flipkart API:** ClearSettle acts as a data recipient under Flipkart's API terms
- **Google OAuth / Instagram OAuth:** ClearSettle receives user profile data from Google/Meta as authorized by the user during OAuth consent

---

## 3. Data We Collect

### 3.1 Account Registration Data

| Data Element | Purpose | Source |
|---|---|---|
| Full name | Account identity; communications | Directly from user |
| Email address | Login; notifications; support | Directly from user / Google OAuth |
| Phone number (optional) | Account recovery; MFA | Directly from user |
| Company name | Multi-company context; invoicing | Directly from user |
| GST number (optional) | GST report generation | Directly from user |
| Hashed password | Authentication | Derived (never stored in clear) |

### 3.2 Social Authentication Data

| Provider | Data Received | Storage |
|---|---|---|
| Google OAuth | Email, full name, Google user ID, profile picture URL | Email + name in user record; Google ID in social_accounts |
| Instagram OAuth | Instagram user ID, username (no email from Instagram) | Placeholder email generated; Instagram ID in social_accounts |

No social provider tokens (access tokens, refresh tokens) are stored in plaintext. All provider tokens are encrypted with Fernet before database storage.

### 3.3 Marketplace Integration Data

| Data Element | Purpose | Storage |
|---|---|---|
| Amazon SP-API credentials (seller ID, client ID, refresh token) | Automated settlement sync | Fernet-encrypted in DB |
| Flipkart OAuth tokens | Automated report sync | Fernet-encrypted in DB |
| Settlement reports (uploaded CSV/XLSX files) | Reconciliation and analytics | GCS bucket (encrypted at rest) |
| Settlement transactions | Financial analysis; GST | PostgreSQL (Cloud SQL) |
| Payout events | Cash flow tracking | PostgreSQL (Cloud SQL) |

### 3.4 Usage and Technical Data

| Data Element | Purpose | Retention |
|---|---|---|
| IP address (login and API requests) | Security; fraud detection | 90 days (auth logs), 12 months (access logs) |
| User agent string | Security; debugging | 90 days |
| API request logs | Debugging; performance | 12 months |
| Error logs | Debugging | 6 months |
| Audit logs (financial operations) | Compliance; accountability | 3 years |

### 3.5 Data We Do Not Collect

ClearSettle does not collect:
- Payment card information (no card processing on the platform)
- Biometric data beyond what the user's device provides for local biometric authentication
- Location data beyond IP-based country for security purposes
- Communication content (emails, messages) between sellers and their customers
- Customer (end-buyer) personal data — ClearSettle processes seller-side financial data only

---

## 4. Legal Basis for Processing

| Processing Activity | Legal Basis |
|---|---|
| Account registration and authentication | Contract performance |
| Settlement ingestion and reconciliation | Contract performance |
| GST report generation | Legal obligation (GST Act, 2017) |
| Security audit logging | Legitimate interest (platform security) |
| Fraud detection | Legitimate interest (platform security) |
| Amazon / Flipkart data sync | Contract performance + user consent (OAuth) |
| Email notifications (transactional) | Contract performance |
| Email notifications (marketing) | Consent (opt-in only) |

---

## 5. How We Use Data

ClearSettle uses collected data exclusively for:

1. **Service delivery:** Processing settlement reports, generating reconciliation results, producing financial dashboards
2. **Authentication and security:** Verifying user identity; detecting unauthorized access; enforcing RBAC
3. **Compliance and audit:** Maintaining audit trails required by the Companies Act 2013 and GST Act 2017
4. **Support and debugging:** Investigating reported issues using logs and error records
5. **Platform improvement:** Aggregated, anonymized usage analytics (no individual profiling)

ClearSettle does not:
- Sell seller financial data to any third party
- Use seller financial data to train machine learning models without explicit consent
- Share seller data with other sellers on the platform
- Use seller data for advertising targeting

---

## 6. Data Sharing and Third-Party Disclosure

### 6.1 Third-Party Processors

ClearSettle engages the following processors who may handle personal or financial data on ClearSettle's behalf:

| Processor | Purpose | Data Shared | Location |
|---|---|---|---|
| Google Cloud Platform | Infrastructure (hosting, storage, database) | All platform data at rest and in transit | India (asia-south1) |
| Google (Gmail / Workspace) | Email delivery for notifications | Email address, notification content | Global |
| Amazon (SP-API) | Settlement data retrieval | Amazon seller credentials | Global |
| Flipkart | Settlement data retrieval | Flipkart OAuth tokens | India |
| Meta (Instagram) | Social authentication | Instagram OAuth flow | Global |
| Anthropic (Claude API) | AI-powered reconciliation insights (if enabled) | Anonymized financial summaries | Global |

All processors are engaged under data processing agreements that require them to handle ClearSettle data in accordance with applicable law.

### 6.2 Legal Disclosures

ClearSettle may disclose data without user consent when required by:
- A valid court order or legal process under Indian law
- A regulatory authority with jurisdiction over ClearSettle's operations
- An emergency involving risk to life

ClearSettle will, where legally permitted, notify the affected user of such a request before disclosure.

### 6.3 Business Transfers

In the event of a merger, acquisition, or asset sale, seller data may be transferred to the successor entity. Sellers will be notified in advance, and the successor entity will be bound by this policy or an equivalent.

---

## 7. Data Security

ClearSettle implements the following controls to protect personal and financial data:

- **Encryption in transit:** TLS 1.2+ for all API and web traffic
- **Encryption at rest:** Cloud SQL encryption; GCS server-side encryption; Fernet encryption for marketplace credentials
- **Access control:** RBAC with least-privilege; MFA required for privileged access
- **Secrets management:** All credentials stored in GCP Secret Manager; never in code or environment files
- **Audit logging:** All financial data access logged with user ID, timestamp, and operation
- **Vulnerability management:** Automated dependency scanning; quarterly penetration testing

For the full technical security specification, see the Security Policy (CLS-SEC-POL-001).

---

## 8. Data Retention

Data retention periods are defined in the Data Retention Policy (CLS-DRP-POL-013). Key periods:

- **Financial records:** 8 years (Companies Act, 2013)
- **User account PII:** 3 years post-account closure, then anonymized
- **Marketplace credentials:** 30 days post-disconnection
- **Security logs:** 3 years
- **Uploaded files:** 8 years

---

## 9. Data Subject Rights

Data subjects have the following rights regarding their personal data:

| Right | How to Exercise | Response Time |
|---|---|---|
| **Access:** Receive a copy of your personal data | Email privacy@clearsettle.app | 30 days |
| **Correction:** Correct inaccurate personal data | Email privacy@clearsettle.app or in-app settings | 30 days |
| **Erasure:** Delete personal data where no legal retention applies | Email privacy@clearsettle.app | 30 days |
| **Portability:** Receive data in a machine-readable format | Email privacy@clearsettle.app | 30 days |
| **Objection:** Object to processing based on legitimate interest | Email privacy@clearsettle.app | 30 days |
| **Withdraw consent:** Withdraw marketing email consent | Unsubscribe link in any email | Immediate |

**Limitations:** Financial records cannot be deleted before the statutory retention period. The right to erasure does not override ClearSettle's legal obligation to retain financial records for 8 years.

---

## 10. Cookies and Tracking

ClearSettle's web application uses:
- **Session cookies:** Required for authentication; no consent required
- **Security cookies:** CSRF protection tokens; required for security
- **Analytics cookies:** Aggregated, anonymized usage analytics (opt-out available)

ClearSettle does not use third-party advertising or tracking cookies.

---

## 11. Children's Data

The ClearSettle platform is intended for business use only. ClearSettle does not knowingly collect personal data from individuals under 18 years of age. If ClearSettle becomes aware that a user is under 18, the account will be suspended pending verification.

---

## 12. Changes to This Policy

ClearSettle will notify sellers of material changes to this policy via email at least 30 days before changes take effect. Continued use of the platform after the effective date constitutes acceptance of the updated policy.

---

## 13. Contact

For privacy inquiries, data subject rights requests, or concerns about this policy:

- **Email:** privacy@clearsettle.app
- **Data Protection Officer:** CEO, ClearSettle
- **Response time:** 5 business days for inquiries; 30 days for formal data rights requests

---

*This policy is reviewed annually. Next review: June 2027. For the full technical and operational policy, see the Data Protection Policy (CLS-DPP-POL-002).*
