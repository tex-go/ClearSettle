# Business Continuity Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-BCP-POL-010 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | CEO / CTO |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Business Continuity Policy (BCP) defines ClearSettle's approach to maintaining critical business functions during and after a disruption. It ensures that seller reconciliation services, financial data integrity, and marketplace integrations remain available or are restored within defined time objectives.

This policy applies to all ClearSettle business functions, technology systems, staff, and third-party providers.

---

## 2. Recovery Objectives

### 2.1 Recovery Time Objective (RTO)

| Service | RTO |
|---|---|
| ClearSettle API (FastAPI) | 1 hour |
| PostgreSQL / Cloud SQL | 2 hours |
| File ingestion pipeline | 4 hours |
| Amazon SP-API integration | 4 hours |
| Flipkart marketplace sync | 4 hours |
| Admin and reporting dashboards | 8 hours |
| Email delivery | 8 hours |
| Staging environment | 24 hours |

### 2.2 Recovery Point Objective (RPO)

| Data Store | RPO |
|---|---|
| PostgreSQL (Cloud SQL) | 1 hour (continuous WAL archiving) |
| GCS file storage (uploaded reports) | 4 hours |
| Application configuration (Secret Manager) | Near-zero (GCP-managed redundancy) |
| Audit logs (Cloud Logging export) | 1 hour |

---

## 3. Business Impact Analysis

### 3.1 Critical Business Functions

| Function | Impact of Loss | Priority |
|---|---|---|
| Seller reconciliation API | Direct revenue impact; sellers cannot reconcile | P1 |
| Financial report ingestion | Data loss risk; affects GST compliance | P1 |
| Amazon SP-API sync | Sellers lose real-time settlement data | P2 |
| Flipkart marketplace sync | Sellers lose Flipkart P&L visibility | P2 |
| User authentication | All users locked out of platform | P1 |
| Admin dashboard | Operational visibility lost | P3 |
| Email notifications | Reduced user experience | P3 |

### 3.2 Single Points of Failure

The following components are identified as single points of failure and have specific mitigation plans:

| Component | Mitigation |
|---|---|
| Cloud SQL primary instance | Cloud SQL High Availability (HA) replica; automated failover |
| GCP asia-south1 region outage | GCS multi-region bucket; runbooks for region cutover |
| Amazon SP-API availability | Local cached settlement data serves read requests for up to 24h |
| Flipkart OAuth token | Token stored encrypted in DB; valid for 24h without refresh |
| Secret Manager | GCP SLA 99.9%; secrets cached in-memory at startup for 1h |
| Single GCP project | Documented runbook for cross-project restore within 4h |

---

## 4. Continuity Strategies

### 4.1 Infrastructure Resilience

**Database:**
- Cloud SQL High Availability configuration with standby replica in the same region
- Automated daily backups with 7-day retention and point-in-time recovery (PITR) up to 7 days
- Continuous WAL archiving to GCS for sub-hour RPO
- Weekly backup restoration test (automated via Cloud Scheduler)

**Application Layer:**
- Docker Compose on GCP Compute Engine (current); Cloud Run target for auto-scaling
- Application stateless design allows restart on any Compute Engine instance
- All configuration loaded from Secret Manager at startup — no instance-specific state
- Nginx configuration stored in version control; redeployable in under 15 minutes

**File Storage:**
- GCS bucket configured with multi-region or dual-region replication
- File upload receipts (ingestion_ledger) stored in database — GCS loss allows re-upload without data loss
- 30-day object versioning enabled on GCS bucket

### 4.2 Marketplace Integration Continuity

**Amazon SP-API:**
- Settlement data cached in the local database upon each sync
- Read-only reconciliation continues from cached data during Amazon API outages
- Alert triggered if sync fails for more than 4 consecutive hours

**Flipkart:**
- Flipkart OAuth tokens valid for 24 hours; refresh attempted automatically
- Manual file upload pathway always available as fallback

### 4.3 Communication During Disruption

| Audience | Channel | Responsible |
|---|---|---|
| ClearSettle customers | In-app banner + status email | CEO / Customer Success |
| Internal team | Slack #incidents channel | CTO |
| Amazon / Flipkart (if relevant) | Account manager contact | CTO |
| Investors / Board (P1 extended) | Direct call | CEO |

---

## 5. Roles and Responsibilities

| Role | Responsibility |
|---|---|
| **Incident Commander (CEO)** | Overall BCP activation decision; external communications |
| **Technical Lead (CTO)** | Infrastructure recovery execution; team coordination |
| **Engineering Lead** | Application restore; data validation |
| **Security Lead** | Security assessment post-incident; access control review |
| **Customer Success** | Customer communication; SLA tracking |

---

## 6. BCP Activation

### 6.1 Activation Triggers

BCP is formally activated when:
- Any P1 service (API, database, auth) is unavailable for more than 30 minutes
- A security incident results in service suspension
- A third-party dependency (GCP region, Amazon SP-API) is unavailable for more than 2 hours
- Physical office access is unavailable for more than 1 business day

### 6.2 Activation Steps

1. Incident Commander declares BCP activation in Slack #incidents
2. Technical Lead assesses impacted systems within 15 minutes
3. Recovery runbook for the affected service is executed
4. Status page updated within 30 minutes of activation
5. Customer email sent within 1 hour of activation for P1 disruptions

---

## 7. Testing and Maintenance

| Activity | Frequency | Owner |
|---|---|---|
| BCP document review | Every 6 months | CTO |
| Database failover test | Quarterly | Engineering Lead |
| Full backup restore test | Quarterly | Engineering Lead |
| BCP tabletop exercise | Annually | CEO + CTO |
| Communication tree verification | Quarterly | CEO |

All test results are documented and stored in `docs/compliance/bcp-test-log.md`.

---

*This policy is reviewed every 6 months. Next review: December 2026. Questions: security@clearsettle.app*
