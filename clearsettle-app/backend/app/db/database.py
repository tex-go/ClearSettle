from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    url = get_settings().database_url
    if not url:
        return None

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,   # reconnect on stale connections
        pool_size=5,
        max_overflow=10,
    )
    return engine


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None


def init_db():
    """Create all tables (used when Alembic is not available, e.g. SQLite dev)."""
    if engine is None:
        return
    from app.db import models  # noqa: ensure all models are registered
    Base.metadata.create_all(bind=engine)
