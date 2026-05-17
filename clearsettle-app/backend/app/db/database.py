"""
Async SQLAlchemy engine + session factory.

Uses asyncpg as the PostgreSQL driver for non-blocking I/O.
psycopg2 is kept in requirements.txt only for Alembic's sync migrations.

URL format expected in DATABASE_URL env var:
    postgresql+asyncpg://user:password@host:5432/dbname
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base  # noqa: re-exported so alembic env can import it


def _build_engine():
    url = get_settings().database_url
    if not url:
        return None

    # Accept either format; normalise to asyncpg
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )


engine = _build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = (
    async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    if engine
    else None
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session; used by FastAPI Depends."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialised")
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """
    Create all tables from metadata.
    Only used in development / testing when Alembic is not available.
    In production start.sh runs `alembic upgrade head` before uvicorn.
    """
    if engine is None:
        return
    import app.db.models  # noqa: ensure all models are registered with Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
