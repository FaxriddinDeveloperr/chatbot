"""Rejalashtirilgan xabarlar: tabiiy tildagi so'rovni tahlil qilish va yuborish.

Owner "Bahodirga bugun soat 14:00da: Salom, band edim" kabi erkin matn
yozadi — Gemini buni (kim, qachon, nima) ga ajratadi. Yuborish vaqti
JobQueue orqali rejalashtiriladi; bot qayta ishga tushganda hali
yuborilmagan xabarlar bazadan o'qib qayta rejalashtiriladi (`reschedule_all_pending`).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from google.genai import types
from telegram.ext import Application, ContextTypes

from ..config import config
from ..database import repo
from ..database.models import SCHED_SENT, SCHED_FAILED, utcnow
from .llm import LLMError, current_model, get_client
from .store import store

logger = logging.getLogger(__name__)

# Toshkent doim UTC+5, yozgi vaqtga o'tish yo'q — shuning uchun sobit offset yetarli.
TASHKENT_OFFSET = timedelta(hours=5)


def local_now() -> datetime:
    return utcnow() + TASHKENT_OFFSET


def to_utc(local_dt: datetime) -> datetime:
    return local_dt - TASHKENT_OFFSET


@dataclass
class ScheduleParse:
    understood: bool
    recipients: list[str] = field(default_factory=list)
    send_at_local: datetime | None = None
    message: str = ""


async def parse_schedule_text(text: str) -> ScheduleParse:
    """Owner'ning erkin matnini (kim, qachon, nima) ga ajratadi."""
    now = local_now()
    system_prompt = (
        "Sen shaxsiy yordamchisan. Owner senga xabarni KIMGA, QACHON va NIMA deb "
        "yozish kerakligini tabiiy tilda aytadi — imlo xatolari, so'zlashuv uslubi "
        "bo'lishi mumkin (masalan 'soat' o'rniga 'sa', 'hozir' o'rniga 'hodir'). "
        "Buni to'g'ri tushunib JSON qilib qaytar.\n\n"
        f"Hozirgi mahalliy sana-vaqt (Toshkent, UTC+5): "
        f"{now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')})\n\n"
        "QOIDALAR:\n"
        "- recipients: qabul qiluvchilarning ismlari ro'yxati (masalan "
        '["Bahodir", "Aziza"]). Agar bittagina bo\'lsa ham ro\'yxat qaytar.\n'
        "- send_at: xabar yuborilishi kerak bo'lgan mahalliy sana-vaqt, "
        "ISO formatda \"YYYY-MM-DDTHH:MM:SS\". Agar faqat vaqt aytilgan bo'lsa "
        "(sana yo'q) va bu vaqt bugun uchun allaqachon o'tib ketgan bo'lsa — "
        "ertangi kunga o'tkaz. Agar vaqt umuman aytilmagan bo'lsa — hozirdan "
        "5 daqiqa keyin.\n"
        "- message: owner talab qilgan, qabul qiluvchiga yuborilishi kerak "
        "bo'lgan xabar matni (faqat shu matn, boshqa hech narsa qo'shma).\n"
        "- understood: agar kimga va nima yozish kerakligini aniq tushungan "
        "bo'lsang true, aks holda false."
    )

    try:
        response = await get_client().aio.models.generate_content(
            model=await current_model(),
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "understood": {"type": "BOOLEAN"},
                        "recipients": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "send_at": {"type": "STRING"},
                        "message": {"type": "STRING"},
                    },
                    "required": ["understood", "recipients", "send_at", "message"],
                },
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"Rejalashtirish so'rovini tahlil qilib bo'lmadi: {exc}") from exc

    try:
        data = json.loads((response.text or "").strip())
    except json.JSONDecodeError:
        return ScheduleParse(understood=False)

    if not data.get("understood") or not data.get("recipients"):
        return ScheduleParse(understood=False)

    try:
        send_at_local = datetime.fromisoformat(str(data["send_at"]))
    except ValueError:
        return ScheduleParse(understood=False)

    return ScheduleParse(
        understood=True,
        recipients=[str(r).strip() for r in data["recipients"] if str(r).strip()],
        send_at_local=send_at_local,
        message=str(data.get("message", "")).strip(),
    )


def register_job(app_or_context, scheduled_id: int, send_at_utc: datetime) -> None:
    """JobQueue'ga yuborish vazifasini qo'shadi (Application yoki context orqali)."""
    delay = max((send_at_utc - utcnow()).total_seconds(), 0)
    job_queue = app_or_context.job_queue
    job_queue.run_once(send_due_message, when=delay, data=scheduled_id, name=f"sched_{scheduled_id}")


async def send_due_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Rejalashtirilgan xabarni yuborish vaqti keldi."""
    from ..utils.logger import report_error  # aylanma importni oldini olish uchun shu yerda

    scheduled_id = int(context.job.data)
    msg = await repo.get_scheduled_message(scheduled_id)
    if msg is None or msg.status != "pending":
        return

    bconn_id = await store.get("business_connection_id", "")
    if not bconn_id:
        await repo.set_scheduled_status(scheduled_id, SCHED_FAILED)
        await report_error(
            context,
            f"Rejalashtirilgan xabar yuborilmadi — Business ulanish yo'q "
            f"({msg.person_name}): \"{msg.text}\"",
        )
        return

    try:
        await context.bot.send_message(
            chat_id=msg.person_id, text=msg.text, business_connection_id=bconn_id
        )
    except Exception as exc:  # noqa: BLE001
        await repo.set_scheduled_status(scheduled_id, SCHED_FAILED)
        await report_error(
            context, f"Rejalashtirilgan xabarni yuborib bo'lmadi ({msg.person_name}): {exc}"
        )
        return

    await repo.set_scheduled_status(scheduled_id, SCHED_SENT)
    await repo.save_message(msg.person_id, "assistant", msg.text)
    await repo.log_response(msg.person_id, msg.person_id, msg.person_name, "", msg.text, "auto")
    try:
        await context.bot.send_message(
            chat_id=config.owner_id,
            text=f"📤 Rejalashtirilgan xabar yuborildi — {msg.person_name}:\n\"{msg.text}\"",
        )
    except Exception:  # noqa: BLE001
        pass


async def reschedule_all_pending(app: Application) -> None:
    """Bot qayta ishga tushganda — hali yuborilmagan xabarlarni qayta rejalashtiradi."""
    pending = await repo.pending_scheduled_messages()
    for msg in pending:
        register_job(app, msg.id, msg.send_at)
    if pending:
        logger.info("Qayta rejalashtirildi: %d ta xabar", len(pending))
