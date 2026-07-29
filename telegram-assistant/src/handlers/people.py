"""Odamlar boshqaruvi: whitelist / blacklist / notanishlar, qidiruv."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..database import repo
from ..utils import keyboards
from ..utils.keyboards import LEVEL_EMOJI, LEVEL_NAME
from .commands import guard, is_owner

MENU_TITLE = "👥 Odamlar\n\nQidiruv: /people @username"


def _person_text(person) -> str:
    username = f"@{person.username}" if person.username else "username yo'q"
    last = person.last_message_at.strftime("%d.%m.%Y %H:%M") if person.last_message_at else "—"
    return (
        f"{LEVEL_EMOJI[person.level]} {person.full_name or person.id}\n"
        f"Username: {username}\n"
        f"ID: {person.id}\n"
        f"Daraja: {LEVEL_NAME[person.level]}\n"
        f"Xabarlar soni: {person.message_count}\n"
        f"Oxirgi xabar: {last}"
    )


async def cmd_people(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    # /people @username — qidiruv
    if context.args:
        person = await repo.find_by_username(context.args[0])
        if person is None:
            await update.message.reply_text("Bunday odam topilmadi.")
            return
        await update.message.reply_text(
            _person_text(person), reply_markup=keyboards.person_view(person)
        )
        return
    counts = await repo.count_by_level()
    await update.message.reply_text(MENU_TITLE, reply_markup=keyboards.people_menu(counts))


async def handle_people_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """pp:* tugmalari."""
    query = update.callback_query
    if query is None or not is_owner(update):
        if query:
            await query.answer("Ruxsat yo'q")
        return
    await query.answer()

    parts = query.data.split(":")
    action = parts[1]

    if action == "menu":
        counts = await repo.count_by_level()
        await query.edit_message_text(MENU_TITLE, reply_markup=keyboards.people_menu(counts))

    elif action == "list":
        level = parts[2]
        people = await repo.people_by_level(level)
        title = f"{LEVEL_EMOJI[level]} {LEVEL_NAME[level]} ({len(people)})"
        if not people:
            title += "\n\nRo'yxat bo'sh."
        await query.edit_message_text(title, reply_markup=keyboards.people_list(people))

    elif action == "view":
        person = await repo.get_person(int(parts[2]))
        if person is None:
            return
        await query.edit_message_text(
            _person_text(person), reply_markup=keyboards.person_view(person)
        )

    elif action == "set":
        user_id, level = int(parts[2]), parts[3]
        await repo.set_level(user_id, level)
        person = await repo.get_person(user_id)
        if person:
            await query.edit_message_text(
                f"✅ Daraja o'zgartirildi.\n\n{_person_text(person)}",
                reply_markup=keyboards.person_view(person),
            )
