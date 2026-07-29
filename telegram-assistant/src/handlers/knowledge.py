"""Bilim bazasi boshqaruvi: /knowledge menyusi, CRUD, tartib, yoqish/o'chirish."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..database import repo
from ..utils import keyboards
from .commands import guard, is_owner

MENU_TITLE = "📚 Bilim bazasi\n\nBo'limni tanlang:"


async def cmd_knowledge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    sections = await repo.kb_all()
    await update.message.reply_text(MENU_TITLE, reply_markup=keyboards.kb_menu(sections))


async def handle_kb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """kb:* tugmalari."""
    query = update.callback_query
    if query is None or not is_owner(update):
        if query:
            await query.answer("Ruxsat yo'q")
        return
    await query.answer()

    parts = query.data.split(":")
    action = parts[1]
    section_id = int(parts[2]) if len(parts) > 2 else None

    if action == "menu":
        sections = await repo.kb_all()
        await query.edit_message_text(MENU_TITLE, reply_markup=keyboards.kb_menu(sections))

    elif action == "view" and section_id:
        section = await repo.kb_get(section_id)
        if section is None:
            return
        status = "✅ yoqilgan" if section.is_active else "🔴 o'chirilgan"
        text = f"📄 {section.title} ({status})\n\n{section.content}"
        await query.edit_message_text(text[:4000], reply_markup=keyboards.kb_section(section))

    elif action == "edit" and section_id:
        context.user_data["await"] = ("kb_edit", section_id)
        await query.edit_message_text(
            "✏️ Yangi matnni yuboring — bo'lim mazmuni to'liq almashtiriladi:"
        )

    elif action == "toggle" and section_id:
        await repo.kb_toggle(section_id)
        section = await repo.kb_get(section_id)
        if section:
            status = "✅ yoqilgan" if section.is_active else "🔴 o'chirilgan"
            text = f"📄 {section.title} ({status})\n\n{section.content}"
            await query.edit_message_text(text[:4000], reply_markup=keyboards.kb_section(section))

    elif action == "del" and section_id:
        section = await repo.kb_get(section_id)
        if section:
            await query.edit_message_text(
                f"🗑 \"{section.title}\" bo'limini BUTUNLAY o'chirishga ishonchingiz komilmi?",
                reply_markup=keyboards.kb_delete_confirm(section_id),
            )

    elif action == "delc" and section_id:
        await repo.kb_delete(section_id)
        sections = await repo.kb_all()
        await query.edit_message_text(
            "🗑 O'chirildi.\n\n" + MENU_TITLE, reply_markup=keyboards.kb_menu(sections)
        )

    elif action == "new":
        context.user_data["await"] = ("kb_new_title",)
        await query.edit_message_text("➕ Yangi bo'lim NOMINI yuboring:")

    elif action == "order":
        sections = await repo.kb_all()
        await query.edit_message_text(
            "🔄 Tartib — ⬆️/⬇️ bilan suring:", reply_markup=keyboards.kb_order(sections)
        )

    elif action in ("up", "down") and section_id:
        await repo.kb_move(section_id, up=(action == "up"))
        sections = await repo.kb_all()
        await query.edit_message_text(
            "🔄 Tartib — ⬆️/⬇️ bilan suring:", reply_markup=keyboards.kb_order(sections)
        )


async def handle_kb_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: tuple
) -> bool:
    """Matn kiritish holatlari: yangi bo'lim nomi/matni, tahrirlash."""
    kind = state[0]
    text = update.message.text

    if kind == "kb_new_title":
        context.user_data["await"] = ("kb_new_content", text.strip()[:120])
        await update.message.reply_text("Endi bo'lim MAZMUNINI yuboring:")
        return True

    if kind == "kb_new_content":
        title = state[1]
        await repo.kb_add(title, text)
        sections = await repo.kb_all()
        await update.message.reply_text(
            f"✅ \"{title}\" bo'limi qo'shildi.", reply_markup=keyboards.kb_menu(sections)
        )
        return True

    if kind == "kb_edit":
        section_id = state[1]
        await repo.kb_update_content(section_id, text)
        section = await repo.kb_get(section_id)
        title = section.title if section else "Bo'lim"
        await update.message.reply_text(f"✅ \"{title}\" yangilandi.")
        return True

    return False
