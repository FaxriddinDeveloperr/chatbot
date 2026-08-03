"""Async SQLAlchemy engine va sessiya fabrikasi."""

from __future__ import annotations

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine

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


async def _drop_legacy_people_columns(conn: AsyncConnection) -> None:
    """Endi ishlatilmaydigan eski ustunlarni (level, message_count) olib
    tashlaydi — ularning NOT NULL cheklovi (default'siz) yangi odam
    yozishga to'sqinlik qilar edi, chunki joriy model ularni bilmaydi."""
    rows = (await conn.execute(text("PRAGMA table_info(people)"))).fetchall()
    columns = {row[1] for row in rows}
    if "level" in columns:
        await conn.execute(text("DROP INDEX IF EXISTS ix_people_level"))
        await conn.execute(text("ALTER TABLE people DROP COLUMN level"))
    if "message_count" in columns:
        await conn.execute(text("ALTER TABLE people DROP COLUMN message_count"))


async def init_db() -> None:
    """Jadvallarni yaratadi (mavjudlarini o'zgartirmaydi) va eski ustunlarni tozalaydi."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _drop_legacy_people_columns(conn)
