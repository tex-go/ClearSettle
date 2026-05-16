# ClearSettle — Unified eCommerce Intelligence

eCommerce reconciliation SaaS for Indian multi-platform sellers (Tirupur textile vendors).

## Quick Start

```bash
docker-compose up --build
```

## Access URLs

| URL | Description |
|-----|-------------|
| http://localhost | Full app (nginx proxy) |
| http://localhost:3000 | Frontend direct |
| http://localhost:8000 | Backend API direct |
| http://localhost:8000/docs | Swagger UI |

## Demo Credentials

```
Email:    demo@clearsettle.in
Password: demo123
```

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11 |
| Frontend | React 18 + Vite + Recharts + Zustand |
| Proxy | Nginx |
| Deploy | Docker Compose |

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
