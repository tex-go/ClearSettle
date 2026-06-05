# Disaster Recovery Policy

| Field | Value |
|---|---|
| **Document ID** | CLS-DR-POL-011 |
| **Version** | 1.0 |
| **Effective Date** | 2026-06-05 |
| **Review Cycle** | Every 6 months |
| **Next Review** | 2026-12-05 |
| **Owner** | CTO / Engineering Lead |
| **Classification** | Internal — Confidential |

---

## 1. Purpose and Scope

This Disaster Recovery Policy (DRP) defines the procedures to restore ClearSettle's technical infrastructure and services following a disruptive event. It covers all production systems: the FastAPI backend, Cloud SQL PostgreSQL database, GCS file storage, and related GCP infrastructure.

This policy supplements the Business Continuity Policy (CLS-BCP-POL-010) with specific technical runbooks and recovery procedures.

---

## 2. Disaster Scenarios and Severity Classification

| Scenario | Severity | RTO Target |
|---|---|---|
| Application process crash (single container) | Low | 5 minutes (auto-restart) |
| Full application server failure | Medium | 1 hour |
| Cloud SQL primary instance failure | High | 2 hours |
| Cloud SQL data corruption | Critical | 4 hours |
| GCS bucket loss | High | 4 hours (restore from versioning) |
| GCP asia-south1 region outage | Critical | 8 hours |
| Full GCP project compromise | Critical | 24 hours |
| Ransomware / data encryption | Critical | 24–48 hours |

---

## 3. Infrastructure Inventory

### 3.1 Production Components

| Component | GCP Service | Configuration |
|---|---|---|
| Application server | Compute Engine (e2-standard-2) | asia-south1-a |
| Database | Cloud SQL PostgreSQL 15 | HA with replica; asia-south1 |
| File storage | Cloud Storage | Regional bucket; asia-south1 |
| Secrets | Secret Manager | Global; auto-replicated |
| Networking | VPC, Cloud Armor, Nginx | asia-south1 |
| Monitoring | Cloud Logging, Cloud Monitoring | Global |

### 3.2 Application Components

| Component | Location | Recovery Method |
|---|---|---|
| FastAPI application | GitHub `main` branch | Pull and redeploy |
| Docker Compose config | GitHub + VM `/app/docker-compose.yml` | Pull from Git |
| Nginx config | GitHub + VM `/etc/nginx/` | Pull from Git |
| Alembic migrations | GitHub `alembic/versions/` | `alembic upgrade head` |
| GCP service account keys | Secret Manager | Re-download from IAM |

---

## 4. Recovery Runbooks

### 4.1 Application Server Failure

**Trigger:** Compute Engine instance unreachable; health checks failing for > 10 minutes.

**Steps:**
1. Verify instance state in GCP Console → Compute Engine → VM Instances
2. If instance stopped: Start the instance (`gcloud compute instances start clearsettle-prod --zone=asia-south1-a`)
3. If instance failed: Create a new instance from the production machine image
4. SSH into the instance: `gcloud compute ssh clearsettle-prod --zone=asia-south1-a`
5. Navigate to application directory: `cd /app`
6. Pull latest code: `git pull origin main`
7. Restart services: `docker compose up -d`
8. Verify health: `curl http://localhost:8000/health`
9. Verify Nginx: `nginx -t && systemctl reload nginx`
10. Run smoke tests: check `/auth/login`, `/ingestion/files`, `/dashboard/summary` endpoints
11. Restore monitoring alerts if silenced during recovery

**Expected completion time:** 30–60 minutes

### 4.2 Cloud SQL Primary Failure (Automatic Failover)

**Trigger:** Cloud SQL HA replica promoted automatically; application reconnects.

**Verification Steps:**
1. Check Cloud SQL console for failover event in Logs
2. Application should reconnect automatically (SQLAlchemy connection pool retry)
3. If application still reports DB errors: restart the application container (`docker compose restart api`)
4. Verify data integrity: run `python scripts/db_health_check.py` on the server
5. Document failover event in incident log

**Expected completion time:** 5–15 minutes (automatic); 30 minutes with manual verification

### 4.3 Cloud SQL Data Corruption or Accidental Deletion

**Trigger:** Data validation failures; missing records; application errors indicating corrupt data.

**Steps:**
1. Immediately stop write operations: set application to maintenance mode (`MAINTENANCE_MODE=true` env var)
2. Identify corruption scope: which tables, time range, number of records
3. Determine recovery point: last known good state from audit logs or ingestion_ledger timestamps
4. For point-in-time recovery:
   - GCP Console → Cloud SQL → Backups → Restore to point in time
   - Select timestamp before corruption event
   - Restore to a new Cloud SQL instance (do not overwrite production)
5. Validate restored instance data
6. Apply incremental changes from audit logs if needed
7. Cutover application connection string to restored instance
8. Resume write operations
9. Delete the corrupted instance after 7-day validation period

**Expected completion time:** 2–4 hours

### 4.4 GCS File Storage Loss

**Trigger:** GCS bucket unavailable or files missing.

**Steps:**
1. Check object versioning: most deleted objects are recoverable from version history
2. For versioned object recovery:
   - `gsutil cp gs://clearsettle-uploads/OBJECT_NAME#VERSION_ID gs://clearsettle-uploads/OBJECT_NAME`
3. For bucket-level loss (rare):
   - Create new bucket with same name and configuration
   - Restore from GCS cross-region replica if configured
   - Note: ingestion_ledger in the database lists all processed files; re-upload from seller if originals lost
4. Notify affected sellers if their uploaded reports cannot be recovered

**Expected completion time:** 1–4 hours depending on scope

### 4.5 GCP Region Outage (asia-south1)

**Trigger:** GCP status page indicates asia-south1 degradation; application completely unreachable.

**Steps:**
1. Monitor GCP status at status.cloud.google.com
2. If outage projected > 4 hours:
   - Provision new Compute Engine instance in alternate region (asia-south2 or us-central1)
   - Restore application from Git
   - Point to Cloud SQL replica (if cross-region replica exists) or restore from backup to new region
   - Update DNS to new instance IP
3. Communicate outage status to customers via email (can be sent from any network)
4. Once asia-south1 recovers, plan cutback to primary region

**Expected completion time:** 4–8 hours

### 4.6 Security Compromise / Ransomware

**Trigger:** Unauthorized access detected; data encrypted; credentials exposed.

**Immediate Actions (first 30 minutes):**
1. Isolate: shut down affected instances; revoke all service account keys
2. Preserve: snapshot all disks before any recovery actions (forensic evidence)
3. Rotate: all secrets in GCP Secret Manager immediately
4. Notify: Security Lead, CEO, Legal (if customer data affected)
5. Do not pay ransom; restore from clean backups only

**Recovery Steps:**
1. Provision new infrastructure in a clean GCP project
2. Restore database from last known-clean backup (prior to compromise)
3. Restore application from Git (verify commit hashes against signed releases)
4. Do not restore any VM disk images — treat all as compromised
5. Force logout all user sessions (rotate JWT signing secret)
6. Notify affected customers per Data Breach Notification requirements
7. Engage third-party forensics firm

**Expected completion time:** 24–48 hours

---

## 5. Backup Configuration

### 5.1 Database Backups

| Backup Type | Frequency | Retention | Storage |
|---|---|---|---|
| Cloud SQL automated backup | Daily at 02:00 UTC | 7 days | GCS (managed by Cloud SQL) |
| Cloud SQL transaction logs (PITR) | Continuous | 7 days | GCS (managed by Cloud SQL) |
| Manual pre-deployment backup | Before every migration | 30 days | GCS (manual export) |
| Monthly full export | 1st of each month | 12 months | GCS (pg_dump gzip) |

### 5.2 Application Backups

| Asset | Backup Method | Recovery Time |
|---|---|---|
| Application code | Git repository (GitHub) | < 15 minutes |
| Docker configurations | Git repository | < 15 minutes |
| Nginx configuration | Git repository | < 15 minutes |
| Alembic migrations | Git repository | < 30 minutes |
| GCP IAM configuration | Terraform / documented | 1–2 hours |

---

## 6. Post-Disaster Review

Within 5 business days of any disaster declaration, the Engineering Lead conducts a post-incident review covering:

1. Timeline of events from detection to full recovery
2. Root cause analysis
3. Data loss assessment (actual RPO achieved vs. target)
4. Recovery time assessment (actual RTO achieved vs. target)
5. Gaps in runbooks or tooling identified during recovery
6. Action items with owners and deadlines

The post-incident report is stored in `docs/incidents/` and reviewed by the CEO and CTO.

---

## 7. DR Testing Schedule

| Test Type | Frequency | Owner |
|---|---|---|
| Database backup restore verification | Monthly (automated) | Engineering |
| Manual PITR restore to test instance | Quarterly | Engineering Lead |
| Application redeploy from scratch | Quarterly | Engineering Lead |
| Full DR simulation (chaos day) | Annually | CTO |
| Runbook review and update | Every 6 months | Engineering Lead |

---

*This policy is reviewed every 6 months. Next review: December 2026. Questions: security@clearsettle.app*
