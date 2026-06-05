# Vendor Security Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-SEC-VSP-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Annually |
| **Next Review** | 2027-06-05 |
| **Owner** | Chief Security Officer / CTO |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Vendor Security Policy governs how ClearSettle evaluates, approves, and monitors third-party vendors and cloud service providers who have access to ClearSettle systems, infrastructure, or seller data. It ensures that vendor relationships do not introduce unacceptable security or compliance risk.

---

## 2. Vendor Risk Classification

### Tier 1 — Critical Vendors

Vendors with access to seller financial data, marketplace credentials, or ClearSettle production infrastructure.

| Vendor | Service | Data Access |
|---|---|---|
| Google Cloud Platform | Infrastructure, Cloud SQL, GCS, Secret Manager, Cloud Logging | All production data |
| GitHub (Microsoft) | Source code repository | Application source code |
| Anthropic | AI/ML API for report analysis | Processed settlement data (anonymized where feasible) |

### Tier 2 — Significant Vendors

Vendors providing services that support the ClearSettle platform but do not have direct access to production data.

| Vendor | Service | Data Access |
|---|---|---|
| Amazon (AWS/Seller Central) | SP-API marketplace integration | Seller-authorized API access |
| Meta (Instagram) | Social authentication | User profile data (name, email) |
| Google (OAuth) | Social authentication | User profile data (name, email) |
| SendGrid / SMTP provider | Transactional email | Seller email addresses |
| PagerDuty / Alert provider | Incident alerting | System health data only |

### Tier 3 — Standard Vendors

Vendors providing productivity tools and services with no access to seller data.

Examples: project management tools, documentation platforms, video conferencing, payment processors (if applicable for ClearSettle billing).

---

## 3. Vendor Review Process

### 3.1 Pre-Approval Review

Before engaging any Tier 1 or Tier 2 vendor, the following must be completed:

**Security Assessment:**
1. Review vendor's most recent SOC 2 Type II report or ISO 27001 certificate
2. Review vendor's data protection and privacy policies
3. Assess vendor's incident response capabilities and notification obligations
4. Evaluate vendor's encryption standards for data at rest and in transit
5. Review vendor's sub-processor relationships and any data residency commitments
6. Assess the vendor's financial stability and business continuity posture

**Contractual Requirements:**
1. Data Processing Agreement (DPA) required for any vendor processing personal data
2. Sub-processor obligations: vendor must disclose all sub-processors with access to ClearSettle data
3. Security incident notification: vendor must notify ClearSettle within 24 hours of any incident affecting ClearSettle data
4. Right to audit: ClearSettle must have the right to conduct or commission security audits of Tier 1 vendors annually

**Approval:**
- Tier 1 vendors require CTO approval
- Tier 2 vendors require Engineering Lead approval
- Tier 3 vendors require Manager approval

### 3.2 Annual Vendor Review

All Tier 1 and Tier 2 vendors are reviewed annually:

1. Confirm current SOC 2 / ISO 27001 certification is valid
2. Review any disclosed security incidents from the prior year
3. Assess changes to the vendor's data processing practices
4. Review vendor's sub-processor list for changes
5. Confirm contractual terms remain current and adequate

---

## 4. Google Cloud Platform

### 4.1 Service Overview

GCP is ClearSettle's primary cloud infrastructure provider. All production services run on GCP infrastructure in the `asia-south1` (Mumbai) region.

### 4.2 Security Controls

- **Encryption at rest:** All Cloud SQL, Cloud Storage, and Cloud Logging data is encrypted using AES-256 with Google-managed encryption keys by default. Customer-Managed Encryption Keys (CMEK) are evaluated for future implementation.
- **Encryption in transit:** All data in transit within GCP uses TLS 1.3.
- **IAM:** GCP IAM is used for all access control to GCP resources per the Access Control Policy.
- **VPC:** All ClearSettle infrastructure runs within a dedicated GCP VPC with private networking.
- **Compliance:** GCP holds SOC 1/2/3, ISO 27001, PCI DSS, and multiple other certifications. Certifications are available at cloud.google.com/security/compliance.

### 4.3 Data Residency

All ClearSettle production data is stored in the GCP `asia-south1` region (Mumbai, India) to comply with Indian data localization requirements and to minimize latency for Indian seller users.

### 4.4 GCP Shared Responsibility

ClearSettle understands the shared responsibility model: Google is responsible for the security of the cloud infrastructure; ClearSettle is responsible for the security of the applications, data, and configurations running on that infrastructure.

### 4.5 GCP Contractual Framework

ClearSettle operates under Google Cloud's standard Terms of Service and Data Processing Addendum (DPA). Google's DPA covers GDPR and applicable data protection obligations.

---

## 5. GitHub (Microsoft)

### 5.1 Service Overview

GitHub hosts the ClearSettle source code repository, CI/CD pipelines (GitHub Actions), and collaborative development workflows.

### 5.2 Data in GitHub

- Application source code
- Terraform infrastructure code (non-sensitive configuration)
- Documentation

**What must never be stored in GitHub:**
- Production secrets, API keys, or credentials
- Database connection strings
- SSL certificates or private keys
- Seller financial data or test data containing real PII

### 5.3 Security Controls

- All developers access GitHub with MFA enforced at the organization level
- All production repositories are private
- `main` and `production` branches are protected: require pull request review by at least one reviewer, require status checks to pass, prevent force-pushes
- Secret scanning is enabled on all repositories via GitHub Advanced Security or `detect-secrets` pre-commit hooks
- Dependabot security alerts are enabled and actioned per the vulnerability management SLA in the Security Policy

### 5.4 GitHub Actions Security

- GitHub Actions workflows do not have access to production GCP credentials
- Deployment to production requires manual approval by CTO or Engineering Lead after CI passes
- GitHub Actions secrets (staging deploy keys, test credentials) use GitHub Encrypted Secrets and are not exposed in logs

---

## 6. Anthropic

### 6.1 Service Overview

ClearSettle uses the Anthropic API (Claude models) for intelligent analysis of marketplace settlement reports, generating financial insights, and detecting reconciliation anomalies.

### 6.2 Data Shared with Anthropic

Settlement report data and parsed financial records may be sent to the Anthropic API for analysis. The following data handling commitments apply:

**Data Minimization:**
- PII (seller names, buyer information) is stripped from data sent to the Anthropic API where technically feasible
- Financial data is sent in structured format without personally identifying business information where possible
- Analysis requests include only the data necessary for the specific analytical task

**Anthropic Data Processing:**
- Data sent to Anthropic is processed according to Anthropic's usage policy and privacy policy
- ClearSettle uses the Anthropic API in API mode; data sent via the API is not used to train Anthropic's models per Anthropic's default policy
- ClearSettle reviews Anthropic's policy updates to ensure continued compliance

**Contractual Framework:**
- ClearSettle operates under Anthropic's standard API Terms of Service
- ClearSettle monitors for the availability of an Anthropic Data Processing Addendum for enterprise customers

**ANTHROPIC_API_KEY Security:**
- The Anthropic API key is stored in GCP Secret Manager
- The key is never hardcoded, committed to source control, or logged
- API key rotation follows the 90-day rotation schedule in the Security Policy

### 6.3 Conditional Use

ClearSettle treats Anthropic as a non-essential service. The intelligence pipeline is designed to be non-blocking:
- If the Anthropic API is unavailable, file ingestion and reconciliation complete successfully without AI analysis
- Sellers are not informed when AI analysis is unavailable; the platform degrades gracefully

---

## 7. Future Vendor Onboarding Requirements

Any new Tier 1 or Tier 2 vendor must meet all of the following before being approved for use with ClearSettle production data:

### 7.1 Security Certification

The vendor must hold at least one of:
- SOC 2 Type II report (issued within the past 12 months)
- ISO 27001 certificate (current)
- CSA STAR Level 2 certification

### 7.2 Data Protection

- The vendor must operate a documented incident response procedure with notification obligations
- The vendor must provide a Data Processing Addendum if processing personal data
- The vendor must have adequate data residency controls if Indian data localization is required

### 7.3 Security Controls

- Encryption at rest (AES-256 minimum) and encryption in transit (TLS 1.2 minimum)
- Access controls with least privilege and audit logging
- Regular third-party penetration testing (minimum annual)
- Vulnerability disclosure and patch management program

### 7.4 Business Continuity

- The vendor must have documented backup and recovery procedures
- RTO and RPO must be adequate for ClearSettle's operational requirements
- Vendor must not be the sole provider of a critical function without an identified alternative

---

## 8. Data Sharing Restrictions

ClearSettle applies the following restrictions to all vendor data sharing:

1. **Need to know:** Vendors receive only the data necessary to perform their contracted service
2. **No onward transfer:** Vendors may not share ClearSettle data with sub-processors not disclosed in the DPA without prior written approval
3. **Return or destruction:** Upon contract termination, vendors must return or destroy all ClearSettle data within 30 days
4. **No commercial use:** Vendors may not use ClearSettle data for their own commercial purposes, research, or product improvement without explicit written consent
5. **Seller data restrictions:** Amazon and Flipkart marketplace data is subject to the respective marketplace data use restrictions. No vendor receives marketplace data except for the specific analytical purpose for which it was authorized.

---

*This policy is reviewed annually. Next review: June 2027. Questions: security@clearsettle.app*
