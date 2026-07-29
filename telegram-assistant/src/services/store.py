"""Bazadagi sozlamalarni o'qish/yozish (kesh bilan)."""

from __future__ import annotations

from sqlalchemy import select

from ..database.models import Setting
from ..database.session import async_session


class SettingsStore:
    """settings jadvali ustidagi kalit-qiymat ombori."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    async def get(self, key: str, default: str = "") -> str:
        if key in self._cache:
            return self._cache[key]
        async with async_session() as s:
            row = (await s.execute(select(Setting).where(Setting.key == key))).scalars().first()
        value = row.value if row else default
        self._cache[key] = value
        return value

    async def get_int(self, key: str, default: int = 0) -> int:
        raw = await self.get(key, str(default))
        try:
            return int(raw)
        except ValueError:
            return default

    async def get_bool(self, key: str, default: bool = False) -> bool:
        return (await self.get(key, "1" if default else "0")) == "1"

    async def set(self, key: str, value: str) -> None:
        async with async_session() as s:
            row = await s.get(Setting, key)
            if row is None:
                s.add(Setting(key=key, value=value))
            else:
                row.value = value
            await s.commit()
        self._cache[key] = value


store = SettingsStore()
