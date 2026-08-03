"""Ownerdan matn kutish holatlarini bitta joyda yo'naltirish.

context.user_data["await"] da (turi, ...payload) tuple saqlanadi:
- ("st_model",)                 — model nomi
- ("sched_recipients",)         — rejalashtirish: kimga (1-bosqich)
- ("sched_time", token)         — rejalashtirish: qachon (2-bosqich)
- ("sched_message", token)      — rejalashtirish: nima deb yozish (3-bosqich)
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from .commands import is_owner
from .schedule import (
    handle_schedule_message_text,
    handle_schedule_recipients_text,
    handle_schedule_time_text,
)
from .settings import handle_settings_text


async def handle_owner_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner shaxsiy chatda yozgan oddiy matn — kutish holatiga qarab yo'naltiriladi."""
    if not is_owner(update) or update.message is None:
        return

    state = context.user_data.pop("await", None)
    if state is None:
        return  # hech narsa kutilmayapti

    kind = state[0]
    if kind.startswith("st_"):
        await handle_settings_text(update, context, state)
    elif kind == "sched_recipients":
        await handle_schedule_recipients_text(update, context, state)
    elif kind == "sched_time":
        await handle_schedule_time_text(update, context, state)
    elif kind == "sched_message":
        await handle_schedule_message_text(update, context, state)
