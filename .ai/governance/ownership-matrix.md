# Ownership Matrix
**Version:** 1.0 | **Owner:** `architect-agent`
**Last Updated:** 2026-06-01

Every file, directory, and concern in ClearSettle has exactly one **Primary Owner** and zero or more **Collaborators**. Changes to a file require the Primary Owner's involvement. Multiple owners = no owner.

---

## Backend Ownership

| Path | Primary Owner | Collaborators | Notes |
|---|---|---|---|
| `backend/app/routers/` | `backend-agent` | `architect-agent` (review) | Route handlers only |
| `backend/app/services/` | `backend-agent` | `reconciliation-agent` (recon services) | Business logic |
| `backend/app/repositories/` | `backend-agent` | `database-agent` (query review) | DB access layer |
| `backend/app/schemas/` | `backend-agent` | `architect-agent` (contract approval) | Pydantic models |
| `backend/app/db/models/` | `database-agent` | `backend-agent` | ORM models |
| `backend/app/core/auth.py` | `security-agent` | `backend-agent` | Auth logic |
| `backend/app/core/config.py` | `devops-agent` | `backend-agent` | Configuration |
| `backend/alembic/versions/` | `database-agent` | `backend-agent` | Migrations |
| `backend/app/parsers/` | `parser-agent` | `ecommerce-agent` | Parser logic |
| `backend/app/reconciliation/` | `reconciliation-agent` | `data-quality-agent` | Recon algorithms |
| `backend/tests/` | `qa-agent` | `backend-agent` | Test files |
| `backend/Dockerfile` | `devops-agent` | `backend-agent` | Container config |
| `backend/requirements.txt` | `backend-agent` | `security-agent` (dep review) | Dependencies |

## Frontend Ownership

| Path | Primary Owner | Collaborators | Notes |
|---|---|---|---|
| `frontend/src/pages/` | `frontend-agent` | `uiux-agent` (design review) | Page components |
| `frontend/src/components/` | `frontend-agent` | `uiux-agent` (design review) | Shared components |
| `frontend/src/hooks/` | `frontend-agent` | — | Custom hooks |
| `frontend/src/store/` | `frontend-agent` | — | Zustand stores |
| `frontend/src/utils/api.js` | `frontend-agent` | `security-agent` (token handling) | API client |
| `frontend/src/index.css` | `uiux-agent` | `frontend-agent` | Design tokens |
| `frontend/src/pages/Login.jsx` | `uiux-agent` + `frontend-agent` | — | Brand-critical |
| `frontend/tests/` | `qa-agent` | `frontend-agent` | Test files |
| `frontend/Dockerfile` | `devops-agent` | `frontend-agent` | Container config |
| `frontend/nginx.template.conf` | `devops-agent` | `frontend-agent` | Nginx config |

## Mobile Ownership

| Path | Primary Owner | Collaborators | Notes |
|---|---|---|---|
| `mobile/lib/core/theme/` | `uiux-agent` | `flutter-agent` | Design tokens |
| `mobile/lib/core/` | `flutter-agent` | — | Core utilities |
| `mobile/lib/features/` | `flutter-agent` | `uiux-agent` (visual review) | Feature modules |
| `mobile/lib/services/` | `flutter-agent` | `backend-agent` (API contract) | API services |
| `mobile/lib/parsers/` | `parser-agent` | `flutter-agent` | Mobile parsers |
| `mobile/lib/storage/` | `flutter-agent` | `security-agent` (secure storage) | Hive + secure |
| `mobile/pubspec.yaml` | `flutter-agent` | `security-agent` (dep review) | Dependencies |
| `mobile/android/` | `flutter-agent` | `devops-agent` | Build config |

## Infrastructure Ownership

| Path | Primary Owner | Collaborators | Notes |
|---|---|---|---|
| `docker-compose.prod.yml` | `devops-agent` | `architect-agent` | Production compose |
| `docker-compose.yml` | `devops-agent` | `backend-agent`, `frontend-agent` | Dev compose |
| `deploy.sh` | `devops-agent` | — | Deploy script |
| `nginx/nginx.prod.conf` | `devops-agent` | `security-agent` | SSL + proxy config |
| `nginx/nginx.nossl.conf` | `devops-agent` | — | HTTP proxy config |
| `infra/terraform/` | `devops-agent` | `security-agent` | Cloud infra |
| `scripts/ssl-init.sh` | `devops-agent` | — | SSL setup |
| `.github/workflows/` | `devops-agent` | `qa-manager-agent` | CI/CD pipelines |

## AI System Ownership

| Path | Primary Owner | Collaborators | Notes |
|---|---|---|---|
| `.ai/agents/` | `orchestrator-agent` | `architect-agent` | Agent definitions |
| `.ai/governance/` | `architect-agent` | — | Governance docs |
| `.ai/standards/` | `architect-agent` | Domain owners | Standards |
| `.ai/memory/` | `orchestrator-agent` | All agents | Session state |
| `.ai/workflows/` | `orchestrator-agent` | — | Process definitions |

## Cross-Cutting Concerns

| Concern | Primary Owner | Escalation |
|---|---|---|
| API contract changes | `architect-agent` | `ceo-agent` |
| Database schema | `database-agent` | `architect-agent` |
| Authentication | `security-agent` | `architect-agent` |
| Financial calculations | `data-quality-agent` | `ceo-agent` |
| Design system | `uiux-agent` | `architect-agent` |
| Release decision | `release-manager-agent` | `ceo-agent` |
| Release gate | `release-gatekeeper-agent` | `ceo-agent` only |
| Test strategy | `qa-manager-agent` | `architect-agent` |
| Production incidents | `devops-agent` | `release-manager-agent` → `ceo-agent` |
