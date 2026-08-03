"""Logging sozlash va xatoliklarni bazaga yozib, ownerga xabar berish."""

from __future__ import annotations

import logging

from telegram.ext import ContextTypes

from ..config import config
from ..database import repo


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    # httpx har bir so'rovni log qilmasin
    logging.getLogger("httpx").setLevel(logging.WARNING)


def humanize_send_error(exc: Exception) -> str:
    """Telegram'ning xom xato matnini tushunarli, harakat qilsa bo'ladigan
    izohga aylantiradi. Tanilmagan xatolar o'zgarishsiz qaytariladi."""
    text = str(exc)
    if "business_peer_invalid" in text.lower():
        return (
            "Bu odamga Business orqali xabar yubora olmadim — bu Telegram'ning "
            "o'zidagi cheklov, kodda xato emas. Sabab: shu aniq chat uchun "
            "botning yozish ruxsati o'chirilgan bo'lishi mumkin.\n\n"
            "Tekshiring: 1) shu odam bilan suhbatni oching — yuqorida bot "
            "nomi/belgisi ko'rinsa, ruxsat yoqilganini tasdiqlang; "
            "2) Sozlamalar → Telegram Business → Chatbots → bu bot → chat "
            "ruxsatlarida bu odam \"Exclude\" qilinmaganini tekshiring.\n\n"
            f"(Xom xato: {text})"
        )
    return text


async def report_error(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Xatoni bazaga yozadi va ownerga yuboradi. Odamga HECH QACHON yuborilmaydi."""
    logging.getLogger("assistant").error(text)
    try:
        await repo.log_error(text)
    except Exception:  # noqa: BLE001 — log yozish ham yiqilsa, davom etamiz
        logging.getLogger("assistant").exception("Xatoni bazaga yozib bo'lmadi")
    if config.owner_id:
        try:
            await context.bot.send_message(
                chat_id=config.owner_id, text=f"⚠️ Xatolik:\n{text[:3500]}"
            )
        except Exception:  # noqa: BLE001
            pass
