# Data Retention Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-DRP-POL-013 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 12 months |
| **Next Review** | 2027-06-05 |
| **Owner** | CEO / Data Protection Officer |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Data Retention Policy defines how long ClearSettle retains different categories of data, the legal basis for each retention period, and the secure disposal procedures applied when data reaches the end of its retention life.

This policy applies to all data collected, processed, or stored by ClearSettle including seller financial data, marketplace integration data, user account data, system logs, and backup data.

---

## 2. Legal and Regulatory Basis

ClearSettle's retention periods are informed by the following frameworks:

| Framework | Applicability |
|---|---|
| **Income Tax Act, 1961** | Financial records: 6 years from end of assessment year |
| **GST Act, 2017** | GST-related records: 6 years from the date of filing the annual return |
| **Companies Act, 2013** | Books of accounts: 8 years from the end of financial year |
| **Information Technology Act, 2000** | Electronic records: as prescribed by applicable rules |
| **Amazon SP-API Data Protection Policy** | Selling Partner data: retained only as long as necessary for the stated purpose |
| **Meta / Instagram Platform Terms** | User data from Instagram OAuth: retained per Meta's data policy and ClearSettle's stated purpose |

---

## 3. Data Retention Schedule

### 3.1 User Account Data

| Data Category | Retention Period | Basis |
|---|---|---|
| User account (name, email, company) | Duration of account + 3 years post-closure | Legal: limitation period for disputes |
| Hashed passwords | Duration of account + 30 days post-closure | Operational: account recovery window |
| Social auth records (google_id, instagram_id) | Duration of linked account | Operational |
| Session tokens (refresh tokens) | 30 days or until revocation | Security: token lifecycle |
| Failed login attempts (IP, timestamp) | 90 days | Security: fraud detection |

### 3.2 Financial and Reconciliation Data

| Data Category | Retention Period | Basis |
|---|---|---|
| Settlement records (`settlements` table) | 8 years from settlement date | Companies Act, 2013 |
| Settlement transactions | 8 years from transaction date | Companies Act, 2013 + GST Act |
| Payout events | 8 years from payout date | Companies Act, 2013 |
| Reconciliation results (`reconciliation_results`) | 8 years | Companies Act, 2013 |
| Discrepancy events | 8 years | Audit trail requirement |
| GST summary data | 8 years from filing date | GST Act, 2017 |
| Ingestion ledger (`ingestion_ledger`) | 8 years from ingestion date | Companies Act, 2013 |

### 3.3 Uploaded Files

| Data Category | Retention Period | Basis |
|---|---|---|
| Uploaded settlement reports (GCS) | 8 years from upload date | Companies Act, 2013 |
| Processed files marked as deleted by user | 90 days (soft delete), then purged | Operational: recovery window |
| Failed / corrupted uploads | 30 days | Operational: reprocessing window |

### 3.4 Marketplace Credentials and API Data

| Data Category | Retention Period | Basis |
|---|---|---|
| Amazon SP-API credentials (encrypted) | Duration of connection + 30 days post-revocation | Amazon Data Protection Policy |
| Amazon SP-API access logs | 3 years from access date | Amazon Data Protection Policy |
| Flipkart OAuth tokens (encrypted) | Duration of connection + 30 days | Operational |
| Marketplace audit logs | 3 years | Amazon compliance requirement |

### 3.5 System and Security Logs

| Data Category | Retention Period | Basis |
|---|---|---|
| Application logs (Cloud Logging) | 12 months | Operational: debugging and incident response |
| Security audit logs (immutable export) | 3 years | Security policy requirement |
| Authentication event logs | 3 years | Security: fraud investigation |
| Admin action logs | 3 years | Accountability |
| Error logs | 6 months | Operational |

### 3.6 Backup Data

| Data Category | Retention Period | Notes |
|---|---|---|
| Daily Cloud SQL automated backups | 7 days | Managed by Cloud SQL |
| Monthly full database exports | 12 months | Stored in GCS |
| Pre-deployment manual backups | 30 days | Stored in GCS |
| Point-in-time recovery (WAL) | 7 days | Managed by Cloud SQL |

---

## 4. Data Deletion and Disposal

### 4.1 Account Closure

When a seller closes their ClearSettle account:

1. **Immediate (Day 0):** Account deactivated; login disabled; active sessions revoked
2. **Day 30:** Social auth tokens revoked; marketplace credentials deleted from database
3. **Year 3 post-closure:** User PII (name, email, phone) anonymized or deleted from account records
4. **Year 8 post-closure:** Financial records purged or anonymized in accordance with legal minimum retention

Note: Financial records (settlements, reconciliation data) are retained for the full 8-year statutory period even after account closure. PII linked to these records is replaced with an anonymized seller reference ID at Year 3.

### 4.2 Data Purge Process

Data purge is handled by the data cleanup service (scheduled via Cloud Scheduler):

1. Records past their retention date are identified by the cleanup job
2. For financial records: the record is anonymized in place (PII fields set to null or pseudonymized ID)
3. For non-financial records: the record is hard-deleted from the database
4. GCS objects past retention are deleted using Object Lifecycle Management rules
5. Purge actions are logged to the security audit log with record counts and table names

### 4.3 Secure Disposal of Physical Media

ClearSettle operates on cloud infrastructure. Physical media disposal applies only to:
- Developer laptops and workstations decommissioned by staff
- On-premises backups (if any)

**Procedure:** Physical storage media is securely wiped using NIST SP 800-88 compliant methods (cryptographic erasure for SSDs; DoD 5220.22-M for HDDs) before disposal or transfer. Certificates of destruction are retained for 3 years.

---

## 5. Data Subject Rights and Retention

Under applicable data protection law, data subjects may request:

- **Right to access:** ClearSettle provides a data export within 30 days
- **Right to erasure:** PII is deleted where no statutory retention requirement applies; a written response explains any data that must be retained and the legal basis
- **Right to correction:** Incorrect PII is corrected within 30 days; financial records cannot be altered retrospectively (audit trail integrity)

Data subject rights requests are tracked in the DPO's request log and responded to within 30 days.

---

## 6. Exceptions

Retention periods may be extended beyond the schedule above if:
- Legal hold is placed on data due to ongoing litigation or regulatory investigation
- Amazon or Flipkart data retention requirements impose a longer period than specified here

Exceptions are documented in `docs/compliance/exceptions-register.md` with the legal basis for the extension.

---

## 7. Responsibility

| Role | Responsibility |
|---|---|
| **CEO / DPO** | Policy ownership; annual review |
| **Engineering Lead** | Technical implementation of retention and purge jobs |
| **Security Lead** | Audit log retention; secure disposal verification |
| **Customer Success** | Handling data subject rights requests |

---

*This policy is reviewed annually. Next review: June 2027. Questions: privacy@clearsettle.app*
