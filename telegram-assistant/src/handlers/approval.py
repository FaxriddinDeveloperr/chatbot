"""Tasdiqlash oqimi: UNKNOWN odamlarga javob owner ruxsati bilan yuboriladi.

Tasdiq so'rovlari xotirada (bot_data) saqlanadi va 1 soatdan keyin
JobQueue orqali avtomatik bekor qilinadi.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ..config import config
from ..database import repo
from ..database.models import (
    LEVEL_WHITELIST,
    STATUS_APPROVED,
    STATUS_EDITED,
    STATUS_EXPIRED,
    STATUS_REJECTED,
)
from ..services.llm import LLMError, generate_reply
from ..services.prompt import build_system_prompt
from ..services.store import store
from ..utils.keyboards import approval_kb
from ..utils.logger import report_error

logger = logging.getLogger(__name__)

APPROVAL_TTL = 3600  # 1 soat


def _approvals(context: ContextTypes.DEFAULT_TYPE) -> dict[str, dict[str, Any]]:
    return context.bot_data.setdefault("approvals", {})


def _render_text(data: dict[str, Any]) -> str:
    username = f"@{data['username']}" if data.get("username") else "username yo'q"
    return (
        f"🔔 Yangi xabar — {username} ({data['person_name']})\n\n"
        f"💬 Kelgan xabar:\n\"{data['incoming']}\"\n\n"
        f"🤖 Tayyorlangan javob:\n\"{data['reply']}\""
    )


async def create_approval(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    bconn_id: str,
    chat_id: int,
    user_id: int,
    username: str | None,
    person_name: str,
    incoming: str,
    reply: str,
    lang: str,
    voice_hint: bool,
) -> None:
    """Ownerga tasdiq so'rovini yuboradi va 1 soatlik muddat qo'yadi."""
    approval_id = uuid.uuid4().hex[:12]
    data: dict[str, Any] = {
        "bconn_id": bconn_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "person_name": person_name,
        "incoming": incoming,
        "reply": reply,
        "lang": lang,
        "voice_hint": voice_hint,
        "owner_message_id": None,
    }

    sent = await context.bot.send_message(
        chat_id=config.owner_id,
        text=_render_text(data),
        reply_markup=approval_kb(approval_id),
    )
    data["owner_message_id"] = sent.message_id
    _approvals(context)[approval_id] = data

    if context.job_queue:
        context.job_queue.run_once(
            _expire_job, when=APPROVAL_TTL, data=approval_id, name=f"ap_{approval_id}"
        )


async def _expire_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """1 soat o'tdi — eskirgan javob yuborilmasin."""
    approval_id = str(context.job.data)
    data = _approvals(context).pop(approval_id, None)
    if data is None:
        return
    await repo.log_response(
        data["chat_id"], data["user_id"], data["person_name"],
        data["incoming"], data["reply"], STATUS_EXPIRED,
    )
    try:
        await context.bot.edit_message_text(
            chat_id=config.owner_id,
            message_id=data["owner_message_id"],
            text=_render_text(data) + "\n\n⌛ Muddati o'tdi — yuborilmadi.",
        )
    except Exception:  # noqa: BLE001
        pass


def _cancel_expiry(context: ContextTypes.DEFAULT_TYPE, approval_id: str) -> None:
    if context.job_queue:
        for job in context.job_queue.get_jobs_by_name(f"ap_{approval_id}"):
            job.schedule_removal()


async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """✅ / ✏️ / 🔄 / ❌ / ⭐ tugmalari."""
    query = update.callback_query
    if query is None or update.effective_user is None:
        return
    if update.effective_user.id != config.owner_id:
        await query.answer("Ruxsat yo'q")
        return

    _, action, approval_id = query.data.split(":", 2)
    approvals = _approvals(context)
    data = approvals.get(approval_id)
    if data is None:
        await query.answer("Bu so'rov eskirgan yoki yakunlangan")
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:  # noqa: BLE001
            pass
        return

    from .business import deliver_reply  # aylanma importni oldini olish uchun shu yerda

    if action == "send":
        await query.answer("Yuborilmoqda...")
        approvals.pop(approval_id, None)
        _cancel_expiry(context, approval_id)
        try:
            await deliver_reply(
                context,
                bconn_id=data["bconn_id"],
                chat_id=data["chat_id"],
                user_id=data["user_id"],
                person_name=data["person_name"],
                incoming=data["incoming"],
                reply=data["reply"],
                lang=data["lang"],
                voice_hint=data["voice_hint"],
                status=STATUS_APPROVED,
            )
        except Exception as exc:  # noqa: BLE001
            await report_error(context, f"Tasdiqlangan javobni yuborib bo'lmadi: {exc}")
            return
        await query.edit_message_text(_render_text(data) + "\n\n✅ Yuborildi.")

    elif action == "edit":
        context.user_data["await"] = ("ap_edit", approval_id)
        await query.answer()
        await context.bot.send_message(
            chat_id=config.owner_id,
            text="✏️ Yangi javob matnini yuboring (o'sha matn odamga yuboriladi):",
        )

    elif action == "rew":
        await query.answer("Qayta yozilmoqda...")
        try:
            system_prompt = await build_system_prompt()
            depth = await store.get_int("context_depth", 20)
            history = await repo.get_history(data["chat_id"], depth)
            lang, reply = await generate_reply(system_prompt, history, rewrite=True)
        except LLMError as exc:
            await report_error(context, f"Qayta yozib bo'lmadi: {exc}")
            return
        data["reply"], data["lang"] = reply, lang
        await query.edit_message_text(
            _render_text(data), reply_markup=approval_kb(approval_id)
        )

    elif action == "cancel":
        approvals.pop(approval_id, None)
        _cancel_expiry(context, approval_id)
        await repo.log_response(
            data["chat_id"], data["user_id"], data["person_name"],
            data["incoming"], data["reply"], STATUS_REJECTED,
        )
        await query.answer("Bekor qilindi")
        await query.edit_message_text(_render_text(data) + "\n\n❌ Bekor qilindi.")

    elif action == "wl":
        await repo.set_level(data["user_id"], LEVEL_WHITELIST)
        await query.answer("⭐ Whitelist'ga qo'shildi — keyingi safar avtomatik javob oladi")


async def handle_approval_edit_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, approval_id: str
) -> bool:
    """Owner tahrirlagan matnni yuborish. True — muvaffaqiyatli qayta ishlandi."""
    data = _approvals(context).pop(approval_id, None)
    if data is None:
        await update.message.reply_text("Bu so'rov allaqachon eskirgan.")
        return True
    _cancel_expiry(context, approval_id)

    from .business import deliver_reply

    new_reply = update.message.text
    try:
        await deliver_reply(
            context,
            bconn_id=data["bconn_id"],
            chat_id=data["chat_id"],
            user_id=data["user_id"],
            person_name=data["person_name"],
            incoming=data["incoming"],
            reply=new_reply,
            lang=data["lang"],
            voice_hint=data["voice_hint"],
            status=STATUS_EDITED,
        )
    except Exception as exc:  # noqa: BLE001
        await report_error(context, f"Tahrirlangan javobni yuborib bo'lmadi: {exc}")
        return True

    try:
        await context.bot.edit_message_text(
            chat_id=config.owner_id,
            message_id=data["owner_message_id"],
            text=_render_text({**data, "reply": new_reply}) + "\n\n✏️ Tahrirlangan holda yuborildi.",
        )
    except Exception:  # noqa: BLE001
        pass
    await update.message.reply_text("✅ Yuborildi.")
    return True
