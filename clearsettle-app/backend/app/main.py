from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    auth, dashboard, settlements, bank, disputes,
    returns, commission, gst, inventory, cashflow,
    analytics, platforms, reports, dispute_engine, recovery, competitors
)

app = FastAPI(title="ClearSettle API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(settlements.router, prefix="/settlements", tags=["settlements"])
app.include_router(bank.router, prefix="/bank", tags=["bank"])
app.include_router(disputes.router, prefix="/disputes", tags=["disputes"])
app.include_router(returns.router, prefix="/returns", tags=["returns"])
app.include_router(commission.router, prefix="/commission", tags=["commission"])
app.include_router(gst.router, prefix="/gst", tags=["gst"])
app.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
app.include_router(cashflow.router, prefix="/cashflow", tags=["cashflow"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(platforms.router, prefix="/platforms", tags=["platforms"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(dispute_engine.router, prefix="/dispute-engine", tags=["dispute-engine"])
app.include_router(recovery.router, prefix="/recovery", tags=["recovery"])
app.include_router(competitors.router, prefix="/competitors", tags=["competitors"])


@app.get("/")
def root():
    return {
        "service": "ClearSettle API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "status_endpoint": "/status",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "ClearSettle API"}


@app.get("/status")
def status():
    return {
        "service": "ClearSettle API",
        "status": "online",
        "version": "1.0.0",
        "environment": "production",
        "demo_credentials": {
            "email": "demo@clearsettle.in",
            "password": "demo123",
        },
        "features": [
            {"id": "auth",            "route": "/auth",            "description": "JWT login / logout / profile"},
            {"id": "dashboard",       "route": "/dashboard",       "description": "Live KPIs, platform overview, settlement trend"},
            {"id": "settlements",     "route": "/settlements",     "description": "Platform payout tracking with breakdown"},
            {"id": "bank",            "route": "/bank",            "description": "Bank credit ↔ settlement ID reconciliation"},
            {"id": "disputes",        "route": "/disputes",        "description": "Overcharge and penalty dispute management"},
            {"id": "returns",         "route": "/returns",         "description": "Return deductions and reason analysis"},
            {"id": "commission",      "route": "/commission",      "description": "Published vs charged commission rate audit"},
            {"id": "gst",             "route": "/gst",             "description": "TCS/TDS reconciliation and ITC claims"},
            {"id": "inventory",       "route": "/inventory",       "description": "Multi-platform stock levels with low-stock alerts"},
            {"id": "cashflow",        "route": "/cashflow",        "description": "30-day settlement calendar and cash flow forecast"},
            {"id": "analytics",       "route": "/analytics",       "description": "SKU-level profitability and P&L analysis"},
            {"id": "platforms",       "route": "/platforms",       "description": "Marketplace API connection settings"},
            {"id": "reports",         "route": "/reports",         "description": "PDF / Excel / CSV report generation"},
            {"id": "dispute_engine",  "route": "/dispute-engine",  "description": "8 automated dispute detection rules + recovery calculator"},
            {"id": "recovery",        "route": "/recovery",        "description": "Filed disputes and recovery timeline tracker"},
            {"id": "competitors",     "route": "/competitors",     "description": "Market intelligence and competitor feature matrix"},
        ],
        "total_features": 16,
    }
