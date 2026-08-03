"""Async SQLAlchemy engine va sessiya fabrikasi."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import config
from .models import Base

config.db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(f"sqlite+aiosqlite:///{config.db_path}", echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """WAL rejimi + busy timeout — bir vaqtda bir necha yozuv bo'lganda
    "database is locked" xatosini kamaytiradi."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


async def init_db() -> None:
    """Jadvallarni yaratadi (mavjudlarini o'zgartirmaydi)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
