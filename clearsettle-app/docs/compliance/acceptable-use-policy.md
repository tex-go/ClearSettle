# Acceptable Use Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-AUP-POL-014 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 12 months |
| **Next Review** | 2027-06-05 |
| **Owner** | CEO / HR Lead |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Acceptable Use Policy (AUP) defines the permitted and prohibited uses of ClearSettle systems, data, and infrastructure. It ensures that all users — employees, contractors, and sellers — use ClearSettle resources in a manner that protects the security, integrity, and reputation of the platform and complies with applicable laws.

This policy applies to:
- All ClearSettle employees and contractors using ClearSettle systems
- All sellers and their staff using the ClearSettle platform
- All systems, devices, networks, and data under ClearSettle's management

---

## 2. General Acceptable Use Principles

All users of ClearSettle systems must:

1. Use ClearSettle systems only for legitimate business purposes
2. Protect their login credentials and never share account access
3. Report suspected security incidents, data breaches, or policy violations promptly to security@clearsettle.app
4. Comply with all applicable laws including the Information Technology Act 2000, GST Act 2017, and data protection regulations
5. Respect the confidentiality of financial data belonging to other sellers on the platform

---

## 3. ClearSettle Platform — Seller Acceptable Use

### 3.1 Permitted Uses

Sellers may use the ClearSettle platform to:
- Upload their own marketplace settlement reports (Flipkart, Amazon, Meesho)
- View and analyze their own reconciliation data and financial summaries
- Generate GST and tax reports for their own business
- Connect their own marketplace accounts via OAuth for automated sync
- Share access with their accountants, CA consultants, or finance staff within their organization
- Export their own financial data for use in accounting software

### 3.2 Prohibited Uses — Sellers

Sellers must not:
- Upload settlement reports or financial data belonging to another seller without explicit written authorization
- Attempt to access the accounts or data of other sellers
- Use automated scripts, bots, or scraping tools against the ClearSettle API without explicit written permission from ClearSettle
- Use the platform to process, launder, or conceal proceeds of any illegal activity
- Submit falsified, manipulated, or fraudulent settlement reports
- Reverse-engineer, decompile, or attempt to extract the ClearSettle application source code
- Resell, sublicense, or provide access to the ClearSettle platform to third parties
- Interfere with or attempt to disrupt platform availability, performance, or security
- Use the platform in any way that violates Amazon's Selling Partner API Terms, Flipkart's API Terms, or Meta's Platform Terms
- Share API credentials or OAuth tokens issued to them with unauthorized parties

---

## 4. ClearSettle Staff — Internal System Use

### 4.1 Permitted Uses — Employees and Contractors

Staff may use ClearSettle internal systems to:
- Perform their defined job functions as assigned by their manager
- Access production systems during approved maintenance windows or for authorized incident response
- Use company-provided development and test environments for feature development and debugging
- Access seller data strictly as required to deliver support, resolve incidents, or fulfill legal requests — with all access logged

### 4.2 Prohibited Uses — Employees and Contractors

Staff must not:
- Access seller financial data for any purpose outside of their documented job function
- Share production credentials, SSH keys, or GCP service account keys with unauthorized personnel
- Install unauthorized software on ClearSettle servers, VMs, or infrastructure
- Use ClearSettle infrastructure for personal projects, cryptocurrency mining, or non-business purposes
- Copy or export seller data to personal devices, personal cloud storage, or unauthorized systems
- Disable or bypass security controls including MFA, audit logging, or pre-commit hooks without explicit approval
- Access or modify production databases directly except during approved, documented maintenance windows
- Use privileged access (superadmin, GCP Owner role) for routine tasks that can be accomplished with least-privilege access
- Commit secrets, credentials, or PII to Git repositories
- Share or publicly disclose internal systems documentation, architecture diagrams, or compliance documents without authorization

### 4.3 Device Policy

Devices used to access ClearSettle production systems must:
- Have full-disk encryption enabled (BitLocker on Windows, FileVault on macOS)
- Have the operating system and security patches current (within 30 days of release)
- Have screen lock configured with a maximum 5-minute timeout
- Not be shared with family members, friends, or other unauthorized individuals
- Be reported immediately to the Security Lead if lost or stolen

---

## 5. Data Handling — All Users

### 5.1 Confidentiality

- All seller financial data is confidential and must not be shared outside of ClearSettle's system except as explicitly permitted by the seller or required by law
- Internal ClearSettle business data (roadmaps, financial projections, security configurations) is confidential and must not be disclosed externally
- This policy does not restrict legitimate whistleblowing or reporting to regulatory authorities

### 5.2 Data Minimization

- Access seller data only to the extent necessary for the task at hand
- Do not download or export larger datasets than required for the specific task
- Do not retain copies of seller data in personal communications tools, personal email, or messaging apps

---

## 6. Monitoring and Enforcement

### 6.1 Monitoring

ClearSettle reserves the right to:
- Log all access to production systems and seller financial data
- Monitor API usage for anomalous patterns or policy violations
- Review audit logs for compliance with this policy

Users of ClearSettle systems should have no expectation of privacy in their system activity logs. Monitoring is conducted for security and compliance purposes only and is handled in accordance with the Privacy and Data Handling Policy (CLS-PDP-POL-015).

### 6.2 Consequences of Violation

Policy violations are handled as follows:

| Severity | Example | Consequence |
|---|---|---|
| Minor | Sharing a work account temporarily for a legitimate task | Written warning; mandatory re-training |
| Moderate | Accessing seller data outside job scope; committing a non-secret config file | Formal disciplinary action; access review |
| Serious | Committing credentials to Git; unauthorized data export | Suspension pending investigation |
| Critical | Unauthorized disclosure of seller financial data; deliberate data tampering | Immediate termination; potential legal action |

For sellers, serious violations result in account suspension and may result in legal action and reporting to marketplace platforms.

### 6.3 Reporting Violations

Suspected policy violations must be reported to:
- **Security incidents:** security@clearsettle.app
- **HR / conduct concerns:** Directly to the CEO
- **Seller account issues:** support@clearsettle.app

Reports made in good faith are protected from retaliation.

---

## 7. Agreement

All ClearSettle employees and contractors must acknowledge this policy as part of their onboarding and annually thereafter. Sellers agree to this policy as a condition of their ClearSettle account.

---

*This policy is reviewed annually. Next review: June 2027. Questions: legal@clearsettle.app*
