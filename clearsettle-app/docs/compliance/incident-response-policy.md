# Incident Response Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-SEC-IRP-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Chief Security Officer |
| **Classification** | Internal — Confidential |
| **Approved By** | CEO / CTO |

---

## 1. Purpose and Scope

### 1.1 Purpose

This Incident Response Policy establishes the procedures ClearSettle follows to detect, respond to, contain, eradicate, and recover from security incidents. It ensures that all security events are handled in a consistent, timely, and legally compliant manner that protects seller data, marketplace partner data, and the integrity of ClearSettle's financial reconciliation platform.

### 1.2 Scope

This policy applies to:

- All ClearSettle employees, contractors, and third-party vendors
- All systems, services, and infrastructure operated by ClearSettle
- All data processed through the ClearSettle platform including Amazon SP-API data, Flipkart seller data, and all marketplace settlement data
- All cloud infrastructure on Google Cloud Platform (GCP)
- All environments: production, staging, and development

### 1.3 Regulatory and Partner Requirements

ClearSettle operates as an Amazon Solution Provider and is subject to:

- Amazon Selling Partner API Developer Agreement
- Amazon Data Protection Policy
- Amazon Seller Data Standards
- Applicable Indian IT Act 2000 and DPDP Act 2023 obligations
- GDPR obligations where EU seller data is processed

---

## 2. Security Incident Definitions

### 2.1 What Constitutes a Security Incident

A security incident is any confirmed or suspected event that:

- Compromises the confidentiality, integrity, or availability of ClearSettle systems
- Involves unauthorized access to seller financial data or marketplace credentials
- Results in the disclosure of Amazon SP-API tokens, Flipkart OAuth tokens, or marketplace API credentials
- Involves a breach of marketplace partner data use restrictions
- Constitutes a violation of any applicable data protection law
- Disrupts the availability of the ClearSettle platform for more than 15 minutes

### 2.2 Categories of Security Incidents

**Category A — Data Breach:** Unauthorized access to or exfiltration of seller financial data, marketplace credentials, or personal information.

**Category B — System Compromise:** Unauthorized access to ClearSettle servers, databases, or cloud infrastructure.

**Category C — Credential Compromise:** Theft, exposure, or unauthorized use of authentication credentials including API tokens, OAuth tokens, service account keys, or database credentials.

**Category D — Malware and Ransomware:** Detection of malicious software on any ClearSettle system or endpoint.

**Category E — Denial of Service:** Any attack or event that degrades or disrupts ClearSettle platform availability.

**Category F — Insider Threat:** Unauthorized data access or exfiltration by an employee, contractor, or vendor.

**Category G — Third-Party Breach:** A breach at a vendor or cloud provider that affects ClearSettle data or operations.

**Category H — Marketplace Integration Incident:** Compromise of Amazon SP-API integration, Flipkart integration, or any marketplace connector that exposes seller credentials or financial data.

---

## 3. Incident Severity Levels

### Severity 1 — Critical

**Definition:** Active, ongoing compromise with confirmed data exfiltration, system takeover, or marketplace credential exposure affecting production systems.

**Criteria:**
- Confirmed unauthorized access to seller financial data affecting more than 100 sellers
- Exposure of Amazon SP-API refresh tokens or Flipkart OAuth tokens in production
- Ransomware or destructive malware active on production infrastructure
- Complete platform outage exceeding 1 hour during business hours
- Confirmed breach of Amazon Seller Data Protection Policy obligations
- Database credentials or encryption keys exposed publicly

**Response Time:** Immediate — Incident Commander must be engaged within 15 minutes of detection.

**Escalation:** CEO, CTO, Legal Counsel, and Amazon Seller Central Support notified within 1 hour.

**Amazon Reporting Obligation:** Amazon must be notified within 24 hours of confirmed Severity 1 incidents involving Amazon SP-API data. See Section 11.

---

### Severity 2 — High

**Definition:** Significant security event with potential for data exposure or system compromise that has been contained but requires urgent investigation.

**Criteria:**
- Suspected unauthorized access to seller financial data (unconfirmed)
- Anomalous activity on marketplace API credentials
- Successful phishing attack on ClearSettle employee with system access
- Vulnerability actively exploited in a non-production environment
- Unauthorized access to internal systems without confirmed data access
- Loss or theft of an employee device with access to production systems
- Partial platform outage exceeding 4 hours

**Response Time:** Incident Commander engaged within 1 hour.

**Escalation:** CTO, Engineering Lead, and Security Lead notified within 2 hours.

---

### Severity 3 — Medium

**Definition:** Security event with limited impact that requires investigation and remediation within 24 hours.

**Criteria:**
- Failed unauthorized access attempts (brute force, credential stuffing)
- Discovery of a critical or high severity vulnerability in ClearSettle code or dependencies
- Accidental internal data disclosure without external exposure
- Third-party vendor security incident with potential but unconfirmed impact on ClearSettle
- Violation of access control policies by an internal user
- Suspicious activity flagged by Cloud Logging or Security Command Center

**Response Time:** Security Lead engaged within 4 hours.

**Escalation:** CTO notified within 8 hours.

---

### Severity 4 — Low

**Definition:** Minor security event or policy violation that requires documentation and remediation but poses no immediate risk.

**Criteria:**
- Policy violations without security impact (e.g., weak password used on non-critical system)
- Informational security alerts from monitoring tools
- Low severity vulnerability discoveries in dependencies
- Incomplete audit log entries or monitoring gaps

**Response Time:** Assigned to security team within 24 hours.

**Escalation:** Engineering Lead notified at next daily standup or equivalent communication.

---

## 4. Incident Response Team

### 4.1 Core Incident Response Team (CIRT)

| Role | Responsibility | Primary Contact |
|---|---|---|
| **Incident Commander** | Overall incident coordination, decision authority, stakeholder communication | CTO |
| **Security Lead** | Technical investigation, containment actions, forensic analysis | Head of Engineering / Security Engineer |
| **Engineering Lead** | System isolation, infrastructure remediation, recovery | Backend Engineering Lead |
| **Legal Counsel** | Regulatory notification obligations, legal hold, customer notification | External Legal Counsel / Company Secretary |
| **Communications Lead** | Customer, partner, and public communications | CEO / Founding Team |
| **Marketplace Compliance Officer** | Amazon/Flipkart notification obligations, partner communications | Designated Compliance Officer |

### 4.2 Extended Incident Response Team

Activated for Severity 1 or Severity 2 incidents:

- **GCP Support** — Engage via GCP Support portal for infrastructure-related incidents
- **Database Administrator** — PostgreSQL and Cloud SQL recovery
- **Mobile Lead** — Flutter app response for client-side incidents
- **Frontend Lead** — React application response

### 4.3 Incident Commander Responsibilities

The Incident Commander:

1. Declares the incident severity level within 30 minutes of engagement
2. Activates the appropriate CIRT members based on severity
3. Establishes an incident communication channel (dedicated Slack channel or Google Meet)
4. Authorizes containment and remediation actions
5. Provides status updates to stakeholders every 2 hours for Severity 1, every 4 hours for Severity 2
6. Makes the determination on regulatory notification obligations in consultation with Legal Counsel
7. Authorizes the postmortem process upon incident closure
8. Signs off on the final incident report

---

## 5. Escalation Matrix

| Severity | Detection to Assignment | Assignment to IC | IC to CEO/Legal | Amazon Notification |
|---|---|---|---|---|
| **1 — Critical** | 5 minutes | 15 minutes | 1 hour | 24 hours (if Amazon data involved) |
| **2 — High** | 15 minutes | 1 hour | 2 hours | If Amazon data confirmed exposed |
| **3 — Medium** | 1 hour | 4 hours | 8 hours | Only if Amazon data involved |
| **4 — Low** | 4 hours | 24 hours | Not required | Not required |

### 5.1 Notification Cascade

**Level 1 (Security Lead):** All incidents detected through monitoring, user reports, or automated alerts.

**Level 2 (Engineering Lead + CTO):** Severity 1, 2, or any incident with confirmed data exposure.

**Level 3 (CEO + Legal Counsel):** Severity 1, confirmed data breach, or any regulatory reporting obligation.

**Level 4 (Amazon / External Partners):** Severity 1 involving Amazon SP-API data, or any confirmed breach of Amazon Data Protection Policy.

**Level 5 (Affected Customers):** Confirmed data breach involving customer financial data per DPDP Act and applicable law.

---

## 6. Detection Procedures

### 6.1 Detection Sources

ClearSettle maintains the following detection mechanisms:

**Automated Detection:**
- Google Cloud Security Command Center — continuous threat detection
- Cloud Logging alerts for anomalous API access patterns
- Cloud Armor WAF alerts for injection and DDoS attempts
- Uptime monitoring with PagerDuty or equivalent alerting
- Failed authentication monitoring (>5 failures per minute on any endpoint)
- Amazon SP-API rate limit breach detection
- Anomalous database query volume detection via pg_stat_activity monitoring
- Dependency vulnerability scanning via Dependabot or Snyk

**Manual Detection:**
- Employee reports via security@clearsettle.app
- Customer reports of unexpected account activity
- Marketplace partner security notifications
- Bug bounty program disclosures (when active)
- Routine security code review findings

### 6.2 Initial Triage Procedure

Upon detection of a potential security event:

1. **Log the event** in the incident tracking system (Linear, Jira, or equivalent) with timestamp, source, and initial description
2. **Classify** as security incident or false positive within 30 minutes
3. **Assign preliminary severity** based on Section 3 criteria
4. **Notify Security Lead** immediately for any classification other than confirmed false positive
5. **Do not** attempt to remediate before the Security Lead has reviewed — premature action can destroy forensic evidence

---

## 7. Investigation Procedures

### 7.1 Initial Investigation

Within 2 hours of incident declaration (Severity 1-2) or 8 hours (Severity 3-4):

1. Identify affected systems, data stores, and user accounts
2. Determine the initial attack vector or failure mode
3. Establish the timeline of the incident using Cloud Logging, application logs, and database audit logs
4. Identify all affected seller accounts and marketplace data
5. Determine whether any Amazon SP-API tokens or Flipkart credentials were accessible during the incident window
6. Assess whether data was accessed, modified, or exfiltrated

### 7.2 Evidence Collection

See Section 9 for full evidence collection procedures.

### 7.3 Investigation Tools

- **Google Cloud Logging** — primary log source for GCP infrastructure
- **PostgreSQL audit logs** — `pg_audit` extension logs for database access
- **Nginx access logs** — HTTP request logs for API access investigation
- **Application structured logs** — ClearSettle application logs with correlation IDs
- **GCP VPC Flow Logs** — network traffic analysis
- **Cloud Armor request logs** — WAF and DDoS protection logs

---

## 8. Containment Procedures

### 8.1 Immediate Containment (within 1 hour for Severity 1)

Authorized by Incident Commander:

1. **Revoke compromised credentials** — Amazon SP-API refresh tokens, Flipkart OAuth tokens, database credentials, GCP service account keys
2. **Block suspicious IP addresses** via Cloud Armor rules
3. **Isolate affected GCP instances** by modifying firewall rules to block inbound/outbound traffic
4. **Disable affected user accounts** in the ClearSettle authentication system
5. **Enable maintenance mode** on the ClearSettle platform if necessary to prevent further access
6. **Snapshot affected Cloud SQL instances** before any remediation to preserve forensic state
7. **Notify marketplace partners** (Amazon, Flipkart) of the potential credential compromise to initiate token invalidation on their end

### 8.2 Short-Term Containment (within 24 hours)

1. Deploy patches or configuration changes to eliminate the vulnerability
2. Rotate all potentially compromised credentials and API keys
3. Enable enhanced logging on affected systems
4. Implement additional monitoring rules targeting the attack pattern
5. Validate the integrity of seller financial data in the affected period

### 8.3 Long-Term Containment

1. Architecture review to eliminate the root vulnerability class
2. Update security controls to prevent recurrence
3. Enhanced monitoring deployment
4. Third-party penetration testing of affected components

---

## 9. Evidence Collection Procedures

### 9.1 Evidence Collection Principles

All evidence must be collected in a manner that:
- Preserves the original state of affected systems
- Maintains a documented chain of custody
- Is sufficient for regulatory reporting and potential legal proceedings
- Does not alert the attacker if the incident involves an active threat actor

### 9.2 Evidence Sources and Collection Steps

**Cloud Infrastructure Evidence:**
1. Export Cloud Logging log entries to Google Cloud Storage with immutable retention policy before any remediation
2. Create disk snapshots of affected GCP compute instances
3. Export VPC Flow Logs for the incident window
4. Preserve Cloud Armor request logs

**Database Evidence:**
1. Export `pg_audit` log entries for the incident window
2. Query `social_accounts`, `platform_connections`, `marketplace_credentials`, and `ingestion_ledger` for access during the incident window
3. Check `marketplace_audit_logs` table for all credential and connection events

**Application Evidence:**
1. Export structured application logs with correlation IDs from the incident window
2. Collect authentication logs from the JWT issuance and refresh token tables
3. Export API rate limiting logs

**Chain of Custody:**
All evidence must be documented with:
- Collector name and role
- Collection timestamp (UTC)
- Storage location and access controls
- Hash verification (SHA-256) of exported files
- Legal hold notice if applicable

---

## 10. Recovery Procedures

### 10.1 Recovery Authorization

Recovery actions for Severity 1 require Incident Commander authorization. For Severity 2-4, the Engineering Lead may authorize recovery after Security Lead confirms containment.

### 10.2 Recovery Steps

1. **Verify containment** — confirm the attack vector has been eliminated before recovery
2. **Restore from clean backups** if system integrity is in question (see Disaster Recovery Policy)
3. **Rotate all credentials** associated with affected systems — do not reuse any credentials from the affected period
4. **Re-authorize marketplace integrations** — issue new Amazon SP-API authorization requests to affected sellers, re-issue Flipkart OAuth flows
5. **Validate data integrity** — verify that seller financial data in the `ingestion_ledger`, `settlements`, and `payout_events` tables has not been modified
6. **Restore platform access** in phases, monitoring for anomalies at each stage
7. **Notify affected sellers** per Section 11 notification obligations

---

## 11. Notification Procedures

### 11.1 Amazon SP-API Incident Notification

**Trigger:** Any confirmed Severity 1 incident involving Amazon SP-API data, refresh tokens, or seller authorization data.

**Deadline:** Amazon must be notified within **24 hours** of detection of any security incident involving Amazon Selling Partner data.

**Notification Process:**
1. Incident Commander confirms Amazon data was involved
2. Legal Counsel and Marketplace Compliance Officer draft notification
3. Notification sent to Amazon via Seller Central support case or Partner Network support
4. Notification must include:
   - Date and time of incident discovery
   - Nature of the incident
   - Amazon data types potentially affected
   - Number of affected sellers
   - Immediate actions taken
   - Ongoing investigation status
   - Contact details for ClearSettle security team

**Amazon Data Types Subject to Mandatory Reporting:**
- Seller Personally Identifiable Information (PII)
- Financial settlement data accessed via SP-API
- Marketplace credentials or authorization tokens
- Any data obtained under the Selling Partner API Data Protection Policy

### 11.2 Customer (Seller) Notification

**Trigger:** Confirmed exposure of a seller's financial data or account credentials.

**Deadline:** Within 72 hours of confirmed breach under applicable data protection obligations.

**Notification Contents:**
- Nature of the incident and data affected
- Timeframe of potential exposure
- Actions taken by ClearSettle
- Actions the seller should take (revoke tokens, change passwords)
- Contact for further information

### 11.3 Regulatory Notification

Under India's DPDP Act 2023, significant breaches of personal data must be reported to the Data Protection Board within the prescribed timeframe. Legal Counsel must assess each incident for regulatory notification obligations.

---

## 12. Root Cause Analysis

### 12.1 RCA Requirements

Root cause analysis is mandatory for all Severity 1 and Severity 2 incidents. RCA must be completed within:
- **Severity 1:** 5 business days of incident closure
- **Severity 2:** 10 business days of incident closure
- **Severity 3:** 15 business days at discretion of Security Lead

### 12.2 RCA Components

1. **Timeline** — complete chronological timeline from initial occurrence to closure
2. **Technical Root Cause** — the specific vulnerability, misconfiguration, or failure that enabled the incident
3. **Contributing Factors** — process, organizational, or tool failures that allowed the root cause to exist
4. **Impact Assessment** — confirmed data accessed, systems affected, and seller impact
5. **Corrective Actions** — specific, time-bound remediation items with assigned owners
6. **Preventive Measures** — architectural or process changes to prevent recurrence

---

## 13. Postmortem Requirements

### 13.1 Postmortem Standards

ClearSettle conducts blameless postmortems. The purpose of the postmortem is to improve systems and processes, not to assign fault.

### 13.2 Required Participants

- Incident Commander
- Engineering team members who responded to the incident
- Security Lead
- For Severity 1: CTO and CEO

### 13.3 Postmortem Document

The postmortem document must include all RCA components (Section 12) plus:

- **What went well** — detection, response, and communication actions that were effective
- **What needs improvement** — gaps identified in detection, response, or communication
- **Action items** — specific, assigned, time-bound items to address identified gaps
- **Metrics** — MTTD (Mean Time to Detect), MTTR (Mean Time to Respond), MTTC (Mean Time to Contain)

### 13.4 Postmortem Distribution

- Internal: All engineering and security team members
- For Severity 1 incidents involving Amazon data: Summary provided to Amazon if requested
- Not shared with customers unless legally required or strategically appropriate

---

## 14. Security Review Cadence

ClearSettle conducts mandatory security reviews every 6 months covering:

1. Review of all security incidents from the previous period
2. Update to threat model for ClearSettle platform
3. Review of all marketplace integration security controls
4. Penetration testing or vulnerability assessment (annually, with interim review every 6 months)
5. Review and update of all compliance documentation
6. Validation that Amazon SP-API and Flipkart security controls remain current with partner requirements

**Security review schedule:** June and December of each calendar year.

---

## 15. Incident Log and Records

All security incidents must be documented in ClearSettle's incident tracking system with:

- Incident ID
- Detection timestamp (UTC)
- Severity level (1-4)
- Category (A-H per Section 2.2)
- Affected systems and data
- Incident Commander and responders
- Timeline of key actions
- Resolution timestamp
- Final RCA reference

Incident records must be retained for a minimum of **3 years**.

---

*This policy is reviewed every 6 months. Next review: December 2026. Questions: security@clearsettle.app*
