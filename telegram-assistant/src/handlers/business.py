"""Telegram Business xabarlarini qayta ishlash — botning yuragi.

Oqim:
1. business_message keladi
2. Owner o'zi yozgan bo'lsa — faollik belgilanadi, javob yozilmaydi (loop yo'q)
3. Blacklist / rate limit tekshiruvi
4. Ovozli xabar bo'lsa — STT orqali matnga aylantiriladi
5. Owner online bo'lsa — faqat tarixga yoziladi, javob yo'q
6. Whitelist — avtomatik javob; Unknown — ownerga tasdiq so'rovi
"""

from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ContextTypes

from ..config import config
from ..database import repo
from ..database.models import (
    LEVEL_BLACKLIST,
    LEVEL_WHITELIST,
    STATUS_AUTO,
)
from ..services import presence
from ..services.llm import LLMError, generate_reply
from ..services.prompt import build_system_prompt
from ..services.rate_limit import rate_limiter
from ..services.store import store
from ..stt import get_stt
from ..tts import get_tts
from ..utils.logger import humanize_send_error, report_error
from .approval import create_approval

logger = logging.getLogger(__name__)


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


async def deliver_reply(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    bconn_id: str,
    chat_id: int,
    user_id: int,
    person_name: str,
    incoming: str,
    reply: str,
    lang: str,
    voice_hint: bool,
    status: str,
) -> None:
    """Javobni tabiiy ko'rinishda (typing + kechikish) yuboradi va log qiladi."""
    delay_min = await store.get_int("delay_min", 3)
    delay_max = await store.get_int("delay_max", 8)

    try:
        await context.bot.send_chat_action(
            chat_id=chat_id, action=ChatAction.TYPING, business_connection_id=bconn_id
        )
    except Exception:  # noqa: BLE001 — typing muvaffaqiyatsiz bo'lsa ham davom etamiz
        pass
    await asyncio.sleep(random.uniform(delay_min, max(delay_min, delay_max)))

    voice_path: Path | None = None
    voice_enabled = await store.get_bool("voice_enabled", True)
    min_chars = await store.get_int("voice_min_chars", 300)
    tts = get_tts()
    if voice_enabled and tts.supports(lang) and (voice_hint or len(reply) > min_chars):
        voice_path = await tts.synthesize(reply, lang)

    if voice_path is not None:
        try:
            with voice_path.open("rb") as f:
                await context.bot.send_voice(
                    chat_id=chat_id, voice=f, business_connection_id=bconn_id
                )
        finally:
            voice_path.unlink(missing_ok=True)
    else:
        await context.bot.send_message(
            chat_id=chat_id, text=reply, business_connection_id=bconn_id
        )

    await repo.save_message(chat_id, "assistant", reply)
    await repo.log_response(chat_id, user_id, person_name, incoming, reply, status)


async def handle_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Har bir kelgan business xabar uchun asosiy mantiq."""
    msg = update.business_message
    if msg is None or msg.from_user is None:
        return

    # Botning o'z xabarlari business ulanish orqali shu chatga aks etib
    # qaytishi mumkin (o'z-o'ziga javob berish siklini oldini olish uchun),
    # va guruh/kanal emas — faqat shaxsiy (1-1) suhbatlar bilan ishlaymiz.
    if msg.from_user.id == context.bot.id or msg.chat.type != ChatType.PRIVATE:
        return

    bconn_id = msg.business_connection_id
    if bconn_id:
        await store.set("business_connection_id", bconn_id)

    # Owner o'zi yozgan xabar — faollik belgisi, javob berilmaydi (infinite loop yo'q)
    if msg.from_user.id == config.owner_id:
        await presence.mark_owner_activity()
        if msg.text:
            await repo.save_message(msg.chat.id, "assistant", msg.text, config.owner_id)
        return

    user = msg.from_user
    person = await repo.upsert_person(user.id, user.username, user.full_name or "")

    if person.level == LEVEL_BLACKLIST:
        return

    if not rate_limiter.allow(user.id):
        logger.info("Rate limit: %s", user.id)
        return

    # Xabar matnini olish (ovozli bo'lsa — STT)
    voice_hint = False
    text = msg.text or msg.caption
    if msg.voice is not None:
        voice_hint = True
        try:
            tg_file = await context.bot.get_file(msg.voice.file_id)
            audio = bytes(await tg_file.download_as_bytearray())
            text = await get_stt().transcribe(audio, msg.voice.mime_type or "audio/ogg")
        except LLMError as exc:
            await report_error(context, f"Ovozli xabarni tushunib bo'lmadi ({user.full_name}): {exc}")
            return
    if not text:
        return  # qo'llab-quvvatlanmaydigan kontent (rasm, stiker...)

    await repo.save_message(msg.chat.id, "user", text, user.id)

    # Owner online bo'lsa — bot jim (tarix baribir saqlanadi)
    if not await presence.owner_is_offline():
        return

    # Javob generatsiyasi
    try:
        system_prompt = await build_system_prompt()
        depth = await store.get_int("context_depth", 20)
        history = await repo.get_history(msg.chat.id, depth)
        lang, reply = await generate_reply(system_prompt, history)
    except LLMError as exc:
        await report_error(context, f"LLM javob bera olmadi ({user.full_name}): {exc}")
        return  # odamga hech narsa yuborilmaydi

    if person.level == LEVEL_WHITELIST:
        try:
            await deliver_reply(
                context,
                bconn_id=bconn_id,
                chat_id=msg.chat.id,
                user_id=user.id,
                person_name=user.full_name or str(user.id),
                incoming=text,
                reply=reply,
                lang=lang,
                voice_hint=voice_hint,
                status=STATUS_AUTO,
            )
        except Exception as exc:  # noqa: BLE001
            await report_error(
                context, f"Javob yuborishda xato ({user.full_name}): {humanize_send_error(exc)}"
            )
    else:
        # UNKNOWN — ownerdan tasdiq so'raymiz
        await create_approval(
            context,
            bconn_id=bconn_id,
            chat_id=msg.chat.id,
            user_id=user.id,
            username=user.username,
            person_name=user.full_name or str(user.id),
            incoming=text,
            reply=reply,
            lang=lang,
            voice_hint=voice_hint,
        )
