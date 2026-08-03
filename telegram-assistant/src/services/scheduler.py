"""Rejalashtirilgan xabarlar: vaqt/qabul qiluvchi tahlili va yuborish.

Hech qanday AI ishlatilmaydi — kim-qachon-nima bosqichma-bosqich (wizard)
so'raladi va oddiy qoidalar bilan tahlil qilinadi, shuning uchun Gemini
kvotasi tugab qolsa ham bu funksiya 100% ishlayveradi. Yuborish vaqti
JobQueue orqali rejalashtiriladi; bot qayta ishga tushganda hali
yuborilmagan xabarlar bazadan o'qib qayta rejalashtiriladi (`reschedule_all_pending`).
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timedelta

from telegram.ext import Application, ContextTypes

from ..config import config
from ..database import repo
from ..database.models import SCHED_FAILED, SCHED_SENT, utcnow
from .store import store

logger = logging.getLogger(__name__)

# Toshkent doim UTC+5, yozgi vaqtga o'tish yo'q — shuning uchun sobit offset yetarli.
TASHKENT_OFFSET = timedelta(hours=5)

_TIME_RE = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?(?!\d)")
_RELATIVE_RE = re.compile(r"(\d+)\s*(daqiqa|minut|soat)")


def local_now() -> datetime:
    return utcnow() + TASHKENT_OFFSET


def to_utc(local_dt: datetime) -> datetime:
    return local_dt - TASHKENT_OFFSET


def split_recipients(text: str) -> list[str]:
    """'Bahodir, @aziza_k va Vali' -> ['Bahodir', '@aziza_k', 'Vali']."""
    parts = re.split(r",|\bva\b|\bhamda\b|\+", text, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def parse_time_text(text: str, now_local: datetime) -> datetime | None:
    """Oddiy qoidalar bilan sana-vaqtni ajratadi (AI ishlatilmaydi).

    Qo'llab-quvvatlanadi: "14:00", "bugun 18:30", "ertaga 09:00",
    "05.08 14:00", "05.08.2026 14:00", "30 daqiqadan keyin", "2 soatdan keyin".
    """
    t = text.lower().strip()

    rel = _RELATIVE_RE.search(t)
    if rel and "keyin" in t:
        n = int(rel.group(1))
        unit = rel.group(2)
        delta = timedelta(hours=n) if unit == "soat" else timedelta(minutes=n)
        return now_local + delta

    time_match = _TIME_RE.search(t)
    if not time_match:
        return None
    hour, minute = int(time_match.group(1)), int(time_match.group(2))
    if hour > 23 or minute > 59:
        return None

    date_match = _DATE_RE.search(t)
    if date_match:
        day, month = int(date_match.group(1)), int(date_match.group(2))
        year = int(date_match.group(3)) if date_match.group(3) else now_local.year
        try:
            candidate = datetime.combine(date(year, month, day), time(hour, minute))
        except ValueError:
            return None
        if not date_match.group(3) and candidate < now_local:
            candidate = candidate.replace(year=year + 1)
        return candidate

    if "indinga" in t:
        target_day = now_local.date() + timedelta(days=2)
    elif "ertaga" in t or "erta" in t:
        target_day = now_local.date() + timedelta(days=1)
    elif "bugun" in t:
        target_day = now_local.date()
    else:
        # Faqat vaqt aytilgan — o'tib ketgan bo'lsa ertangi kunga
        target_day = now_local.date()
        candidate = datetime.combine(target_day, time(hour, minute))
        if candidate < now_local:
            target_day += timedelta(days=1)
        return datetime.combine(target_day, time(hour, minute))

    return datetime.combine(target_day, time(hour, minute))


def register_job(app_or_context, scheduled_id: int, send_at_utc: datetime) -> None:
    """JobQueue'ga yuborish vazifasini qo'shadi (Application yoki context orqali)."""
    delay = max((send_at_utc - utcnow()).total_seconds(), 0)
    job_queue = app_or_context.job_queue
    job_queue.run_once(send_due_message, when=delay, data=scheduled_id, name=f"sched_{scheduled_id}")


async def send_due_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Rejalashtirilgan xabarni yuborish vaqti keldi."""
    from ..utils.logger import humanize_send_error, report_error  # aylanma import

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
            context,
            f"Rejalashtirilgan xabarni yuborib bo'lmadi ({msg.person_name}): "
            f"{humanize_send_error(exc)}",
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
