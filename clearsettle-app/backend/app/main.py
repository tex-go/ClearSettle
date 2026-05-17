import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    auth, dashboard, settlements, bank, disputes,
    returns, commission, gst, inventory, cashflow,
    analytics, platforms, reports, dispute_engine, recovery, competitors,
    sp_api,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.database_url:
        try:
            from app.db.database import init_db
            init_db()
            logger.info("Database initialised")
        except Exception as exc:
            logger.warning("DB init skipped (Alembic may manage schema): %s", exc)
    yield


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


@app.get("/")
def root():
    settings = get_settings()
    return {
        "service": "ClearSettle API",
        "status": "online",
        "version": "1.0.0",
        "database": "connected" if settings.database_url else "mock-data mode",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    settings = get_settings()
    db_status = "not_configured"
    if settings.database_url:
        try:
            from app.db.database import engine
            with engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:
            db_status = f"error: {exc}"
    return {"status": "ok", "service": "ClearSettle API", "database": db_status}


@app.get("/status")
def status():
    settings = get_settings()
    return {
        "service": "ClearSettle API",
        "status": "online",
        "version": "1.0.0",
        "environment": settings.env,
        "database": "postgresql" if "postgresql" in settings.database_url else
                    ("sqlite" if "sqlite" in settings.database_url else "none"),
        "sp_api_configured": bool(settings.sp_api_app_id and settings.sp_api_client_id),
        "demo_credentials": {"email": "demo@clearsettle.in", "password": "demo123"},
        "features": [
            {"id": "auth",           "route": "/auth"},
            {"id": "dashboard",      "route": "/dashboard"},
            {"id": "settlements",    "route": "/settlements"},
            {"id": "bank",           "route": "/bank"},
            {"id": "disputes",       "route": "/disputes"},
            {"id": "returns",        "route": "/returns"},
            {"id": "commission",     "route": "/commission"},
            {"id": "gst",            "route": "/gst"},
            {"id": "inventory",      "route": "/inventory"},
            {"id": "cashflow",       "route": "/cashflow"},
            {"id": "analytics",      "route": "/analytics"},
            {"id": "platforms",      "route": "/platforms"},
            {"id": "reports",        "route": "/reports"},
            {"id": "dispute_engine", "route": "/dispute-engine"},
            {"id": "recovery",       "route": "/recovery"},
            {"id": "competitors",    "route": "/competitors"},
            {"id": "sp_api",         "route": "/sp-api"},
        ],
        "total_features": 17,
    }
