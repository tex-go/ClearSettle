"""
Read-only async connection to the flipkart_recon database.

The main backend uses this to surface Flipkart ETL and reconciliation data
across the Dashboard, Settlements, Commission, GST, and Returns pages.

Connection: postgresql+asyncpg://clearsettle_user:***@localhost:5432/flipkart_recon
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import os as _os

# Inside Docker the PostgreSQL container is reachable via service name "postgres".
# Outside Docker (microservice on Windows host) localhost:5432 works.
_FK_HOST = _os.environ.get("FK_DB_HOST", "postgres")
_FK_DSN = (
    f"postgresql+asyncpg://clearsettle_user:clearsettle_pass"
    f"@{_FK_HOST}:5432/flipkart_recon"
)

_engine = create_async_engine(
    _FK_DSN,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=5,
    echo=False,
)

_SessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_fk_session() -> AsyncSession:
    """Yield a read-only async session to the flipkart_recon database."""
    async with _SessionLocal() as session:
        yield session


@asynccontextmanager
async def fk_session():
    """Async context-manager for direct (non-DI) use in routers."""
    async with _SessionLocal() as session:
        yield session
