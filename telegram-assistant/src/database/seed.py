"""Baza birinchi marta yaratilganda boshlang'ich sozlamalar bilan to'ldirish."""

from __future__ import annotations

from sqlalchemy import select

from .models import Setting
from .session import async_session

DEFAULT_SETTINGS: dict[str, str] = {
    "business_connection_id": "",
    "model": "",  # bo'sh bo'lsa .env dagi GEMINI_MODEL ishlatiladi
}


async def seed() -> None:
    """Bo'sh bazani boshlang'ich sozlamalar bilan to'ldiradi."""
    async with async_session() as s:
        existing = {
            row.key for row in (await s.execute(select(Setting))).scalars().all()
        }
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                s.add(Setting(key=key, value=value))

        await s.commit()
