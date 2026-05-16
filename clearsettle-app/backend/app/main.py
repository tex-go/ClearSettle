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


@app.get("/health")
def health():
    return {"status": "ok", "service": "ClearSettle API"}
