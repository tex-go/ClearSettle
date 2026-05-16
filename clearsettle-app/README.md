# ClearSettle — Unified eCommerce Intelligence

eCommerce reconciliation SaaS for Indian multi-platform sellers (Tirupur textile vendors).

---

## Railway Deployment (Production)

### How it works

Two Railway services in one project:
- **Backend** — FastAPI, root directory `clearsettle-app/backend`
- **Frontend** — React + nginx, root directory `clearsettle-app/frontend`

The frontend nginx proxies `/api/*` to the backend at runtime using the `API_URL` env var — no build-time baking, no CORS issues.

### Step-by-step

#### 1. Create a Railway project

Go to [railway.app](https://railway.app) → New Project → Empty Project.

#### 2. Add the Backend service

1. Click **+ New Service** → **GitHub Repo** → select this repo
2. Set **Root Directory** to `clearsettle-app/backend`
3. Railway auto-detects `railway.toml` and uses the Dockerfile
4. Add these **Environment Variables** in the service settings:
   ```
   SECRET_KEY=your-secret-key-change-this-in-prod
   ENV=production
   ```
5. Click **Deploy** → wait for the health check `/health` to pass
6. Go to **Settings → Networking** → click **Generate Domain**
7. Copy the domain, e.g. `clearsettle-backend-production.up.railway.app`

#### 3. Add the Frontend service

1. Click **+ New Service** → **GitHub Repo** → same repo
2. Set **Root Directory** to `clearsettle-app/frontend`
3. Add these **Environment Variables**:
   ```
   API_URL=https://clearsettle-backend-production.up.railway.app
   ```
   Replace the URL with your actual backend domain from step 6 above.
4. Click **Deploy**
5. Generate a domain for the frontend too

#### 4. Done

Open the frontend Railway URL — login with the demo credentials below.

> **Tip:** You can use Railway reference variables so you don't need to copy-paste the backend URL manually:
> ```
> API_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}
> ```
> (Replace `backend` with your backend service name in Railway.)

---

## Local Development (Docker Compose)

```bash
cd clearsettle-app
docker-compose up --build
```

| URL | Description |
|-----|-------------|
| http://localhost | Full app via nginx |
| http://localhost:3000 | Frontend direct |
| http://localhost:8000 | Backend API direct |
| http://localhost:8000/docs | Swagger UI |

---

## Demo Credentials

```
Email:    demo@clearsettle.in
Password: demo123
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11 |
| Frontend | React 18 + Vite + Recharts + Zustand |
| Proxy | Nginx (with runtime `envsubst` for Railway) |
| Deploy | Docker Compose (local) / Railway (production) |

## Features (15 Pages)

1. **Dashboard** — Live KPIs, platform overview, settlement trend chart
2. **Settlements** — Track all platform payouts with breakdown modal
3. **Bank Reconciliation** — Match bank credits to settlement IDs
4. **Disputes** — Manage overcharge and penalty disputes
5. **Returns** — Return deductions, reason analysis, platform rates
6. **Commission Audit** — Published vs charged rate comparison
7. **GST / TCS** — TCS/TDS reconciliation and ITC claims
8. **Inventory Sync** — Multi-platform stock levels with alerts
9. **Cash Flow Forecast** — 30-day settlement calendar
10. **Profitability** — SKU-level P&L analysis
11. **Dispute Rule Engine** — 8 automated detection rules + recovery calculator
12. **Recovery Tracker** — Filed disputes and recovery timeline
13. **Market Intelligence** — Competitor feature matrix
14. **Platform Settings** — Manage marketplace API connections
15. **Reports** — Generate PDF/Excel/CSV for all modules

## Architecture

```
clearsettle-app/
├── backend/           FastAPI app (Python)
│   └── app/
│       ├── core/      Auth (JWT)
│       ├── data/      Mock data (no DB needed)
│       └── routers/   16 API routers
├── frontend/          React 18 app
│   └── src/
│       ├── pages/     15 page components
│       ├── components/ Layout + UI primitives
│       ├── store/     Zustand (auth + toasts)
│       ├── hooks/     useApi
│       └── utils/     api.js, format.js
└── nginx/             Reverse proxy config
```
