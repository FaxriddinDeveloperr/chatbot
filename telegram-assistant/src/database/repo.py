"""Baza bilan ishlash uchun barcha so'rovlar (repository qatlami)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, desc, func, select, update

from .models import (
    ChatMessage,
    ErrorLog,
    KnowledgeSection,
    Person,
    ResponseLog,
    utcnow,
)
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
        person.message_count += 1
        person.last_message_at = utcnow()
        await s.commit()
        return person


async def get_person(user_id: int) -> Person | None:
    async with async_session() as s:
        return await s.get(Person, user_id)


async def set_level(user_id: int, level: str) -> None:
    async with async_session() as s:
        await s.execute(update(Person).where(Person.id == user_id).values(level=level))
        await s.commit()


async def people_by_level(level: str, limit: int = 30) -> list[Person]:
    async with async_session() as s:
        rows = await s.execute(
            select(Person)
            .where(Person.level == level)
            .order_by(desc(Person.last_message_at))
            .limit(limit)
        )
        return list(rows.scalars().all())


async def count_by_level() -> dict[str, int]:
    async with async_session() as s:
        rows = await s.execute(select(Person.level, func.count(Person.id)).group_by(Person.level))
        return {level: cnt for level, cnt in rows.all()}


async def find_by_username(username: str) -> Person | None:
    async with async_session() as s:
        row = await s.execute(
            select(Person).where(func.lower(Person.username) == username.lower().lstrip("@"))
        )
        return row.scalars().first()


# ---------------------------------------------------------------- Chat history


async def save_message(chat_id: int, role: str, text: str, user_id: int | None = None) -> None:
    async with async_session() as s:
        s.add(ChatMessage(chat_id=chat_id, user_id=user_id, role=role, text=text))
        await s.commit()


async def get_history(chat_id: int, limit: int = 20) -> list[tuple[str, str]]:
    """Oxirgi N xabar — eskidan yangiga tartiblangan (role, text) juftliklari."""
    async with async_session() as s:
        rows = await s.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(desc(ChatMessage.id))
            .limit(limit)
        )
        messages = list(rows.scalars().all())
    return [(m.role, m.text) for m in reversed(messages)]


# ---------------------------------------------------------------- Knowledge base


async def kb_all(active_only: bool = False) -> list[KnowledgeSection]:
    async with async_session() as s:
        q = select(KnowledgeSection).order_by(KnowledgeSection.position)
        if active_only:
            q = q.where(KnowledgeSection.is_active.is_(True))
        return list((await s.execute(q)).scalars().all())


async def kb_get(section_id: int) -> KnowledgeSection | None:
    async with async_session() as s:
        return await s.get(KnowledgeSection, section_id)


async def kb_add(title: str, content: str) -> KnowledgeSection:
    async with async_session() as s:
        max_pos = (await s.execute(select(func.max(KnowledgeSection.position)))).scalar() or 0
        section = KnowledgeSection(title=title, content=content, position=max_pos + 1)
        s.add(section)
        await s.commit()
        return section


async def kb_update_content(section_id: int, content: str) -> None:
    async with async_session() as s:
        await s.execute(
            update(KnowledgeSection)
            .where(KnowledgeSection.id == section_id)
            .values(content=content, updated_at=utcnow())
        )
        await s.commit()


async def kb_toggle(section_id: int) -> bool:
    """Bo'limni yoqadi/o'chiradi; yangi holatni qaytaradi."""
    async with async_session() as s:
        section = await s.get(KnowledgeSection, section_id)
        if section is None:
            return False
        section.is_active = not section.is_active
        await s.commit()
        return section.is_active


async def kb_delete(section_id: int) -> None:
    async with async_session() as s:
        await s.execute(delete(KnowledgeSection).where(KnowledgeSection.id == section_id))
        await s.commit()


async def kb_move(section_id: int, up: bool) -> None:
    """Bo'limni tartibda bir pog'ona yuqoriga/pastga suradi."""
    sections = await kb_all()
    idx = next((i for i, sec in enumerate(sections) if sec.id == section_id), None)
    if idx is None:
        return
    swap_with = idx - 1 if up else idx + 1
    if swap_with < 0 or swap_with >= len(sections):
        return
    a, b = sections[idx], sections[swap_with]
    async with async_session() as s:
        await s.execute(
            update(KnowledgeSection).where(KnowledgeSection.id == a.id).values(position=b.position)
        )
        await s.execute(
            update(KnowledgeSection).where(KnowledgeSection.id == b.id).values(position=a.position)
        )
        await s.commit()


# ---------------------------------------------------------------- Logs & stats


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


async def stats_since(since: datetime) -> dict:
    """Berilgan vaqtdan beri statistika."""
    async with async_session() as s:
        incoming = (
            await s.execute(
                select(func.count(ChatMessage.id)).where(
                    ChatMessage.role == "user", ChatMessage.created_at >= since
                )
            )
        ).scalar_one()

        by_status_rows = await s.execute(
            select(ResponseLog.status, func.count(ResponseLog.id))
            .where(ResponseLog.created_at >= since)
            .group_by(ResponseLog.status)
        )
        by_status = {status: cnt for status, cnt in by_status_rows.all()}

        top_rows = await s.execute(
            select(ChatMessage.user_id, func.count(ChatMessage.id).label("cnt"))
            .where(ChatMessage.role == "user", ChatMessage.created_at >= since)
            .group_by(ChatMessage.user_id)
            .order_by(desc("cnt"))
            .limit(5)
        )
        top: list[tuple[str, int]] = []
        for user_id, cnt in top_rows.all():
            person = await s.get(Person, user_id) if user_id else None
            name = person.full_name if person else str(user_id)
            top.append((name, cnt))

    return {"incoming": incoming, "by_status": by_status, "top": top}
