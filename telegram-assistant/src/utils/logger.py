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
