from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ingest, orders, reconciliation
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Flipkart Reconciliation Engine",
    description="Identifies revenue leakage by comparing expected vs actual Flipkart settlements.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(orders.router, tags=["orders"])
app.include_router(reconciliation.router, prefix="/reconciliation", tags=["reconciliation"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "flipkart-reconciliation-engine"}
