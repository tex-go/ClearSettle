import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    auth, dashboard, settlements, bank, disputes,
    returns, commission, gst, inventory, cashflow,
    analytics, platforms, reports, dispute_engine, recovery, competitors,
    sp_api, sync, reconciliation, rules, onboarding, api_health, vendor_recon,
    seller_discovery, forecast, meetings,
)
from app.routers import flipkart_reports, admin

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.database_url:
        try:
            from app.db.database import init_db
            await init_db()
            logger.info("Database initialised")
        except Exception as exc:
            logger.warning("DB init skipped (Alembic manages schema in prod): %s", exc)

        # Load RBAC permissions from DB into memory cache
        try:
            from app.db.database import AsyncSessionLocal
            from app.core.rbac import load_rbac_from_db
            if AsyncSessionLocal:
                async with AsyncSessionLocal() as session:
                    await load_rbac_from_db(session)
        except Exception as exc:
            logger.warning("RBAC DB load failed at startup — static fallback active: %s", exc)

    from app.services.seller_discovery import scheduler as discovery_scheduler
    await discovery_scheduler.start()

    import asyncio as _asyncio
    from app.services.meetings.reminder_store import run_reminder_scheduler
    _asyncio.create_task(run_reminder_scheduler())

    yield

    await discovery_scheduler.stop()


app = FastAPI(
    title="ClearSettle API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,           prefix="/auth",           tags=["auth"])
app.include_router(dashboard.router,      prefix="/dashboard",      tags=["dashboard"])
app.include_router(settlements.router,    prefix="/settlements",    tags=["settlements"])
app.include_router(bank.router,           prefix="/bank",           tags=["bank"])
app.include_router(disputes.router,       prefix="/disputes",       tags=["disputes"])
app.include_router(returns.router,        prefix="/returns",        tags=["returns"])
app.include_router(commission.router,     prefix="/commission",     tags=["commission"])
app.include_router(gst.router,            prefix="/gst",            tags=["gst"])
app.include_router(inventory.router,      prefix="/inventory",      tags=["inventory"])
app.include_router(cashflow.router,       prefix="/cashflow",       tags=["cashflow"])
app.include_router(analytics.router,      prefix="/analytics",      tags=["analytics"])
app.include_router(platforms.router,      prefix="/platforms",      tags=["platforms"])
app.include_router(reports.router,        prefix="/reports",        tags=["reports"])
app.include_router(dispute_engine.router, prefix="/dispute-engine", tags=["dispute-engine"])
app.include_router(recovery.router,       prefix="/recovery",       tags=["recovery"])
app.include_router(competitors.router,    prefix="/competitors",    tags=["competitors"])
app.include_router(sp_api.router,         prefix="/sp-api",         tags=["sp-api"])
app.include_router(sync.router,            prefix="/sync",            tags=["sync"])
app.include_router(reconciliation.router,  prefix="/reconciliation",  tags=["reconciliation"])
app.include_router(rules.router,           prefix="/rules",           tags=["rules"])
app.include_router(onboarding.router,      prefix="/onboarding",      tags=["onboarding"])
app.include_router(api_health.router,      prefix="/api-health",      tags=["api-health"])
app.include_router(vendor_recon.router,    prefix="/recon-engine",    tags=["recon-engine"])
app.include_router(seller_discovery.router, prefix="/seller-discovery", tags=["seller-discovery"])
app.include_router(forecast.router,              tags=["forecast"])
app.include_router(meetings.router,              tags=["meetings"])
app.include_router(flipkart_reports.router,  prefix="/flipkart",  tags=["flipkart"])
app.include_router(admin.router,             prefix="/admin",      tags=["admin"])


@app.get("/")
def root():
    settings = get_settings()
    return {
        "service":  "ClearSettle API",
        "status":   "online",
        "version":  "1.0.0",
        "database": "connected" if settings.database_url else "mock-data mode",
        "docs":     "/docs",
        "health":   "/health",
    }


@app.get("/health")
async def health():
    settings = get_settings()
    db_status = "not_configured"
    if settings.database_url:
        try:
            from app.db.database import engine
            import sqlalchemy
            async with engine.connect() as conn:
                await conn.execute(sqlalchemy.text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:
            db_status = f"error: {exc}"
    return {"status": "ok", "service": "ClearSettle API", "database": db_status}


@app.get("/status")
def status_endpoint():
    settings = get_settings()
    db_type = "none"
    if "asyncpg" in (settings.database_url or "") or "postgresql" in (settings.database_url or ""):
        db_type = "postgresql"
    elif "sqlite" in (settings.database_url or ""):
        db_type = "sqlite"

    return {
        "service":          "ClearSettle API",
        "status":           "online",
        "version":          "1.0.0",
        "environment":      settings.env,
        "database":         db_type,
        "sp_api_configured": bool(settings.sp_api_app_id and settings.sp_api_client_id),
        "demo_credentials": {"email": "demo@clearsettle.in", "password": "demo123"},
    }
