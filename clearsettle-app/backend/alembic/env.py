"""
Alembic migration environment — async edition.

Uses asyncpg (same driver as the app) via asyncio.run() so the migration
process stays compatible with `alembic upgrade head` called from a shell
script (start.sh) in a completely synchronous context.
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Make the app package importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.db.base import Base  # noqa: Base must be imported before models
import app.db.models  # noqa: registers all ORM models with Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()


def _get_url() -> str:
    """
    Return the database URL normalised to asyncpg format.
    Accepts postgresql://, postgresql+psycopg2://, or postgresql+asyncpg://.
    """
    url = settings.database_url or ""
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# ── Offline mode (generates SQL without a live DB) ───────────────────────────

def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connects to a live DB) ──────────────────────────────────────

def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = _get_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set — cannot run migrations")

    connectable = create_async_engine(url, echo=False)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
