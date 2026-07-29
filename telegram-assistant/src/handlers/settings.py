"""Sozlamalar menyusi: hamma narsa tugma orqali o'zgartiriladi."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..config import config
from ..database import repo
from ..services.store import store
from ..utils import keyboards
from .commands import guard, is_owner

TITLE = "⚙️ Sozlamalar\n\nO'zgartirish uchun tugmani bosing:"


async def _values() -> dict[str, str]:
    return {
        "auto_offline_minutes": await store.get("auto_offline_minutes", "15"),
        "voice_enabled": await store.get("voice_enabled", "1"),
        "voice_min_chars": await store.get("voice_min_chars", "300"),
        "default_lang": await store.get("default_lang", "auto"),
        "model": (await store.get("model", "")) or config.gemini_model,
        "context_depth": await store.get("context_depth", "20"),
        "delay_min": await store.get("delay_min", "3"),
        "delay_max": await store.get("delay_max", "8"),
    }


async def _show_menu(query) -> None:
    await query.edit_message_text(TITLE, reply_markup=keyboards.settings_menu(await _values()))


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
    value = parts[2] if len(parts) > 2 else None

    if action == "menu":
        await _show_menu(query)

    elif action == "auto_off":
        if value:
            await store.set("auto_offline_minutes", value)
            await _show_menu(query)
        else:
            await query.edit_message_text(
                "🕐 Auto-offline vaqtini tanlang (daqiqa):",
                reply_markup=keyboards.choices("st:auto_off", ["5", "10", "15", "30", "60"]),
            )

    elif action == "voice":
        current = await store.get_bool("voice_enabled", True)
        await store.set("voice_enabled", "0" if current else "1")
        await _show_menu(query)

    elif action == "minchars":
        if value:
            await store.set("voice_min_chars", value)
            await _show_menu(query)
        else:
            await query.edit_message_text(
                "📏 Ovozli javob uchun minimal uzunlik (belgi):",
                reply_markup=keyboards.choices("st:minchars", ["150", "300", "500", "800"]),
            )

    elif action == "lang":
        if value:
            await store.set("default_lang", value)
            await _show_menu(query)
        else:
            await query.edit_message_text(
                "🌐 Standart til (aniqlanmay qolsa ishlatiladi):",
                reply_markup=keyboards.choices("st:lang", ["auto", "uz", "ru", "en"]),
            )

    elif action == "model":
        context.user_data["await"] = ("st_model",)
        await query.edit_message_text(
            "🧠 Model nomini yuboring (masalan: gemini-2.0-flash):"
        )

    elif action == "context":
        if value:
            await store.set("context_depth", value)
            await _show_menu(query)
        else:
            await query.edit_message_text(
                "💬 Kontekst chuqurligi (xabarlar soni):",
                reply_markup=keyboards.choices("st:context", ["10", "20", "30", "50"]),
            )

    elif action == "delay":
        if value:
            lo, hi = value.split("-")
            await store.set("delay_min", lo)
            await store.set("delay_max", hi)
            await _show_menu(query)
        else:
            await query.edit_message_text(
                "⏱ Javob kechikishi (soniya, tabiiy ko'rinish uchun):",
                reply_markup=keyboards.choices("st:delay", ["1-3", "2-5", "3-8", "5-12"]),
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
