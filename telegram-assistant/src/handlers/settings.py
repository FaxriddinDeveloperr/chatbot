"""Sozlamalar menyusi — /schedule'ning bitta xabarli tahlili uchun model tanlash."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..config import config
from ..services.store import store
from ..utils import keyboards
from .commands import guard, is_owner

TITLE = "⚙️ Sozlamalar\n\nO'zgartirish uchun tugmani bosing:"


async def _values() -> dict[str, str]:
    return {"model": (await store.get("model", "")) or config.gemini_model}


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(
        TITLE, reply_markup=keyboards.settings_menu(await _values())
    )


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """st:* tugmalari."""
    query = update.callback_query
    if query is None or not is_owner(update):
        if query:
            await query.answer("Ruxsat yo'q")
        return
    await query.answer()

    parts = query.data.split(":")
    action = parts[1]

    if action == "menu":
        await query.edit_message_text(TITLE, reply_markup=keyboards.settings_menu(await _values()))

    elif action == "model":
        context.user_data["await"] = ("st_model",)
        await query.edit_message_text(
            "🧠 Model nomini yuboring (masalan: gemini-flash-latest):"
        )


async def handle_settings_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: tuple
) -> bool:
    """Model nomi matn orqali kiritiladi."""
    if state[0] != "st_model":
        return False
    model = update.message.text.strip()
    await store.set("model", model)
    await update.message.reply_text(f"✅ Model o'zgartirildi: {model}")
    return True
