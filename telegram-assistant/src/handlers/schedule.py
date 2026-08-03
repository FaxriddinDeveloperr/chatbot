"""Rejalashtirilgan xabarlar: /schedule (yangi so'rov) va /scheduled (ro'yxat).

Owner erkin matnda "Kimga, qachon, nima" deb yozadi (masalan: "Bahodirga
bugun soat 14:00da: Salom, bandman, ertaga ko'rishamiz") — Gemini buni
tahlil qiladi, ism(lar) mavjud "odamlar" ro'yxati bilan solishtiriladi,
bir nechta mos kelsa tanlash so'raladi, so'ng tasdiqdan keyin JobQueue'ga
qo'yiladi.

MUHIM CHEKLOV: bot faqat avvaldan Business orqali yozgan (`/people`
ro'yxatidagi) odamlarga xabar yubora oladi — Telegram bot hali suhbat
boshlanmagan foydalanuvchiga xabar yozishga ruxsat bermaydi.
"""

from __future__ import annotations

import uuid

from telegram import Message, Update
from telegram.ext import ContextTypes

from ..database import repo
from ..database.models import Person, SCHED_CANCELLED
from ..services import scheduler
from ..services.llm import LLMError
from ..utils import keyboards
from ..utils.logger import report_error
from .commands import guard, is_owner


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    context.user_data["await"] = ("sched_input",)
    await update.message.reply_text(
        "📅 Kimga, qachon va nima deb yozishni BITTA xabarda yuboring.\n\n"
        "Masalan:\n"
        "\"Bahodirga bugun soat 14:00da: Salom, hozir bandman, ertaga ko'rishamiz\"\n\n"
        "Bir nechta odamga:\n"
        "\"Bahodir va Azizaga ertaga soat 9:00da: Yig'ilish bekor qilindi\"\n\n"
        "⚠️ Faqat avval sizga yozgan odamlarga yubora olaman (/people ro'yxati)."
    )


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


async def _advance_draft(token: str, context: ContextTypes.DEFAULT_TYPE, replyable) -> None:
    """Navbatdagi noaniq ismni so'raydi yoki (hammasi hal bo'lsa) tasdiqni ko'rsatadi."""
    draft = context.bot_data["sched_drafts"][token]

    if draft["ambiguous_queue"]:
        name = draft["ambiguous_queue"][0]
        candidates = draft["candidates_by_name"][name]
        text = f"🤔 \"{name}\" nomiga bir nechta odam mos keldi. Kimni nazarda tutyapsiz?"
        markup = keyboards.schedule_pick(token, candidates)
    else:
        names = ", ".join(v[1] for v in draft["resolved"].values())
        text = (
            "📅 Rejalashtirilgan xabar:\n\n"
            f"👤 Kimga: {names}\n"
            f"🕐 Qachon: {draft['send_at_display']}\n"
            f"💬 Matn: \"{draft['message']}\"\n\n"
            "Tasdiqlaysizmi?"
        )
        markup = keyboards.schedule_confirm(token)

    if isinstance(replyable, Message):
        await replyable.reply_text(text, reply_markup=markup)
    else:
        await replyable.edit_message_text(text, reply_markup=markup)


async def handle_schedule_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: tuple
) -> bool:
    """Owner'ning erkin matnli rejalashtirish so'rovini tahlil qiladi."""
    text = update.message.text

    try:
        parse = await scheduler.parse_schedule_text(text)
    except LLMError as exc:
        await report_error(context, f"Rejalashtirish tahlili ishlamadi: {exc}")
        await update.message.reply_text(
            "⚠️ Hozir tahlil qila olmadim, birozdan keyin qayta urinib ko'ring."
        )
        return True

    if not parse.understood:
        context.user_data["await"] = ("sched_input",)
        await update.message.reply_text(
            "Tushunmadim 🤔 Masalan shunday yozing:\n"
            "\"Bahodirga bugun soat 14:00da: Salom, hozir bandman, ertaga ko'rishamiz\""
        )
        return True

    resolved: dict[str, tuple[int, str]] = {}
    ambiguous: dict[str, list[Person]] = {}
    not_found: list[str] = []
    for name in parse.recipients:
        matches = await repo.find_people_by_name(name)
        if len(matches) == 1:
            p = matches[0]
            resolved[name] = (p.id, p.full_name or p.username or str(p.id))
        elif len(matches) == 0:
            not_found.append(name)
        else:
            ambiguous[name] = matches

    if not_found:
        known = await repo.all_people(15)
        known_text = ", ".join(p.full_name or p.username or str(p.id) for p in known)
        await update.message.reply_text(
            f"❌ Quyidagi odam(lar) topilmadi: {', '.join(not_found)}\n\n"
            f"Bilingan odamlar: {known_text or 'hali hech kim yo‘q'}\n\n"
            "Ism to'g'ri yozilganini tekshirib, /schedule bilan qayta urinib ko'ring."
        )
        return True

    token = uuid.uuid4().hex[:10]
    context.bot_data.setdefault("sched_drafts", {})[token] = {
        "resolved": resolved,
        "ambiguous_queue": list(ambiguous.keys()),
        "candidates_by_name": ambiguous,
        "message": parse.message,
        "send_at_utc": scheduler.to_utc(parse.send_at_local),
        "send_at_display": parse.send_at_local.strftime("%d.%m.%Y %H:%M"),
    }
    await _advance_draft(token, context, update.message)
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
        context.user_data["await"] = ("sched_input",)
        await query.edit_message_text(
            "📅 Kimga, qachon va nima deb yozishni BITTA xabarda yuboring.\n\n"
            "Masalan:\n"
            "\"Bahodirga bugun soat 14:00da: Salom, hozir bandman, ertaga ko'rishamiz\"\n\n"
            "Bir nechta odamga:\n"
            "\"Bahodir va Azizaga ertaga soat 9:00da: Yig'ilish bekor qilindi\"\n\n"
            "⚠️ Faqat avval sizga yozgan odamlarga yubora olaman (/people ro'yxati)."
        )

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
        await _advance_draft(token, context, query)

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
