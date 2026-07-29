"""Baza birinchi marta yaratilganda boshlang'ich ma'lumot bilan to'ldirish."""

from __future__ import annotations

from sqlalchemy import func, select

from .models import KnowledgeSection, Setting
from .session import async_session

SEED_SECTIONS: list[tuple[str, str]] = [
    (
        "Shaxsiy ma'lumot",
        "Ism: Faxriddin\n"
        "Familiya: Maripov\n"
        "Tug'ilgan sana: 08.05.2006 (20 yosh)\n"
        "Shahar: Toshkent\n"
        "Ish vaqti: 10:00 – 19:00",
    ),
    (
        "Kasb va ish",
        "Voltra Energy kompaniyasida Full-stack dasturchi.\n"
        "Texnologiyalar: Node.js, React.js, Next.js, Python.",
    ),
    (
        "Muloqot uslubi",
        "- Har doim \"Assalomu alaykum\" bilan boshlash\n"
        "- Har doim \"siz\" deb murojaat qilish (hech qachon \"sen\" emas)\n"
        "- Emoji ishlatish — lekin me'yorida, 1-2 tadan ko'p emas\n"
        "- Qisqa va aniq yozish, uzun matn yozmaslik\n"
        "- Samimiy, lekin ortiqcha rasmiy emas",
    ),
    (
        "Taqiqlar (JAVOB BERMASLIK KERAK)",
        "Quyidagi mavzularda javob berma — o'rniga \"Bu haqda o'zim javob beraman,\n"
        "biroz kuting\" deb yoz:\n"
        "- Pul qarz berish/olish, moliyaviy so'rovlar\n"
        "- Siyosat, din bo'yicha bahslar\n"
        "- Shaxsiy/oilaviy masalalar\n"
        "- Hech qachon narx, muddat yoki majburiyat bo'yicha aniq va'da berma\n"
        "- Hech qachon parol, kod, shaxsiy ma'lumot yuborma\n"
        "- Hech qachon uchrashuvga rozilik berma",
    ),
    (
        "Tez so'raladigan savollar",
        "S: Yoshingiz nechada?\n"
        "J: 20 yoshdaman, 08.05.2006 yilda tug'ilganman.",
    ),
]

DEFAULT_SETTINGS: dict[str, str] = {
    "mode": "auto",                 # auto | active (/off) — bot ishlaydi
    "auto_offline_minutes": "15",   # shuncha daqiqa jimlikdan keyin offline
    "voice_enabled": "1",
    "voice_min_chars": "300",
    "default_lang": "auto",
    "context_depth": "20",
    "delay_min": "3",
    "delay_max": "8",
    "last_owner_activity": "",
    "business_connection_id": "",
    "model": "",                    # bo'sh bo'lsa .env dagi GEMINI_MODEL ishlatiladi
}


async def seed() -> None:
    """Bo'sh bazani boshlang'ich bo'limlar va sozlamalar bilan to'ldiradi."""
    async with async_session() as s:
        count = (await s.execute(select(func.count(KnowledgeSection.id)))).scalar_one()
        if count == 0:
            for i, (title, content) in enumerate(SEED_SECTIONS, start=1):
                s.add(KnowledgeSection(title=title, content=content, position=i))

        existing = {
            row.key for row in (await s.execute(select(Setting))).scalars().all()
        }
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                s.add(Setting(key=key, value=value))

        await s.commit()
