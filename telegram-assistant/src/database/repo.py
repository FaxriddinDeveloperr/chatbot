"""Baza bilan ishlash uchun barcha so'rovlar (repository qatlami)."""

from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher

from sqlalchemy import desc, func, or_, select, update

from .models import ErrorLog, Person, ResponseLog, SCHED_PENDING, ScheduledMessage, utcnow
from .session import async_session

# ---------------------------------------------------------------- People


async def upsert_person(user_id: int, username: str | None, full_name: str) -> Person:
    """Odamni topadi yoki yaratadi; nom/username va faollikni yangilaydi."""
    async with async_session() as s:
        person = await s.get(Person, user_id)
        if person is None:
            person = Person(id=user_id, username=username, full_name=full_name)
            s.add(person)
        person.username = username
        person.full_name = full_name
        person.last_message_at = utcnow()
        await s.commit()
        return person


async def find_by_username(username: str) -> Person | None:
    async with async_session() as s:
        row = await s.execute(
            select(Person).where(func.lower(Person.username) == username.lower().lstrip("@"))
        )
        return row.scalars().first()


def _word_is_close(query_word: str, target_word: str, threshold: float = 0.82) -> bool:
    if len(query_word) < 3 or len(target_word) < 3:
        return query_word == target_word
    return SequenceMatcher(None, query_word, target_word).ratio() >= threshold


def _fuzzy_matches(query: str, person: Person) -> bool:
    """Bir necha harflik imlo xatosiga chidamli taqqoslash (masalan
    'Abdulvahhob' — 'Abdulvahob'), tashqi kutubxonasiz (difflib, stdlib)."""
    q_words = query.lower().split()
    for field in (person.full_name, person.username):
        if not field:
            continue
        target_words = field.lower().replace("_", " ").split()
        if any(_word_is_close(qw, tw) for qw in q_words for tw in target_words):
            return True
    return False


async def find_people_by_name(query: str) -> list[Person]:
    """Ism yoki username bo'yicha qidiradi: avval aniq (qisman) mos kelish,
    hech narsa topilmasa — imlo xatolariga chidamli taqqoslash bilan."""
    q = query.strip().lstrip("@")
    like = f"%{q}%"
    async with async_session() as s:
        rows = await s.execute(
            select(Person).where(
                or_(Person.full_name.ilike(like), Person.username.ilike(like))
            )
        )
        exact = list(rows.scalars().all())
        if exact:
            return exact

        all_rows = list((await s.execute(select(Person))).scalars().all())

    return [p for p in all_rows if _fuzzy_matches(q, p)]


async def all_people(limit: int = 50) -> list[Person]:
    async with async_session() as s:
        rows = await s.execute(
            select(Person).order_by(desc(Person.last_message_at)).limit(limit)
        )
        return list(rows.scalars().all())


# ---------------------------------------------------------------- Logs


async def log_response(
    chat_id: int,
    user_id: int,
    person_name: str,
    incoming: str,
    reply: str,
    status: str,
) -> None:
    async with async_session() as s:
        s.add(
            ResponseLog(
                chat_id=chat_id,
                user_id=user_id,
                person_name=person_name,
                incoming=incoming[:1000],
                reply=reply[:2000],
                status=status,
            )
        )
        await s.commit()


async def recent_responses(limit: int = 10) -> list[ResponseLog]:
    async with async_session() as s:
        rows = await s.execute(select(ResponseLog).order_by(desc(ResponseLog.id)).limit(limit))
        return list(rows.scalars().all())


async def log_error(text: str) -> None:
    async with async_session() as s:
        s.add(ErrorLog(message=text[:3000]))
        await s.commit()


async def recent_errors(limit: int = 10) -> list[ErrorLog]:
    async with async_session() as s:
        rows = await s.execute(select(ErrorLog).order_by(desc(ErrorLog.id)).limit(limit))
        return list(rows.scalars().all())


# ---------------------------------------------------------------- Scheduled messages


async def create_scheduled_message(
    person_id: int, person_name: str, text: str, send_at: datetime
) -> ScheduledMessage:
    async with async_session() as s:
        msg = ScheduledMessage(
            person_id=person_id, person_name=person_name, text=text, send_at=send_at
        )
        s.add(msg)
        await s.commit()
        await s.refresh(msg)
        return msg


async def get_scheduled_message(scheduled_id: int) -> ScheduledMessage | None:
    async with async_session() as s:
        return await s.get(ScheduledMessage, scheduled_id)


async def pending_scheduled_messages() -> list[ScheduledMessage]:
    async with async_session() as s:
        rows = await s.execute(
            select(ScheduledMessage)
            .where(ScheduledMessage.status == SCHED_PENDING)
            .order_by(ScheduledMessage.send_at)
        )
        return list(rows.scalars().all())


async def set_scheduled_status(scheduled_id: int, status: str) -> None:
    async with async_session() as s:
        await s.execute(
            update(ScheduledMessage)
            .where(ScheduledMessage.id == scheduled_id)
            .values(status=status)
        )
        await s.commit()
