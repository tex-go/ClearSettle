# ClearSettle — Current Infrastructure & Deployment

> Snapshot: June 2026. For scaling reference only.

---

## GCP Project

| Field | Value |
|---|---|
| Project | `clearsettle-prod` |
| Region | `asia-south1` (Mumbai) |
| Zone | `asia-south1-a` |
| Domain | `clearsettle.in` |
| Alert email | `sudo.ranjith@gmail.com` |

---

## Compute

| Resource | Spec |
|---|---|
| VM name | `clearsettle-prod-vm` |
| Machine type | `e2-standard-2` (2 vCPU, 8 GB RAM) |
| Boot disk | 50 GB SSD |
| OS | Debian 12 (cloud-amd64) |
| Networking | Private subnet `10.10.0.0/24` in custom VPC |
| Public access | Via Nginx reverse proxy on ports 80/443 |

**Everything runs as Docker Compose on this single VM.**

---

## Services (docker-compose.prod.yml)

| Container | Image | Port | Role |
|---|---|---|---|
| `clearsettle-backend` | Built from `./backend` | 8000 (internal) | FastAPI app |
| `clearsettle-frontend` | Built from `./frontend` | 3000 (internal) | React web app |
| `clearsettle-postgres` | `postgres:15-alpine` | 5432 (internal) | PostgreSQL DB |
| `clearsettle-redis` | `redis:7.2-alpine` | 6379 (internal) | Sessions + rate limiting |
| `clearsettle-nginx` | `nginx:1.27-alpine` | 80, 443 (public) | Reverse proxy + SSL |
| `clearsettle-certbot` | `certbot/certbot` | — | Let's Encrypt auto-renewal |

---

## Database

| Field | Value |
|---|---|
| Engine | PostgreSQL 15 |
| Current setup | Docker container on VM (`clearsettle-postgres`) |
| Planned (Terraform) | Cloud SQL `db-g1-small`, 20 GB SSD, Private IP, REGIONAL HA |
| Backups (Terraform) | Daily at 03:00 UTC, 30-day retention, PITR enabled |
| Max connections | 100 |
| Slow query log | >1000ms |
| ORM | SQLAlchemy async (asyncpg driver) |
| Migrations | Alembic (38 versions as of June 2026) |

---

## File Storage

| Field | Value |
|---|---|
| Current setup | Local disk `/opt/clearsettle/uploads` mounted into container |
| GCS bucket (Terraform) | `clearsettle-prod-uploads` — STANDARD, `asia-south1` |
| Backups bucket | `clearsettle-prod-backups` — NEARLINE, 90-day retention |
| Versioning | Enabled on uploads bucket |
| App abstraction | `StorageService` (`local` or `gcs` via `STORAGE_BACKEND` env var) |

---

## Secrets Management

| Field | Value |
|---|---|
| Store | GCP Secret Manager |
| Secrets managed | DB password, JWT secret, Fernet key, SP-API creds, Google OAuth, SMTP |
| Access | VM service account with `secretmanager.secretAccessor` |

---

## Networking

| Layer | Detail |
|---|---|
| VPC | Custom VPC `clearsettle-prod-vpc` |
| App subnet | `10.10.0.0/24` |
| Public IPs | Nginx only (ports 80/443) |
| DB access | Private IP only (no public IP on Cloud SQL) |
| SSL | Let's Encrypt via Certbot, auto-renewed every 12h |
| TLS | 1.2 minimum, 1.3 preferred |
| Rate limiting | 60 req/min per IP (API), 5 req/min (auth endpoints) |

---

## IAM (Terraform)

| Service Account | Role |
|---|---|
| `clearsettle-prod-vm-sa` | VM runtime — Storage, Secret Manager, Logging |
| `clearsettle-prod-ci-sa` | GitHub Actions CI/CD — Artifact Registry push, SSH deploy |

---

## CI/CD

| Workflow | Trigger | What it does |
|---|---|---|
| `auto-version.yml` | Push to `main` | Bumps `VERSION`, `pubspec.yaml`, `package.json`, creates `vX.Y.Z` tag |
| `release.yml` | `vX.Y.Z` tag | Creates GitHub Release with changelog |
| `deploy.yml` | `vX.Y.Z` tag | SSH into VM → `git pull` → `docker compose up --build` |
| `distribute.yml` | `vX.Y.Z` tag | Flutter build APK → Firebase App Distribution |
| `ci.yml` | Push to `main` | Pytest + coverage |

**Deploy script** (`deploy.sh`):
- Pulls `main`, starts infra containers once (postgres/redis/nginx/certbot)
- Rebuilds only `backend` + `frontend` in parallel
- Health-checks backend before finishing
- Typical deploy time: 60–90 seconds

---

## Mobile App

| Field | Value |
|---|---|
| Framework | Flutter 3.x (Dart) |
| Package | `com.clearsettle.mobile` |
| Auth | Email/password + Google OAuth + Instagram OAuth |
| Distribution | Firebase App Distribution (`clearsettle-mobile` project) |
| Signing | `clearsettle-release.jks` (release keystore) |
| Crash reporting | Firebase Crashlytics |
| Push | Firebase Cloud Messaging |

---

## Backend Tech Stack

| Layer | Tech |
|---|---|
| Framework | FastAPI (Python 3.11) |
| ORM | SQLAlchemy 2.x async |
| DB driver | asyncpg |
| Auth | JWT (HS256) + bcrypt + Fernet encryption |
| File processing | Custom 14-agent ETL pipeline |
| Storage | Local disk or GCS (switchable) |
| Logging | Structured JSON → Cloud Logging |

---

## Current Bottlenecks (single-VM monolith)

| Area | Current | Bottleneck |
|---|---|---|
| Database | Docker container, shared VM disk | No HA, no read replicas, shared I/O |
| File storage | Local `/opt/clearsettle/uploads` | Not scalable across VMs |
| Background jobs | Inline in FastAPI request thread | Blocks API response |
| Compute | 1 VM, e2-standard-2 | No horizontal scaling |
| Redis | Docker container, no persistence config | Restarted = sessions lost |

---

## What Terraform Has Ready (not yet applied to prod)

- Cloud SQL PostgreSQL 15 with REGIONAL HA + PITR
- VPC with Private Service Connection for Cloud SQL
- GCS buckets (`uploads` + `backups`) with lifecycle rules
- Artifact Registry for Docker images
- IAM service accounts for VM + CI
- Secret Manager shells

> Terraform state: `infra/terraform/environments/prod/` — `project_id` not filled in yet.
