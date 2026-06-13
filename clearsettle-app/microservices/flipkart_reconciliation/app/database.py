from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


def _build_engine():
    url = get_settings().database_url
    if not url:
        return None
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return create_async_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


engine = _build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = (
    async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    if engine
    else None
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialised — set DATABASE_URL in .env")
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    if engine is None:
        return
    import app.models  # noqa: registers all models with Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(app.models.Base.metadata.create_all)
