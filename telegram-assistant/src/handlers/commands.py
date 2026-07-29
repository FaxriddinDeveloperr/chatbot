"""Owner komandalar: /start /on /off /status /stats /history /logs + bosh menyu."""

from __future__ import annotations

from datetime import timedelta

from telegram import Update
from telegram.ext import ContextTypes

from ..config import config
from ..database import repo
from ..database.models import (
    STATUS_APPROVED,
    STATUS_AUTO,
    STATUS_EDITED,
    STATUS_EXPIRED,
    STATUS_REJECTED,
    utcnow,
)
from ..services import presence
from ..utils import keyboards


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


async def _status_text() -> str:
    line = await presence.status_line()
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = await repo.stats_since(today)
    sent = sum(
        stats["by_status"].get(s, 0) for s in (STATUS_AUTO, STATUS_APPROVED, STATUS_EDITED)
    )
    return (
        f"🤖 Shaxsiy yordamchi\n\n"
        f"Holat: {line}\n"
        f"Bugun kelgan xabarlar: {stats['incoming']}\n"
        f"Bugun yuborilgan javoblar: {sent}"
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(await _status_text(), reply_markup=keyboards.main_menu())


async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/off — men offlaynman, bot javob beradi."""
    if not await guard(update):
        return
    await presence.set_mode(presence.MODE_ACTIVE)
    await update.message.reply_text(
        "🔴 Offline rejim yoqildi — bot sizning nomingizdan javob beradi.\n"
        "Qaytish uchun: /on"
    )


async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/on — men onlaynman, bot jim turadi (avto-detektor davom etadi)."""
    if not await guard(update):
        return
    await presence.set_mode(presence.MODE_AUTO)
    minutes = (await presence.store.get_int("auto_offline_minutes", 15))
    await update.message.reply_text(
        f"🟢 Siz onlaynsiz — bot jim turadi.\n"
        f"{minutes} daqiqa faollik bo'lmasa, bot avtomatik ishga tushadi."
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(await _status_text())


PERIODS = {"today": ("Bugun", 0), "week": ("Hafta", 7), "month": ("Oy", 30)}


async def _stats_text(period: str) -> str:
    title, days = PERIODS[period]
    if days == 0:
        since = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        since = utcnow() - timedelta(days=days)
    stats = await repo.stats_since(since)
    bs = stats["by_status"]
    sent = bs.get(STATUS_AUTO, 0) + bs.get(STATUS_APPROVED, 0) + bs.get(STATUS_EDITED, 0)
    top_lines = "\n".join(f"  {i}. {name} — {cnt}" for i, (name, cnt) in enumerate(stats["top"], 1))
    return (
        f"📊 Statistika — {title}\n\n"
        f"📩 Kelgan xabarlar: {stats['incoming']}\n"
        f"📤 Yuborilgan javoblar: {sent}\n"
        f"   • avtomatik: {bs.get(STATUS_AUTO, 0)}\n"
        f"   • tasdiqlangan: {bs.get(STATUS_APPROVED, 0)}\n"
        f"   • tahrirlangan: {bs.get(STATUS_EDITED, 0)}\n"
        f"❌ Rad etilgan: {bs.get(STATUS_REJECTED, 0)}\n"
        f"⌛ Muddati o'tgan: {bs.get(STATUS_EXPIRED, 0)}\n\n"
        f"👥 Eng ko'p yozganlar:\n{top_lines or '  (hali yo`q)'}"
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(
        await _stats_text("today"), reply_markup=keyboards.stats_periods("today")
    )


async def _history_text() -> str:
    logs = await repo.recent_responses(10)
    if not logs:
        return "📜 Hali javoblar tarixi yo'q."
    lines = ["📜 Oxirgi javoblar:\n"]
    icons = {
        STATUS_AUTO: "🤖", STATUS_APPROVED: "✅", STATUS_EDITED: "✏️",
        STATUS_REJECTED: "❌", STATUS_EXPIRED: "⌛",
    }
    for log in logs:
        when = log.created_at.strftime("%d.%m %H:%M")
        lines.append(
            f"{icons.get(log.status, '•')} {when} — {log.person_name}\n"
            f"   ⬅️ {log.incoming[:80]}\n"
            f"   ➡️ {log.reply[:80]}\n"
        )
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
    """Bosh menyu tugmalari: menu:* , mode:* , sts:*"""
    query = update.callback_query
    if query is None or not is_owner(update):
        if query:
            await query.answer("Ruxsat yo'q")
        return
    await query.answer()
    data = query.data

    if data == "menu:main":
        await query.edit_message_text(await _status_text(), reply_markup=keyboards.main_menu())
    elif data == "menu:history":
        await query.edit_message_text(await _history_text(), reply_markup=keyboards.main_menu())
    elif data == "menu:logs":
        await query.edit_message_text(await _logs_text(), reply_markup=keyboards.main_menu())
    elif data == "mode:active":
        await presence.set_mode(presence.MODE_ACTIVE)
        await query.edit_message_text(await _status_text(), reply_markup=keyboards.main_menu())
    elif data == "mode:auto":
        await presence.set_mode(presence.MODE_AUTO)
        await query.edit_message_text(await _status_text(), reply_markup=keyboards.main_menu())
    elif data.startswith("sts:"):
        period = data.split(":", 1)[1]
        if period in PERIODS:
            await query.edit_message_text(
                await _stats_text(period), reply_markup=keyboards.stats_periods(period)
            )
