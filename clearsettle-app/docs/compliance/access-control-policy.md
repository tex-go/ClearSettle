# Access Control Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-SEC-ACP-001 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | Chief Security Officer / CTO |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Access Control Policy defines how access to ClearSettle systems, data, and infrastructure is granted, managed, reviewed, and revoked. It applies to all employees, contractors, service accounts, and automated systems.

---

## 2. Role Definitions

### 2.1 Platform Roles

**Super Admin (`superadmin`)**

- Full access to all platform features, all seller accounts, and all administrative functions
- Can create, modify, and delete any data on the platform
- Can manage all user roles and permissions
- Has access to system configuration, audit logs, and security settings
- Granted only to founding team members and designated engineering leads
- Maximum of 3 active `superadmin` accounts at any time
- Subject to enhanced logging and quarterly access review

---

**Organization Admin (`company_admin`)**

- Full access to their company's data including all financial reports, reconciliation results, analytics, and platform connections
- Can invite team members and assign roles within their organization
- Can connect and disconnect marketplace integrations
- Can export financial data
- Cannot access other companies' data
- Cannot access platform-level administration

---

**Finance Manager (`finance_manager`)**

- Read and write access to financial settlement data, payout events, reconciliation results, and analytics
- Can upload reports and trigger marketplace syncs
- Cannot manage user accounts or company settings
- Cannot manage marketplace connections (OAuth authorization)
- Cannot export raw data (can view summaries)

---

**Accountant (`accountant`)**

- Read and write access to reconciliation workflows and dispute management
- Can upload and view settlement reports
- Cannot manage users, settings, or marketplace connections
- Cannot delete financial records

---

**Reconciliation Analyst (`reconciliation_analyst`)**

- Read access to all reconciliation data, discrepancy events, and settlement reports
- Can run reconciliation analysis but cannot modify existing records
- Cannot manage users, settings, or marketplace connections

---

**GST Consultant (`gst_consultant`)**

- Read access to GST and TCS/TDS tax data
- Can view tax ledger entries and monthly tax summaries
- Cannot access raw settlement details or manage any settings

---

**Branch Manager (`branch_manager`)**

- Access limited to the assigned branch's financial data
- Cannot view data from other branches within the same company
- Cannot manage company-level settings or marketplace connections

---

**Auditor (`auditor`)**

- Read-only access to all financial data within the company
- Can view audit logs, settlement reports, reconciliation results, and discrepancy events
- No write access to any data
- Suitable for external auditors with temporary access

---

**CA Admin (`ca_admin`)**

- Platform-level read access to multiple companies under a CA's management umbrella
- Can view but not modify financial data across assigned companies
- Used for Chartered Accountant advisory access

---

**Viewer (`viewer`)**

- Read-only access to summary dashboards and reports
- No access to detailed transaction records, raw settlement data, or reconciliation details
- No access to settings, users, or marketplace connections

---

### 2.2 Infrastructure Roles

| Role | Systems | Persons |
|---|---|---|
| **GCP Owner** | All GCP resources | CEO, CTO (maximum 2) |
| **GCP Editor** | All GCP services except IAM | Engineering Lead |
| **GCP Viewer** | Read-only GCP Console | All engineers |
| **Cloud SQL Admin** | Database administration | Database Administrator (1 person) |
| **Secret Manager Admin** | Secret creation and rotation | CTO, Security Lead |
| **Cloud Storage Admin** | File storage management | Engineering Lead |
| **Security Command Center Admin** | Security monitoring | Security Lead |

---

## 3. RBAC Matrix

| Permission | superadmin | company_admin | finance_manager | accountant | reconciliation_analyst | gst_consultant | branch_manager | auditor | ca_admin | viewer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| View dashboard | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| View settlement reports | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — |
| Upload reports | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — |
| View reconciliation | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — |
| Manage disputes | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — |
| View tax reports | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | ✓ | ✓ | — |
| Export data | ✓ | ✓ | — | — | — | — | — | ✓ | ✓ | — |
| Manage marketplace connections | ✓ | ✓ | — | — | — | — | — | — | — | — |
| Manage users | ✓ | ✓ | — | — | — | — | — | — | — | — |
| View audit logs | ✓ | ✓ | — | — | — | — | — | ✓ | — | — |
| Company settings | ✓ | ✓ | — | — | — | — | — | — | — | — |
| Platform admin | ✓ | — | — | — | — | — | — | — | — | — |
| Cross-company access | ✓ | — | — | — | — | — | — | — | ✓ | — |

---

## 4. Access Approval Process

### 4.1 New Employee Onboarding

**Day 1 — Minimum access provisioned by Engineering Lead:**
1. GitHub repository access (read for non-engineers, write for engineers)
2. GCP Console access with `roles/viewer` IAM role
3. ClearSettle internal documentation (Confluence/Notion)
4. Communication tools (Slack, email)

**Week 1 — Role-specific access (requires manager approval):**
1. Role-specific GCP IAM permissions
2. Development environment access
3. Staging environment access

**After probation (30-90 days) — Production access:**
1. Production access requires explicit documented approval from CTO
2. Production access is limited to the minimum required for the role
3. Direct production database access is not granted to individual engineers; only the application service account has runtime database access

### 4.2 Access Request Process

All non-standard access requests must:
1. Be submitted in writing (email or internal ticketing system) with business justification
2. Specify the resource, access level, and duration required
3. Be approved by the requesting employee's manager and the CTO (for Severity 1 data access) or Engineering Lead (for other access)
4. Be documented in the access control log

### 4.3 Elevated Access

Access to Level 1 data (marketplace credentials, database administration) follows a just-in-time model:
- Access is granted for a maximum of 4 hours
- Access request and approval must be documented before access is granted
- Actions taken during the elevated access window are logged
- Access is automatically revoked at the end of the approved window

---

## 5. Access Reviews

### 5.1 Quarterly Access Review

Conducted by the Engineering Lead and Security Lead every quarter:

1. Review all active GCP IAM bindings — remove stale or overly broad permissions
2. Review all `superadmin` accounts — confirm business need
3. Review all `company_admin` accounts — confirm the account holder is still employed by their company
4. Identify users with access that exceeds their current role requirements
5. Document review results in the access review log

### 5.2 Annual Full Access Review

Conducted by the CTO and Security Lead every year:

1. Full audit of all user accounts (internal and customer)
2. Full audit of all service accounts and their permissions
3. Full audit of all third-party integration permissions
4. Identify and remediate access creep (permissions accumulated over time beyond current requirements)

---

## 6. User Offboarding

### 6.1 Immediate Actions (within 1 hour of termination)

1. Disable ClearSettle platform account
2. Revoke all GCP IAM access
3. Remove from GitHub organization
4. Revoke any personal API keys or tokens
5. Disable communication tool access (Slack, email)
6. Notify the Security Lead to review any marketplace credentials the employee had access to

### 6.2 Actions within 24 hours

1. Transfer ownership of any resources owned by the departing employee
2. Review and revoke any shared credentials the employee may have had access to
3. Rotate any credentials the employee had access to that cannot be individually revoked
4. Document the offboarding actions in the access control log

### 6.3 Contractor and Vendor Offboarding

Contractors and vendors with system access follow the same offboarding process. Contract end dates are tracked; access is automatically reviewed 7 days before contract expiry.

---

## 7. Emergency Access Procedures

### 7.1 Break-Glass Access

For critical production incidents requiring database access outside normal procedures:

1. Incident Commander authorizes break-glass access in the incident management channel
2. Engineering Lead requests temporary elevated access from CTO
3. Access is granted for a maximum of 2 hours with specific documented scope
4. All commands and queries executed during break-glass access are logged
5. Break-glass access event is reviewed in the next security review

### 7.2 Account Recovery

For customer accounts where the account owner is unavailable:

1. Account recovery requests must be submitted with identity verification (government ID)
2. Multi-person approval required: Company owner verification by 2 ClearSettle team members
3. Account recovery actions are logged in the platform audit log
4. The account owner (original registrant) is notified by email of the recovery action

---

*This policy is reviewed every 6 months. Next review: December 2026. Questions: security@clearsettle.app*
