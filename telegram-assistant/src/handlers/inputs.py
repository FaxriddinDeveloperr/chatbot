"""Ownerdan matn kutish holatlarini bitta joyda yo'naltirish.

context.user_data["await"] da (turi, ...payload) tuple saqlanadi:
- ("ap_edit", approval_id)      — tasdiq javobini tahrirlash
- ("kb_new_title",)             — yangi bo'lim nomi
- ("kb_new_content", title)     — yangi bo'lim mazmuni
- ("kb_edit", section_id)       — bo'limni tahrirlash
- ("st_model",)                 — model nomi
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from .approval import handle_approval_edit_text
from .commands import is_owner
from .knowledge import handle_kb_text
from .settings import handle_settings_text


async def handle_owner_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner shaxsiy chatda yozgan oddiy matn — kutish holatiga qarab yo'naltiriladi."""
    if not is_owner(update) or update.message is None:
        return

    state = context.user_data.pop("await", None)
    if state is None:
        return  # hech narsa kutilmayapti

    kind = state[0]
    if kind == "ap_edit":
        await handle_approval_edit_text(update, context, state[1])
    elif kind.startswith("kb_"):
        await handle_kb_text(update, context, state)
    elif kind.startswith("st_"):
        await handle_settings_text(update, context, state)
