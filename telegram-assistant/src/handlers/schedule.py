"""Rejalashtirilgan xabarlar: /schedule (bosqichma-bosqich) va /scheduled (ro'yxat).

Hech qanday AI ishlatilmaydi — 3 bosqich: (1) kimga — ism yoki @username,
bir nechta bo'lsa vergul bilan; (2) qachon — "14:00" / "bugun 18:30" /
"ertaga 09:00" / "05.08 14:00" / "30 daqiqadan keyin"; (3) nima deb yozish.
Har bir bosqichda oddiy qoidalar bilan tahlil qilinadi (services/scheduler.py),
shuning uchun Gemini kvotasi tugab qolsa ham bu funksiya 100% ishlaydi.

MUHIM CHEKLOV: bot faqat avvaldan Business orqali yozgan (`/people`
ro'yxatidagi) odamlarga xabar yubora oladi — Telegram bot hali suhbat
boshlanmagan foydalanuvchiga xabar yozishga ruxsat bermaydi.
"""

from __future__ import annotations

import re
import uuid

from telegram import Message, Update
from telegram.ext import ContextTypes

from ..database import repo
from ..database.models import Person, SCHED_CANCELLED
from ..services import scheduler
from ..utils import keyboards
from .commands import guard, is_owner

_PROMPT_RECIPIENTS = (
    "📅 Xabar rejalashtiramiz. 3 ta savol beraman — har biriga ALOHIDA xabar "
    "bilan javob bering:\n"
    "1️⃣ Kimga?  2️⃣ Qachon?  3️⃣ Nima deb yozay?\n\n"
    "1️⃣ Hozircha FAQAT kimga ekanini yozing — ism-familiya yoki @username "
    "(vaqt va matnni keyin alohida so'rayman).\n"
    "Bir nechta odamga bo'lsa, vergul bilan ajrating: \"Bahodir, @aziza_k\"\n\n"
    "⚠️ Faqat avval sizga yozgan odamlarga yubora olaman (/people ro'yxati)."
)
_PROMPT_TIME = (
    "2️⃣ Endi qachon yuborilishini yozing.\n\n"
    "Masalan: 14:00 | bugun 18:30 | ertaga 09:00 | 05.08 14:00 | "
    "30 daqiqadan keyin"
)
_PROMPT_MESSAGE = "3️⃣ Endi nima deb yozay? Faqat xabar matnini yuboring."

# "kimga" bosqichida owner butun so'zlamani (vaqt+matn bilan) yuborib
# yuborgan bo'lsa aniqlash uchun — aniqroq eslatma berish maqsadida.
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


async def _advance_recipients(token: str, context: ContextTypes.DEFAULT_TYPE, replyable) -> None:
    """Navbatdagi noaniq ismni so'raydi yoki (hammasi hal bo'lsa) vaqtni so'raydi."""
    draft = context.bot_data["sched_drafts"][token]

    if draft["ambiguous_queue"]:
        name = draft["ambiguous_queue"][0]
        candidates = draft["candidates_by_name"][name]
        text = f"🤔 \"{name}\" nomiga bir nechta odam mos keldi. Kimni nazarda tutyapsiz?"
        await _send(replyable, text, keyboards.schedule_pick(token, candidates))
    else:
        context.user_data["await"] = ("sched_time", token)
        await _send(replyable, _PROMPT_TIME)


async def _resolve_recipients(names: list[str]) -> tuple[dict, dict, list]:
    """Har bir ismni /people ro'yxati bilan solishtiradi.

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


async def handle_schedule_recipients_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: tuple
) -> bool:
    names = scheduler.split_recipients(update.message.text)
    if not names:
        context.user_data["await"] = ("sched_recipients",)
        await update.message.reply_text("Iltimos, kamida bitta ism yoki @username yozing.")
        return True

    resolved, ambiguous, not_found = await _resolve_recipients(names)

    if not_found:
        known = await repo.all_people(15)
        known_text = ", ".join(p.full_name or p.username or str(p.id) for p in known)
        context.user_data["await"] = ("sched_recipients",)
        hint = ""
        if _LOOKS_LIKE_FULL_REQUEST.search(update.message.text):
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
        return True

    token = uuid.uuid4().hex[:10]
    context.bot_data.setdefault("sched_drafts", {})[token] = {
        "resolved": resolved,
        "ambiguous_queue": list(ambiguous.keys()),
        "candidates_by_name": ambiguous,
        "message": None,
        "send_at_utc": None,
        "send_at_display": None,
    }
    await _advance_recipients(token, context, update.message)
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
    context.user_data["await"] = ("sched_message", token)
    await update.message.reply_text(_PROMPT_MESSAGE)
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
    names = ", ".join(v[1] for v in draft["resolved"].values())
    text = (
        "📅 Rejalashtirilgan xabar:\n\n"
        f"👤 Kimga: {names}\n"
        f"🕐 Qachon: {draft['send_at_display']}\n"
        f"💬 Matn: \"{draft['message']}\"\n\n"
        "Tasdiqlaysizmi?"
    )
    await update.message.reply_text(text, reply_markup=keyboards.schedule_confirm(token))
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
        await _advance_recipients(token, context, query)

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
