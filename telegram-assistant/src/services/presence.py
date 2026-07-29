"""Owner online/offline holatini aniqlash.

Rejimlar:
- "active" — /off bosilgan: owner offline deb hisoblanadi, bot DOIM javob beradi.
  Avtomatik detektor buni bekor qilmaydi (faqat /on qaytaradi).
- "auto"   — /on yoki standart: owner oxirgi N daqiqada biror chatga yozmagan
  bo'lsa → offline (bot ishlaydi); yozgan zahoti → online (bot jim).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..database.models import utcnow
from .store import store

MODE_AUTO = "auto"
MODE_ACTIVE = "active"


async def mark_owner_activity() -> None:
    """Owner biror chatga yozdi — hozirgi vaqtni saqlaymiz."""
    await store.set("last_owner_activity", utcnow().isoformat())


async def set_mode(mode: str) -> None:
    await store.set("mode", mode)
    if mode == MODE_AUTO:
        # /on bosildi — owner hozir online, avtomatik hisob qaytadan boshlanadi
        await mark_owner_activity()


async def get_mode() -> str:
    return await store.get("mode", MODE_AUTO)


async def owner_is_offline() -> bool:
    """True — bot javob berishi kerak (owner offline)."""
    mode = await get_mode()
    if mode == MODE_ACTIVE:
        return True

    raw = await store.get("last_owner_activity", "")
    if not raw:
        return False  # hali faollik ko'rilmagan — ehtiyotkorlik bilan jim turamiz
    try:
        last = datetime.fromisoformat(raw)
    except ValueError:
        return False
    minutes = await store.get_int("auto_offline_minutes", 15)
    return utcnow() - last > timedelta(minutes=minutes)


async def status_line() -> str:
    """/status va /start uchun qisqa holat matni."""
    mode = await get_mode()
    if mode == MODE_ACTIVE:
        return "🔴 Offline (qo'lda) — bot javob beradi"
    if await owner_is_offline():
        minutes = await store.get_int("auto_offline_minutes", 15)
        return f"🟡 Offline (avto, {minutes} daqiqa jimlik) — bot javob beradi"
    return "🟢 Online — bot jim turibdi"
