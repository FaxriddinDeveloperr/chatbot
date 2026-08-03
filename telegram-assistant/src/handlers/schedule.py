"""Rejalashtirilgan xabarlar: /schedule (bosqichma-bosqich + bitta xabar) va /scheduled.

Ikki yo'l bilan ishlaydi:
1. **Bitta xabarda hammasi** — "Bahodirga va Abdulvahob akaga soat 10:00da: Salom..."
   kabi yozsangiz, avval Gemini bilan tez ajratishga harakat qilinadi.
2. **Bosqichma-bosqich (kafolatlangan)** — agar (1) ishlamasa (AI band/kvota
   tugagan) yoki shunchaki ism/username yozsangiz, 3 ta savol beriladi:
   kimga -> qachon -> nima deb yozish. Bu yo'l hech qanday AI'ga tayanmaydi,
   shuning uchun har doim 100% ishlaydi.

Ism qidiruvi imlo xatolariga chidamli (masalan "Abdulvahhob" — "Abdulvahob"),
lekin baribir topilmasa — bosqichma-bosqich rejimga muammosiz qaytiladi.

MUHIM CHEKLOV: bot faqat avvaldan Business orqali sizga yozgan odamlarga
xabar yubora oladi — Telegram bot hali suhbat boshlanmagan foydalanuvchiga
xabar yozishga ruxsat bermaydi.
"""

from __future__ import annotations

import re
import uuid

from telegram import Message, Update
from telegram.ext import ContextTypes

from ..database import repo
from ..database.models import Person, SCHED_CANCELLED
from ..services import scheduler
from ..services.llm import LLMError
from .commands import guard, is_owner
from ..utils import keyboards

_PROMPT_RECIPIENTS = (
    "📅 Xabar rejalashtiramiz.\n\n"
    "Hammasini bitta xabarda yozsangiz ham bo'ladi:\n"
    "\"Bahodirga va Abdulvahob akaga soat 10:00da: Salom, band edim, "
    "ertaga boraman\"\n\n"
    "Yoki shunchaki kimga ekanini yozing (ism yoki @username) — qachon va "
    "nima deb yozishni keyin alohida so'rayman:\n\"Bahodir, @aziza_k\"\n\n"
    "⚠️ Faqat avval sizga Business orqali yozgan odamlarga yubora olaman."
)
_PROMPT_TIME = (
    "🕐 Qachon yuborilsin?\n\n"
    "Masalan: 14:00 | bugun 18:30 | ertaga 09:00 | 05.08 14:00 | "
    "30 daqiqadan keyin"
)
_PROMPT_MESSAGE = "💬 Nima deb yozay? Faqat xabar matnini yuboring."

# Owner butun so'zlamani (vaqt+matn bilan) yuborganini aniqlash uchun —
# AI orqali bitta xabarda tahlil qilishga urinish kerakligini bildiradi.
_LOOKS_LIKE_FULL_REQUEST = re.compile(r":|\d{1,2}[:.]\d{2}|\bsoat\b", re.IGNORECASE)


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    context.user_data["await"] = ("sched_recipients",)
    await update.message.reply_text(_PROMPT_RECIPIENTS)


def _scheduled_list_text(items: list) -> str:
    lines = ["📅 Rejalashtirilgan xabarlar:\n"]
    for item in items:
        local = item.send_at + scheduler.TASHKENT_OFFSET
        lines.append(
            f"• {item.person_name} — {local.strftime('%d.%m %H:%M')}\n  \"{item.text[:60]}\""
        )
    return "\n".join(lines)


async def cmd_scheduled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    items = await repo.pending_scheduled_messages()
    if not items:
        await update.message.reply_text("📅 Rejalashtirilgan xabarlar yo'q.")
        return
    await update.message.reply_text(
        _scheduled_list_text(items), reply_markup=keyboards.scheduled_list(items)
    )


async def _send(replyable, text: str, reply_markup=None) -> None:
    if isinstance(replyable, Message):
        await replyable.reply_text(text, reply_markup=reply_markup)
    else:
        await replyable.edit_message_text(text, reply_markup=reply_markup)


def _confirm_text(draft: dict) -> str:
    names = ", ".join(v[1] for v in draft["resolved"].values())
    return (
        "📅 Rejalashtirilgan xabar:\n\n"
        f"👤 Kimga: {names}\n"
        f"🕐 Qachon: {draft['send_at_display']}\n"
        f"💬 Matn: \"{draft['message']}\"\n\n"
        "Tasdiqlaysizmi?"
    )


async def _advance(token: str, context: ContextTypes.DEFAULT_TYPE, replyable) -> None:
    """Draftda hali nima yetishmasa — o'shani so'raydi; hammasi tayyor bo'lsa tasdiq."""
    draft = context.bot_data["sched_drafts"][token]

    if draft["ambiguous_queue"]:
        name = draft["ambiguous_queue"][0]
        candidates = draft["candidates_by_name"][name]
        text = f"🤔 \"{name}\" nomiga bir nechta odam mos keldi. Kimni nazarda tutyapsiz?"
        await _send(replyable, text, keyboards.schedule_pick(token, candidates))
    elif draft["send_at_utc"] is None:
        context.user_data["await"] = ("sched_time", token)
        await _send(replyable, _PROMPT_TIME)
    elif draft["message"] is None:
        context.user_data["await"] = ("sched_message", token)
        await _send(replyable, _PROMPT_MESSAGE)
    else:
        await _send(replyable, _confirm_text(draft), keyboards.schedule_confirm(token))


async def _resolve_recipients(names: list[str]) -> tuple[dict, dict, list]:
    """Har bir ismni bazadagi kontaktlar bilan solishtiradi (imlo xatolariga chidamli).

    Qaytaradi: (resolved {ism: (id, ko'rinadigan_nom)}, ambiguous {ism: [Person]}, not_found [ism]).
    """
    resolved: dict[str, tuple[int, str]] = {}
    ambiguous: dict[str, list[Person]] = {}
    not_found: list[str] = []
    for name in names:
        if name.startswith("@"):
            person = await repo.find_by_username(name)
            matches = [person] if person else []
        else:
            matches = await repo.find_people_by_name(name)

        if len(matches) == 1:
            p = matches[0]
            resolved[name] = (p.id, p.full_name or p.username or str(p.id))
        elif len(matches) == 0:
            not_found.append(name)
        else:
            ambiguous[name] = matches
    return resolved, ambiguous, not_found


def _new_draft(resolved: dict, ambiguous: dict, message: str | None, send_at_utc, send_at_display) -> dict:
    return {
        "resolved": resolved,
        "ambiguous_queue": list(ambiguous.keys()),
        "candidates_by_name": ambiguous,
        "message": message,
        "send_at_utc": send_at_utc,
        "send_at_display": send_at_display,
    }


async def _report_not_found(update: Update, not_found: list[str], show_plain_hint: bool) -> None:
    known = await repo.all_people(15)
    known_text = ", ".join(p.full_name or p.username or str(p.id) for p in known)
    hint = ""
    if show_plain_hint:
        hint = (
            "\n\n💡 Bu bosqichda FAQAT ism yoki @username yozing — vaqt va "
            "xabar matnini ALOHIDA, keyingi savollarda so'rayman."
        )
    await update.message.reply_text(
        f"❌ Topilmadi: {', '.join(not_found)}\n\n"
        f"Bilingan odamlar: {known_text or 'hali hech kim yo‘q'}"
        f"{hint}\n\n"
        "Qaytadan yozing (ism yoki @username):"
    )


async def handle_schedule_recipients_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: tuple
) -> bool:
    text = update.message.text

    if _LOOKS_LIKE_FULL_REQUEST.search(text):
        try:
            parse = await scheduler.parse_schedule_text(text)
        except LLMError:
            parse = None

        if parse is not None and parse.understood:
            resolved, ambiguous, not_found = await _resolve_recipients(parse.recipients)
            if not_found:
                context.user_data["await"] = ("sched_recipients",)
                await _report_not_found(update, not_found, show_plain_hint=False)
                return True
            token = uuid.uuid4().hex[:10]
            context.bot_data.setdefault("sched_drafts", {})[token] = _new_draft(
                resolved,
                ambiguous,
                parse.message,
                scheduler.to_utc(parse.send_at_local),
                parse.send_at_local.strftime("%d.%m.%Y %H:%M"),
            )
            await _advance(token, context, update.message)
            return True

        # AI band yoki tushunolmadi — bosqichma-bosqich rejimga qaytamiz
        context.user_data["await"] = ("sched_recipients",)
        await update.message.reply_text(
            "🤖 Hozir avtomatik tahlil qila olmadim (band yoki tushunarsiz "
            "chiqdi). Keling, qadam-baqadam davom etamiz.\n\n"
            "1️⃣ Hozircha FAQAT kimga ekanini yozing — ism yoki @username:"
        )
        return True

    names = scheduler.split_recipients(text)
    if not names:
        context.user_data["await"] = ("sched_recipients",)
        await update.message.reply_text("Iltimos, kamida bitta ism yoki @username yozing.")
        return True

    resolved, ambiguous, not_found = await _resolve_recipients(names)
    if not_found:
        context.user_data["await"] = ("sched_recipients",)
        await _report_not_found(update, not_found, show_plain_hint=False)
        return True

    token = uuid.uuid4().hex[:10]
    context.bot_data.setdefault("sched_drafts", {})[token] = _new_draft(
        resolved, ambiguous, None, None, None
    )
    await _advance(token, context, update.message)
    return True


async def handle_schedule_time_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: tuple
) -> bool:
    token = state[1]
    draft = context.bot_data.get("sched_drafts", {}).get(token)
    if draft is None:
        await update.message.reply_text("Bu so'rov eskirgan. /schedule bilan qaytadan boshlang.")
        return True

    send_at_local = scheduler.parse_time_text(update.message.text, scheduler.local_now())
    if send_at_local is None:
        context.user_data["await"] = ("sched_time", token)
        await update.message.reply_text(f"Tushunmadim 🤔\n\n{_PROMPT_TIME}")
        return True

    draft["send_at_utc"] = scheduler.to_utc(send_at_local)
    draft["send_at_display"] = send_at_local.strftime("%d.%m.%Y %H:%M")
    await _advance(token, context, update.message)
    return True


async def handle_schedule_message_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: tuple
) -> bool:
    token = state[1]
    draft = context.bot_data.get("sched_drafts", {}).get(token)
    if draft is None:
        await update.message.reply_text("Bu so'rov eskirgan. /schedule bilan qaytadan boshlang.")
        return True

    draft["message"] = update.message.text
    await _advance(token, context, update.message)
    return True


async def handle_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """sch:* tugmalari."""
    query = update.callback_query
    if query is None or not is_owner(update):
        if query:
            await query.answer("Ruxsat yo'q")
        return
    await query.answer()

    parts = query.data.split(":")
    action = parts[1]
    drafts = context.bot_data.setdefault("sched_drafts", {})

    if action == "start":
        context.user_data["await"] = ("sched_recipients",)
        await query.edit_message_text(_PROMPT_RECIPIENTS)

    elif action == "list":
        items = await repo.pending_scheduled_messages()
        if items:
            await query.edit_message_text(
                _scheduled_list_text(items), reply_markup=keyboards.scheduled_list(items)
            )
        else:
            await query.edit_message_text(
                "📅 Rejalashtirilgan xabarlar yo'q.", reply_markup=keyboards.main_menu()
            )

    elif action == "pick":
        token, person_id = parts[2], int(parts[3])
        draft = drafts.get(token)
        if draft is None:
            await query.edit_message_text("Bu so'rov eskirgan.")
            return
        name = draft["ambiguous_queue"].pop(0)
        candidates = draft["candidates_by_name"].pop(name)
        person = next((p for p in candidates if p.id == person_id), None)
        if person is not None:
            draft["resolved"][name] = (
                person.id,
                person.full_name or person.username or str(person.id),
            )
        await _advance(token, context, query)

    elif action == "confirm":
        token = parts[2]
        draft = drafts.pop(token, None)
        if draft is None:
            await query.edit_message_text("Bu so'rov eskirgan.")
            return
        for person_id, person_name in draft["resolved"].values():
            created = await repo.create_scheduled_message(
                person_id, person_name, draft["message"], draft["send_at_utc"]
            )
            scheduler.register_job(context, created.id, draft["send_at_utc"])
        names = ", ".join(v[1] for v in draft["resolved"].values())
        await query.edit_message_text(
            f"✅ Rejalashtirildi — {names}\n"
            f"🕐 {draft['send_at_display']}\n"
            f"💬 \"{draft['message']}\""
        )

    elif action == "cancel":
        drafts.pop(parts[2], None)
        await query.edit_message_text("❌ Bekor qilindi.")

    elif action == "del":
        scheduled_id = int(parts[2])
        await repo.set_scheduled_status(scheduled_id, SCHED_CANCELLED)
        if context.job_queue:
            for job in context.job_queue.get_jobs_by_name(f"sched_{scheduled_id}"):
                job.schedule_removal()
        items = await repo.pending_scheduled_messages()
        if items:
            await query.edit_message_text(
                _scheduled_list_text(items), reply_markup=keyboards.scheduled_list(items)
            )
        else:
            await query.edit_message_text(
                "📅 Rejalashtirilgan xabarlar yo'q.", reply_markup=keyboards.main_menu()
            )
