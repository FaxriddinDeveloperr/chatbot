"""Owner komandalar: /start /history /logs + bosh menyu."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..config import config
from ..database import repo
from ..utils import keyboards

WELCOME = (
    "📅 Xabar rejalashtiruvchi\n\n"
    "Odamlarga ma'lum vaqtda xabar yuborishni rejalashtiring — /schedule "
    "bilan boshlang."
)


def is_owner(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id == config.owner_id


async def guard(update: Update) -> bool:
    """Owner bo'lmaganlarga komandalar ishlamaydi."""
    if is_owner(update):
        return True
    # OWNER_ID hali sozlanmagan bo'lsa — foydalanuvchiga o'z ID sini ko'rsatamiz
    if config.owner_id == 0 and update.message is not None:
        await update.message.reply_text(
            f"OWNER_ID sozlanmagan. Sizning ID: {update.effective_user.id}\n"
            f"Uni .env faylga OWNER_ID={update.effective_user.id} qilib yozing "
            "va botni qayta ishga tushiring."
        )
    return False


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(WELCOME, reply_markup=keyboards.main_menu())


async def _history_text() -> str:
    logs = await repo.recent_responses(10)
    if not logs:
        return "📜 Hali yuborilgan rejalashtirilgan xabarlar yo'q."
    lines = ["📜 Oxirgi yuborilgan xabarlar:\n"]
    for log in logs:
        when = log.created_at.strftime("%d.%m %H:%M")
        lines.append(f"📤 {when} — {log.person_name}\n   \"{log.reply[:80]}\"")
    return "\n".join(lines)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(await _history_text())


async def _logs_text() -> str:
    errors = await repo.recent_errors(10)
    if not errors:
        return "🐞 Xatoliklar yo'q. Hammasi joyida! ✨"
    lines = ["🐞 Oxirgi xatoliklar:\n"]
    for err in errors:
        when = err.created_at.strftime("%d.%m %H:%M")
        lines.append(f"• {when} — {err.message[:200]}")
    return "\n".join(lines)


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(await _logs_text())


async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bosh menyu tugmalari: menu:*"""
    query = update.callback_query
    if query is None or not is_owner(update):
        if query:
            await query.answer("Ruxsat yo'q")
        return
    await query.answer()
    data = query.data

    if data == "menu:main":
        await query.edit_message_text(WELCOME, reply_markup=keyboards.main_menu())
    elif data == "menu:history":
        await query.edit_message_text(await _history_text(), reply_markup=keyboards.main_menu())
    elif data == "menu:logs":
        await query.edit_message_text(await _logs_text(), reply_markup=keyboards.main_menu())
