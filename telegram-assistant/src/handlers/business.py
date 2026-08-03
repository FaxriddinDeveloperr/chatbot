"""Telegram Business yangilanishlarini qayta ishlash.

Bot AI orqali avtomatik javob bermaydi — u faqat: (1) business ulanish
holatini kuzatib business_connection_id'ni saqlaydi (rejalashtirilgan
xabarlarni yuborish uchun kerak), (2) sizga yozgan odamlarni "kontakt"
sifatida bazaga yozadi, shunda /schedule ularni ism/username bo'yicha
topa oladi.
"""

from __future__ import annotations

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from ..config import config
from ..database import repo
from ..services.store import store


async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Business connection yoqildi/o'chirildi — saqlab, ownerga xabar beramiz."""
    conn = update.business_connection
    if conn is None:
        return
    if conn.is_enabled:
        await store.set("business_connection_id", conn.id)
        text = "🔗 Telegram Business akkauntingizga ulandim. Endi ishlashga tayyorman!"
    else:
        await store.set("business_connection_id", "")
        text = "❌ Business ulanish uzildi."
    if config.owner_id:
        try:
            await context.bot.send_message(chat_id=config.owner_id, text=text)
        except Exception:  # noqa: BLE001
            pass


async def handle_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kelgan business xabarni kontakt sifatida bazaga yozadi (javob bermaydi)."""
    msg = update.business_message
    if msg is None or msg.from_user is None:
        return

    # Botning o'z xabarlari business ulanish orqali shu chatga aks etib
    # qaytishi mumkin (o'z-o'ziga yozish siklini oldini olish uchun), va
    # guruh/kanal emas — faqat shaxsiy (1-1) suhbatlar bilan ishlaymiz.
    if msg.from_user.id == context.bot.id or msg.chat.type != ChatType.PRIVATE:
        return

    if msg.business_connection_id:
        await store.set("business_connection_id", msg.business_connection_id)

    # Owner o'zi yozgan xabar — kontakt sifatida yozilmaydi
    if msg.from_user.id == config.owner_id:
        return

    user = msg.from_user
    await repo.upsert_person(user.id, user.username, user.full_name or "")
